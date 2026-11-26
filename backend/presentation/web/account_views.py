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
from urllib.parse import urlencode

from apptelemetry import ratelimit
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView
from livebridge import devices, google, polar, wallet
from livebridge.models import Device, DeviceGrant, LedgerEntry, Package
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


def _language_of(path: str) -> str | None:
    """'uz' for '/uz/account/…' — the page the person came from decides the language of the way back."""
    parts = (path or '').split('/', 2)
    code = parts[1] if len(parts) == 3 and parts[0] == '' else ''
    return code if code in dict(settings.LANGUAGES) else None


@require_GET
def google_start(request):
    next_url = _safe_next(request, request.GET.get('next'))
    with translation.override(_language_of(next_url) or translation.get_language()):
        if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
            messages.error(request, _('Sign-in is not configured yet. Please try again later.'))
            return redirect('account')
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        request.session[GOOGLE_SESSION_KEY] = {'state': state, 'verifier': verifier, 'next': next_url,
                                               'at': time.time()}
        return redirect(google.authorization_url(_callback_uri(request), state, challenge))


@require_GET
def google_callback(request):
    pending = request.session.pop(GOOGLE_SESSION_KEY, None)
    next_url = str(pending.get('next') or '') if isinstance(pending, dict) else ''
    with translation.override(_language_of(next_url) or translation.get_language()):
        return _finish_google_sign_in(request, pending)


def _finish_google_sign_in(request, pending):
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


# ── Account pages ──────────────────────────────────────────────────────────────

WRONG_CODES_PER_ACCOUNT = ratelimit.Limit('lb_code_acct', 10, ratelimit.HOUR)
WRONG_CODES_PER_ADDRESS = ratelimit.Limit('lb_code_addr', 30, ratelimit.HOUR)
HISTORY_LIMIT = 50

PACKAGE_NAMES = {'starter': gettext_lazy('Starter'), 'medium': gettext_lazy('Medium'), 'large': gettext_lazy('Large')}
KIND_LABELS = {
    LedgerEntry.TRIAL: gettext_lazy('Free trial'),
    LedgerEntry.PURCHASE: gettext_lazy('Purchase'),
    LedgerEntry.USAGE: gettext_lazy('Usage'),
    LedgerEntry.REFUND: gettext_lazy('Refund'),
    LedgerEntry.ADJUSTMENT: gettext_lazy('Adjustment'),
}


def group_digits(number: int) -> str:
    """29000 → '29 000' (a no-break space, the same in every language)."""
    return f'{number:,}'.replace(',', '\u00a0')


def _minutes_delta(units: int) -> str:
    text = f'{units / settings.LIVEBRIDGE_UNITS_PER_MINUTE:+.1f}'
    return text.replace('-', '\u2212')


def _sign_in_redirect(request):
    return redirect(f"{reverse('livebridge_google_start')}?{urlencode({'next': request.get_full_path()})}")


def account_page(request):
    account = current_account(request)
    context = {'account': account}
    if account is not None:
        entries = list(account.entries.order_by('-created_at', '-pk')[:HISTORY_LIMIT])
        for entry in entries:
            entry.label = KIND_LABELS.get(entry.kind, entry.kind)
            entry.minutes_delta = _minutes_delta(entry.units)
            entry.minutes_after = wallet.minutes(max(entry.balance_after, 0))
        packages = list(Package.objects.filter(is_active=True).order_by('sort_order'))
        for package in packages:
            package.label = PACKAGE_NAMES.get(package.code, package.code)
            package.price = f'${package.price_cents / 100:g}'
            package.minutes = wallet.minutes(package.units)
        context.update({
            'balance_minutes': wallet.minutes(account.balance_units),
            'balance_units': group_digits(account.balance_units),
            'entries': entries,
            'packages': packages,
            'devices': account.devices.filter(revoked_at__isnull=True).order_by('-created_at'),
        })
    return render(request, 'web/account/index.html', context)


def _code_limited(request, account) -> bool:
    return bool(ratelimit.exceeded(WRONG_CODES_PER_ACCOUNT, str(account.pk))
                or ratelimit.exceeded(WRONG_CODES_PER_ADDRESS, ratelimit.address_hash(request)))


def _count_wrong_code(request, account) -> None:
    ratelimit.hit(WRONG_CODES_PER_ACCOUNT, str(account.pk))
    ratelimit.hit(WRONG_CODES_PER_ADDRESS, ratelimit.address_hash(request))


