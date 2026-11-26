"""Polar (merchant of record): checkout sessions for the packages, and the order webhook.

Built against Polar's sandbox first (`POLAR_API_BASE`). Fail closed: no access token or no product id
for a package means no checkout; no webhook secret means every delivery is refused. Only status codes,
order ids and account ids are logged — never tokens, bodies or e-mails.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import logging
import time
import uuid
from collections.abc import Mapping

import httpx
from apptelemetry.ratelimit import HOUR, Limit
from django.conf import settings
from django.db import transaction

from . import alerts, wallet
from .models import Account, LedgerEntry, Package

logger = logging.getLogger('livebridge')

TIMEOUT = 10.0
# Each checkout is a blocking call to Polar and a row in the owner's Polar organisation.
CHECKOUTS_PER_ACCOUNT = Limit('lb_checkout', 10, HOUR)


class PolarError(Exception):
    """A checkout could not be created (not configured, network, or Polar refused)."""


def _post(url: str, payload: dict, headers: dict) -> httpx.Response:
    with httpx.Client(timeout=TIMEOUT) as client:
        return client.post(url, json=payload, headers=headers)


def create_checkout(account: Account, package: Package, success_url: str) -> str:
    """A Polar checkout for one package, tied to the account; returns the checkout page's address."""
    if not settings.POLAR_ACCESS_TOKEN or not package.polar_product_id:
        raise PolarError('checkout is not configured')
    payload = {
        'products': [package.polar_product_id],
        'external_customer_id': str(account.public_id),
        'customer_email': account.email,
        'success_url': success_url,
        'metadata': {'account': str(account.public_id), 'package': package.code},
    }
    try:
        response = _post(f"{settings.POLAR_API_BASE.rstrip('/')}/v1/checkouts/", payload,
                         {'Authorization': f'Bearer {settings.POLAR_ACCESS_TOKEN}', 'Accept': 'application/json'})
    except httpx.HTTPError as exc:
        logger.warning('livebridge.polar checkout failed: %s', type(exc).__name__)
        raise PolarError('network') from None
    if response.status_code != 201:
        logger.warning('livebridge.polar checkout status=%s account=%s', response.status_code, account.pk)
        raise PolarError(f'status {response.status_code}')
    try:
        url = response.json().get('url')
    except (ValueError, AttributeError):
        url = None
    if not isinstance(url, str) or not url.startswith('https://'):
        logger.warning('livebridge.polar checkout without a url account=%s', account.pk)
        raise PolarError('no url')
    return url


# ── Webhook ────────────────────────────────────────────────────────────────────

WEBHOOK_TOLERANCE = 300  # seconds between the delivery's timestamp and our clock


def _webhook_keys(secret: str) -> list[bytes]:
    """Standard Webhooks key (base64 after `whsec_`, endpoints made since 2026-09-08), then Polar's original
    scheme (the UTF-8 bytes of the whole secret) — Polar's own SDK tries both the same way."""
    keys = []
    if secret.startswith('whsec_'):
        try:
            keys.append(base64.b64decode(secret[len('whsec_'):], validate=True))
        except (binascii.Error, ValueError):
            pass
    keys.append(secret.encode())
    return keys


def verify_webhook(body: bytes, headers: Mapping[str, str], secret: str, now: float | None = None) -> bool:
    """Standard Webhooks: HMAC-SHA256 of `{webhook-id}.{webhook-timestamp}.{body}`, any `v1,<base64>` matches."""
    if not secret:
        return False
    msg_id = headers.get('webhook-id') or ''
    timestamp = headers.get('webhook-timestamp') or ''
    signatures = headers.get('webhook-signature') or ''
    if not msg_id or not signatures:
        return False
    try:
        sent_at = int(timestamp)
    except ValueError:
        return False
    if abs((time.time() if now is None else now) - sent_at) > WEBHOOK_TOLERANCE:
        return False
    signed = f'{msg_id}.{timestamp}.'.encode() + body
    expected = [base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()) for key in _webhook_keys(secret)]
    for item in signatures.split():
        version, _, value = item.partition(',')
        if version != 'v1':
            continue
        if any(hmac.compare_digest(candidate, value.encode()) for candidate in expected):
            return True
    return False


def _account_by_public_id(value) -> Account | None:
    try:
        public_id = uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None
    return Account.objects.filter(public_id=public_id).first()


def _order_paid(data: dict) -> None:
    order_id = str(data.get('id') or '')
    customer = data.get('customer') or {}
    # The checkout's own metadata first: a Polar customer's external id is set once and can be an older account's.
    account = (_account_by_public_id((data.get('metadata') or {}).get('account'))
               or _account_by_public_id(customer.get('external_id')))
    product_id = data.get('product_id')
    package = Package.objects.filter(polar_product_id=product_id).first() if product_id else None
    if not order_id or account is None or package is None:
        # The owner settles it by hand with an adjustment.
        logger.error('livebridge.polar.unmatched order=%s', order_id)
        alerts.owner_alert('unmatched_order', order=order_id)
        return
    entry = wallet.credit(account, package.units, LedgerEntry.PURCHASE, order_id, {
        'package': package.code, 'total_cents': data.get('total_amount'), 'net_cents': data.get('net_amount'),
        'currency': data.get('currency'),
    })
    if entry is not None:
        logger.info('livebridge.polar.credited order=%s account=%s', order_id, account.pk)


def _order_refunded(data: dict) -> None:
    """Takes back the units the order granted, in proportion to the amount refunded so far (never below zero)."""
    order_id = str(data.get('id') or '')
    purchase = (LedgerEntry.objects.filter(kind=LedgerEntry.PURCHASE, reference=order_id).first()
                if order_id else None)
    if purchase is None or purchase.account_id is None:
        logger.error('livebridge.polar.refund_unmatched order=%s', order_id)
        alerts.owner_alert('unmatched_refund', order=order_id)
        return
    try:
        net, refunded = int(data.get('net_amount') or 0), int(data.get('refunded_amount') or 0)
    except (TypeError, ValueError):
        net = refunded = 0
    if net <= 0 or refunded <= 0:
        logger.error('livebridge.polar.refund_amounts order=%s', order_id)
        return
    with transaction.atomic():
        account = Account.objects.select_for_update().get(pk=purchase.account_id)
        target = min(purchase.units, purchase.units * refunded // net)
        already = -sum(LedgerEntry.objects.filter(kind=LedgerEntry.REFUND, account=account,
                                                   details__order=order_id).values_list('units', flat=True))
        if target - already > 0:
            wallet.debit(account, target - already, LedgerEntry.REFUND, f'{order_id}:{refunded}',
                         {'order': order_id, 'refunded_cents': refunded})
            logger.info('livebridge.polar.refunded order=%s account=%s', order_id, account.pk)


def handle_event(event: dict) -> None:
    """Applies one verified delivery. Idempotent: a repeated delivery changes nothing."""
    data = event.get('data')
    if not isinstance(data, dict):
        return
    if event.get('type') == 'order.paid':
        _order_paid(data)
    elif event.get('type') == 'order.refunded':
        _order_refunded(data)
