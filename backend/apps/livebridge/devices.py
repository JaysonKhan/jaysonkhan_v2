"""Connecting the desktop app to an account, and the device's tokens.

Shaped like the OAuth device grant: the app starts a grant and gets a secret device code plus a short
user code; the person confirms the code on the account page; the app polls until it receives an access
token (short-lived) and a refresh token (long-lived, rotating). Tokens are opaque random strings and
only their SHA-256 hashes are stored — every comparison is a hash lookup.
"""
from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from . import wallet
from .models import Account, Device, DeviceGrant, RetiredRefreshToken

GRANT_TTL = timedelta(minutes=10)
ACCESS_TTL = timedelta(minutes=15)
REFRESH_TTL = timedelta(days=90)
USER_CODE_ALPHABET = 'BCDFGHJKLMNPQRSTVWXZ'  # shown as XXXX-XXXX
DEVICE_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{8,64}$')
SEEN_EVERY = timedelta(minutes=1)


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int  # seconds, = ACCESS_TTL


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def normalize_user_code(text: str) -> str | None:
    """'bcdf ghjk' → 'BCDF-GHJK'; None unless it is exactly 8 letters of the alphabet."""
    letters = re.sub(r'[\s-]', '', text or '').upper()
    if len(letters) != 8 or any(ch not in USER_CODE_ALPHABET for ch in letters):
        return None
    return f'{letters[:4]}-{letters[4:]}'


def _new_user_code() -> str:
    letters = ''.join(secrets.choice(USER_CODE_ALPHABET) for _ in range(8))
    return f'{letters[:4]}-{letters[4:]}'


def _clean_name(name: str) -> str:
    printable = ''.join(ch for ch in (name or '') if ch.isprintable()).strip()
    return printable[:80] or 'LiveBridge'


def start_grant(device_id: str, device_name: str, now: datetime | None = None) -> tuple[DeviceGrant, str]:
    """A new pending grant and its plain device code (returned once, never stored)."""
    now = now or timezone.now()
    if not isinstance(device_id, str) or not DEVICE_ID_PATTERN.match(device_id):
        raise ValueError('invalid device id')
    DeviceGrant.objects.filter(expires_at__lt=now - timedelta(days=1)).delete()
    user_code = _new_user_code()
    while DeviceGrant.objects.filter(user_code=user_code, status=DeviceGrant.PENDING, expires_at__gt=now).exists():
        user_code = _new_user_code()
    device_code = 'lbd_' + secrets.token_urlsafe(32)
    grant = DeviceGrant.objects.create(
        device_code_hash=token_hash(device_code), user_code=user_code, device_id=device_id,
        device_name=_clean_name(device_name), expires_at=now + GRANT_TTL,
    )
    return grant, device_code


def find_pending_grant(user_code: str, now: datetime | None = None) -> DeviceGrant | None:
    code = normalize_user_code(user_code)
    if code is None:
        return None
    return (DeviceGrant.objects.filter(user_code=code, status=DeviceGrant.PENDING,
                                       expires_at__gt=now or timezone.now())
            .order_by('-created_at').first())


def approve(grant: DeviceGrant, account: Account, now: datetime | None = None) -> str:
    """Marks the grant approved for `account` and grants the trial; returns (and stores) the trial outcome.

    A grant that is no longer pending is left as it is and its stored outcome returned (a repeated submit).
    """
    now = now or timezone.now()
    with transaction.atomic():
        locked = DeviceGrant.objects.select_for_update().get(pk=grant.pk)
        if locked.status != DeviceGrant.PENDING or locked.expires_at <= now:
            return locked.trial_outcome
        locked.trial_outcome = wallet.grant_trial(account, locked.device_id, now=now)
        locked.status = DeviceGrant.APPROVED
        locked.account = account
        locked.save(update_fields=['trial_outcome', 'status', 'account'])
    grant.status, grant.account, grant.trial_outcome = locked.status, locked.account, locked.trial_outcome
    return locked.trial_outcome


def deny(grant: DeviceGrant) -> None:
    DeviceGrant.objects.filter(pk=grant.pk, status=DeviceGrant.PENDING).update(status=DeviceGrant.DENIED)
    grant.refresh_from_db(fields=['status'])


