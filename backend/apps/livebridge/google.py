"""Google sign-in for LiveBridge accounts: the redirect flow, with the code exchanged by the server.

`verify_id_token` is ported from the owner's other Django project (tokeninfo endpoint, IPv4, short
connect timeout). Fail closed: an empty client id or secret accepts nothing. Tokens, codes and e-mail
addresses are never logged. Network helpers are module functions so tests can patch them.
"""
from __future__ import annotations

import logging
import time
from urllib.parse import urlencode

import httpx
from django.conf import settings
from django.db import transaction

from .models import Account

logger = logging.getLogger('livebridge')

AUTHORIZE_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
TOKENINFO_URL = 'https://oauth2.googleapis.com/tokeninfo'
_VALID_ISS = ('https://accounts.google.com', 'accounts.google.com')
# Google's IPv6 address sometimes hangs until the connect timeout; IPv4 with a short connect timeout.
_TIMEOUT = httpx.Timeout(5.0, connect=2.0)


def _client() -> httpx.Client:
    return httpx.Client(transport=httpx.HTTPTransport(local_address='0.0.0.0'), timeout=_TIMEOUT)


def _post_token(data: dict) -> httpx.Response:
    with _client() as client:
        return client.post(TOKEN_URL, data=data)


def _tokeninfo_get(id_token: str) -> httpx.Response:
    with _client() as client:
        return client.get(TOKENINFO_URL, params={'id_token': id_token})


def authorization_url(redirect_uri: str, state: str, code_challenge: str) -> str:
    return AUTHORIZE_URL + '?' + urlencode({
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
        'prompt': 'select_account',
    })


def exchange_code(code: str, redirect_uri: str, code_verifier: str) -> str | None:
    """The ID token for an authorization code, or None."""
    try:
        response = _post_token({
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'code': code,
            'code_verifier': code_verifier,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        })
    except httpx.HTTPError as exc:
        logger.warning('livebridge.google token exchange failed: %s', type(exc).__name__)
        return None
    if not response.is_success:
        logger.warning('livebridge.google token exchange status=%s', response.status_code)
        return None
    try:
        id_token = response.json().get('id_token')
    except (ValueError, AttributeError):
        return None
    return id_token if isinstance(id_token, str) and id_token else None


def verify_id_token(id_token: str) -> dict | None:
    """{'sub', 'email', 'name'} for a valid token issued to our client with a verified e-mail, else None."""
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    if not client_id or not id_token:
        return None
    try:
        response = _tokeninfo_get(id_token)
    except httpx.HTTPError as exc:
        logger.warning('livebridge.google tokeninfo failed: %s', type(exc).__name__)
        return None
    if not response.is_success:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict) or payload.get('iss') not in _VALID_ISS:
        return None
    if payload.get('aud') != client_id:
        logger.warning('livebridge.google token for another audience refused')
        return None
    if payload.get('email_verified') not in (True, 'true'):
        return None
    try:
        if 'exp' in payload and int(payload['exp']) <= time.time():
            return None
    except (TypeError, ValueError):
        return None
    sub = payload.get('sub')
    if not sub:
        return None
    return {'sub': str(sub), 'email': str(payload.get('email') or ''), 'name': str(payload.get('name') or '')}


def account_for(info: dict) -> Account | None:
    """The account for a verified Google identity (found by sub, e-mail and name refreshed), or a new one.

    None when the account was closed by the owner.
    """
    email, name = info['email'][:254], info['name'][:150]
    with transaction.atomic():
        account, created = Account.objects.get_or_create(google_sub=info['sub'],
                                                         defaults={'email': email, 'name': name})
        if not created and (account.email, account.name) != (email, name):
            account.email, account.name = email, name
            account.save(update_fields=['email', 'name'])
    if created:
        logger.info('livebridge.account created account=%s', account.pk)
    return account if account.is_active else None