def _connected_already(account, raw_code: str):
    code = devices.normalize_user_code(raw_code)
    if code is None:
        return None
    return (DeviceGrant.objects.filter(user_code=code, account=account, expires_at__gt=timezone.now(),
                                       status__in=(DeviceGrant.APPROVED, DeviceGrant.CONSUMED))
            .order_by('-created_at').first())


def account_connect(request):
    """The browser half of connecting the app: the person sees the app's code and confirms it."""
    account = current_account(request)
    if account is None:
        return _sign_in_redirect(request)
    if request.method not in ('GET', 'POST'):
        return HttpResponseNotAllowed(['GET', 'POST'])
    data = request.POST if request.method == 'POST' else request.GET
    raw_code = (data.get('code') or '').strip()
    context = {'state': 'enter', 'code': raw_code[:20]}
    if not raw_code:
        return render(request, 'web/account/connect.html', context)
    if _code_limited(request, account):
        context['error'] = _('Too many wrong codes. Please wait an hour and try again.')
        return render(request, 'web/account/connect.html', context)
    grant = devices.find_pending_grant(raw_code)
    if grant is None and request.method == 'POST':
        done = _connected_already(account, raw_code)
        if done is not None:  # the Connect button pressed twice: show the first answer again
            context.update({'state': 'connected', 'grant': done, 'code': done.user_code,
                            'trial_outcome': done.trial_outcome,
                            'trial_minutes': wallet.minutes(settings.LIVEBRIDGE_TRIAL_UNITS)})
            return render(request, 'web/account/connect.html', context)
    if grant is None:
        _count_wrong_code(request, account)
        context['error'] = _('This code is not valid or has expired. Check it in the app.')
        return render(request, 'web/account/connect.html', context)

    context.update({'grant': grant, 'code': grant.user_code})
    if request.method == 'GET':
        context['state'] = 'confirm'
    elif data.get('action') == 'connect':
        context['state'] = 'connected'
        context['trial_outcome'] = devices.approve(grant, account)
        context['trial_minutes'] = wallet.minutes(settings.LIVEBRIDGE_TRIAL_UNITS)
        logger.info('livebridge.connect approved account=%s grant=%s', account.pk, grant.pk)
    else:
        devices.deny(grant)
        context['state'] = 'cancelled'
    return render(request, 'web/account/connect.html', context)


@require_GET
def account_buy(request, code: str):
    """The account page's "Buy": creates a Polar checkout for the package and sends the person there."""
    account = current_account(request)
    if account is None:
        return _sign_in_redirect(request)
    package = get_object_or_404(Package, code=code, is_active=True)
    success_url = request.build_absolute_uri(reverse('account_purchase_done')) + '?checkout_id={CHECKOUT_ID}'
    try:
        return redirect(polar.create_checkout(account, package, success_url))
    except polar.PolarError:
        messages.error(request, _('Payment is not available right now. Please try again later.'))
        return redirect('account')


@require_GET
def account_purchase_done(request):
    """Where Polar sends the person after paying. Credits nothing — the webhook does."""
    return render(request, 'web/account/purchase_done.html')


@require_POST
def account_device_sign_out(request, pk: int):
    account = current_account(request)
    if account is None:
        raise Http404
    device = get_object_or_404(Device, pk=pk, account=account, revoked_at__isnull=True)
    devices.revoke(device)
    messages.success(request, _('%(name)s is signed out.') % {'name': device.name})
    return redirect('account')


@require_POST
def account_delete(request):
    account = current_account(request)
    if account is None:
        return redirect('account')
    if request.POST.get('confirm') != 'on':
        messages.error(request, _('Tick the box to confirm.'))
        return redirect('account')
    with transaction.atomic():
        account.deletion_requested_at = timezone.now()
        account.save(update_fields=['deletion_requested_at'])
        for device in account.devices.filter(revoked_at__isnull=True):
            devices.revoke(device)
    logger.info('livebridge.account deletion requested account=%s', account.pk)
    sign_out(request)
    messages.success(request, _('Your account will be deleted within 30 days.'))
    return redirect('account')


@require_POST
def account_sign_out(request):
    sign_out(request)
    return redirect('account')


# ── Legal pages (English is binding; drafts until the owner approves them) ───────

livebridge_terms = TemplateView.as_view(template_name='web/livebridge_legal/terms.html')
livebridge_privacy = TemplateView.as_view(template_name='web/livebridge_legal/privacy.html')
livebridge_refunds = TemplateView.as_view(template_name='web/livebridge_legal/refunds.html')
