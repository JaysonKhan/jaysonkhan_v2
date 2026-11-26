"""The LiveBridge account in the browser session.

Only our own key is touched: Django's `login`/`logout` would flush the whole session and with it the
Telegram visitor key and a staff login that share the cookie.
"""
from __future__ import annotations

from .models import Account

SESSION_KEY = 'lb_account'


def current_account(request) -> Account | None:
    pk = request.session.get(SESSION_KEY)
    if not pk:
        return None
    account = Account.objects.filter(pk=pk, is_active=True).first()
    if account is None:
        request.session.pop(SESSION_KEY, None)
    return account


def sign_in(request, account: Account) -> None:
    request.session.cycle_key()  # a new session id at sign-in; the other keys are kept
    request.session[SESSION_KEY] = account.pk


def sign_out(request) -> None:
    request.session.pop(SESSION_KEY, None)
