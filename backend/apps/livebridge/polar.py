"""Polar (merchant of record): checkout sessions for the packages.

Built against Polar's sandbox first (`POLAR_API_BASE`). Fail closed: no access token or no product id
for a package means no checkout. Only HTTP status codes are logged — never tokens, bodies or e-mails.
"""
from __future__ import annotations

import logging

import httpx
from django.conf import settings

from .models import Account, Package

logger = logging.getLogger('livebridge')

TIMEOUT = 10.0


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