def _issue(device: Device, now: datetime) -> TokenPair:
    access = 'lba_' + secrets.token_urlsafe(32)
    refresh_token = 'lbr_' + secrets.token_urlsafe(32)
    device.access_hash = token_hash(access)
    device.access_expires_at = now + ACCESS_TTL
    device.refresh_hash = token_hash(refresh_token)
    device.refresh_expires_at = now + REFRESH_TTL
    return TokenPair(access, refresh_token, int(ACCESS_TTL.total_seconds()))


def poll(device_code: str, now: datetime | None = None) -> TokenPair | str:
    """The app's poll: tokens once approved, otherwise an RFC 8628 error code."""
    now = now or timezone.now()
    with transaction.atomic():
        grant = (DeviceGrant.objects.select_for_update()
                 .filter(device_code_hash=token_hash(device_code or '')).first())
        if grant is None:
            return 'invalid_grant'
        if now >= grant.expires_at:
            return 'expired_token'
        if grant.status == DeviceGrant.DENIED:
            return 'access_denied'
        if grant.status == DeviceGrant.PENDING:
            too_soon = grant.last_polled_at and (now - grant.last_polled_at).total_seconds() < grant.interval
            grant.last_polled_at = now
            if too_soon:
                grant.interval += 5
                grant.save(update_fields=['last_polled_at', 'interval'])
                return 'slow_down'
            grant.save(update_fields=['last_polled_at'])
            return 'authorization_pending'
        if grant.status != DeviceGrant.APPROVED:
            return 'invalid_grant'
        for old in Device.objects.filter(account_id=grant.account_id, device_id=grant.device_id,
                                         revoked_at__isnull=True):
            revoke(old, now=now)
        device = Device(account_id=grant.account_id, device_id=grant.device_id, name=grant.device_name)
        pair = _issue(device, now)
        device.save()
        grant.status = DeviceGrant.CONSUMED
        grant.save(update_fields=['status'])
        return pair


def _usable(device: Device) -> bool:
    account = device.account
    return device.revoked_at is None and account.is_active and account.deletion_requested_at is None


def refresh(refresh_token: str, now: datetime | None = None) -> TokenPair | None:
    """Rotates both tokens. Any earlier refresh token of the device used again signs it out (a copied store)."""
    now = now or timezone.now()
    hashed = token_hash(refresh_token or '')
    with transaction.atomic():
        device = Device.objects.select_for_update().filter(refresh_hash=hashed).first()
        if device is None:
            retired = RetiredRefreshToken.objects.filter(token_hash=hashed).select_related('device').first()
            if retired is not None and retired.device.revoked_at is None:
                revoke(retired.device, now=now)
            return None
        if not _usable(device) or device.refresh_expires_at <= now:
            return None
        RetiredRefreshToken.objects.create(device=device, token_hash=hashed, created_at=now)
        RetiredRefreshToken.objects.filter(device=device, created_at__lt=now - REFRESH_TTL).delete()
        pair = _issue(device, now)
        device.save(update_fields=['access_hash', 'access_expires_at', 'refresh_hash', 'refresh_expires_at'])
        return pair


def authenticate(access_token: str, now: datetime | None = None) -> Device | None:
    now = now or timezone.now()
    device = (Device.objects.select_related('account')
              .filter(access_hash=token_hash(access_token or '')).first())
    if device is None or not _usable(device) or device.access_expires_at <= now:
        return None
    if device.last_used_at is None or now - device.last_used_at >= SEEN_EVERY:
        device.last_used_at = now
        device.save(update_fields=['last_used_at'])
    account = device.account
    if account.last_seen_at is None or now - account.last_seen_at >= SEEN_EVERY:
        account.last_seen_at = now
        account.save(update_fields=['last_seen_at'])
    return device


def revoke(device: Device, now: datetime | None = None) -> None:
    device.revoked_at = device.revoked_at or now or timezone.now()
    device.access_hash = None
    device.save(update_fields=['revoked_at', 'access_hash'])
