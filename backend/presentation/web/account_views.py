"""LiveBridge accounts on the web: Google sign-in and the account pages (`apps/livebridge`).

Sign-in is Google's redirect flow with PKCE; the code is exchanged by the server. Only the
LiveBridge key of the session is ever written or removed (`livebridge.session`), so a Telegram
visitor sign-in or a staff login in the same browser survive.
"""
import base64
import hashlib
import hmac
import logging
import secrets
import time

from apptelemetry import ratelimit
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST
from livebridge import google
from livebridge.session import current_account, sign_in, sign_out

logger = logging.getLogger('livebridge')

GOOGLE_SESSION_KEY = 'lb_google'
GOOGLE_STATE_TTL = 600  # seconds between leaving for Google and coming back
GOOGLE_FAILURES = ratelimit.Limit('lb_google_fail', 15, ratelimit.HOUR)


def _safe_next(request, value: str | None) -> str:
    if value and value.startswith('/') and url_has_allowed_host_and_scheme(
            value, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return value
    return reverse('account')


def _callback_uri(request) -> str:
    return request.build_absolute_uri(reverse('livebridge_google_callback'))


@require_GET
def google_start(request):
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        messages.error(request, _('Sign-in is not configured yet. Please try again later.'))
        return redirect('account')
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    request.session[GOOGLE_SESSION_KEY] = {
        'state': state, 'verifier': verifier, 'next': _safe_next(request, request.GET.get('next')), 'at': time.time(),
    }
    return redirect(google.authorization_url(_callback_uri(request), state, challenge))


@require_GET
def google_callback(request):
    pending = request.session.pop(GOOGLE_SESSION_KEY, None)
    state = request.GET.get('state', '')
    if (not isinstance(pending, dict) or not state or not hmac.compare_digest(state, str(pending.get('state', '')))
            or time.time() - float(pending.get('at', 0)) > GOOGLE_STATE_TTL):
        messages.error(request, _('Sign-in expired. Please try again.'))
        return redirect('account')
    if request.GET.get('error'):
        messages.info(request, _('Sign-in cancelled.'))
        return redirect('account')

    id_token = google.exchange_code(request.GET.get('code', ''), _callback_uri(request), pending['verifier'])
    info = google.verify_id_token(id_token) if id_token else None
    if info is None:
        if ratelimit.hit(GOOGLE_FAILURES, ratelimit.address_hash(request)):
            return HttpResponse(_('Too many failed sign-ins. Please try again later.'), status=429)
        messages.error(request, _('Sign-in with Google failed. Please try again.'))
        return redirect('account')
    account = google.account_for(info)
    if account is None:
        messages.error(request, _('This account is closed.'))
        return redirect('account')
    sign_in(request, account)
    return redirect(pending['next'])


def account_page(request):
    return render(request, 'web/account/index.html', {'account': current_account(request)})


@require_POST
def account_sign_out(request):
    sign_out(request)
    return redirect('account')
