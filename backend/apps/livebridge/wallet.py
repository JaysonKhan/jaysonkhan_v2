"""The wallet: the one place an account's balance changes.

Every change locks the account row, writes an append-only `LedgerEntry` with the balance after it,
and saves the balance — in one transaction. A repeated `(kind, reference)` is refused by the unique
constraint (inside a savepoint) and changes nothing; there is deliberately no "does it exist?" query
first, so a sequential retry takes the same path as a concurrent one.
"""
from __future__ import annotations

from datetime import datetime
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Account, LedgerEntry, TrialDevice


def _locked(account: Account) -> Account:
    return Account.objects.select_for_update().get(pk=account.pk)


def _apply(account: Account, units: int, kind: str, reference: str, details: dict) -> LedgerEntry | None:
    """Adds signed `units` to the locked account. Caller holds the transaction."""
    locked = _locked(account)
    balance = locked.balance_units + units
    try:
        with transaction.atomic():
            entry = LedgerEntry.objects.create(account=locked, kind=kind, units=units, balance_after=balance,
                                               reference=reference, details=details)
    except IntegrityError:
        account.balance_units = locked.balance_units
        return None
    locked.balance_units = balance
    locked.save(update_fields=['balance_units'])
    account.balance_units = balance
    return entry


def credit(account: Account, units: int, kind: str, reference: str = '',
           details: dict | None = None) -> LedgerEntry | None:
    if units < 0:
        raise ValueError('credit takes a positive amount')
    with transaction.atomic():
        return _apply(account, units, kind, reference, dict(details or {}))


def debit(account: Account, units: int, kind: str, reference: str = '',
          details: dict | None = None) -> LedgerEntry | None:
    """Takes `min(units, balance)`; the entry records what was taken and, in details, what was asked."""
    if units < 0:
        raise ValueError('debit takes a positive amount')
    with transaction.atomic():
        taken = min(units, _locked(account).balance_units)
        return _apply(account, -taken, kind, reference, {**(details or {}), 'asked': units})


def usage_units(stt_ms_out: int, stt_ms_in: int, tts_chars: int) -> int:
    stt = -(-(stt_ms_out + stt_ms_in) * settings.LIVEBRIDGE_STT_UNITS_PER_SECOND // 1000)  # ceil, integers only
    return stt + tts_chars * settings.LIVEBRIDGE_TTS_UNITS_PER_CHAR


def _balance(account: Account) -> int:
    return Account.objects.values_list('balance_units', flat=True).get(pk=account.pk)


def record_usage(account: Account, session_id: str, seq: int, stt_ms_out: int, stt_ms_in: int,
                 tts_chars: int) -> tuple[int, int]:
    """Charges one gateway report once. Returns (units charged, balance after)."""
    units = usage_units(stt_ms_out, stt_ms_in, tts_chars)
    if units == 0:
        return 0, _balance(account)
    # The account is part of the reference: a session id reused by another account must still be charged.
    entry = debit(account, units, LedgerEntry.USAGE, f'{account.pk}:{session_id}:{seq}',
                  {'stt_ms_out': stt_ms_out, 'stt_ms_in': stt_ms_in, 'tts_chars': tts_chars})
    if entry is None:
        return 0, _balance(account)
    return -entry.units, entry.balance_after


def grant_trial(account: Account, device_id: str, now: datetime | None = None) -> str:
    """'granted' | 'account_used' | 'device_used' | 'daily_cap' — once per account and once per device."""
    now = now or timezone.now()
    with transaction.atomic():
        locked = _locked(account)
        if LedgerEntry.objects.filter(account=locked, kind=LedgerEntry.TRIAL).exists():
            return 'account_used'
        if TrialDevice.objects.filter(device_id=device_id).exists():
            return 'device_used'
        midnight = now.astimezone(dt_timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today = LedgerEntry.objects.filter(kind=LedgerEntry.TRIAL, created_at__gte=midnight).count()
        if today >= settings.LIVEBRIDGE_TRIALS_PER_DAY:
            return 'daily_cap'
        try:
            with transaction.atomic():
                TrialDevice.objects.create(device_id=device_id, account=locked)
        except IntegrityError:
            return 'device_used'
        _apply(account, settings.LIVEBRIDGE_TRIAL_UNITS, LedgerEntry.TRIAL, f'trial:{locked.public_id}', {})
        return 'granted'


def adjust(account: Account, units: int, reason: str, by: str) -> LedgerEntry:
    """A manual correction by staff: credits or debits by sign, with a reason and who made it."""
    reason = (reason or '').strip()
    if not units or not reason:
        raise ValueError('an adjustment needs a non-zero amount and a reason')
    details = {'reason': reason, 'by': by}
    if units > 0:
        return credit(account, units, LedgerEntry.ADJUSTMENT, details=details)
    return debit(account, -units, LedgerEntry.ADJUSTMENT, details=details)


def has_purchase(account: Account) -> bool:
    return LedgerEntry.objects.filter(account=account, kind=LedgerEntry.PURCHASE).exists()


def minutes(units: int) -> int:
    return units // settings.LIVEBRIDGE_UNITS_PER_MINUTE
