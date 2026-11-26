"""The LiveBridge desktop app's API — `/api/livebridge/v1/` (contract: docs/LIVEBRIDGE-ACCOUNTS.md, local).

Plain DRF views without DRF authentication or throttles (the JWT authenticator would reject our opaque
tokens): bearer tokens go through `livebridge.devices.authenticate`, limits through `apptelemetry.ratelimit`,
errors are `{"error": code}`. No token, code or e-mail is logged.
"""
from apptelemetry import ratelimit
from apptelemetry.validation import EnvelopeError
from django.conf import settings
from django.urls import reverse
from django.utils import translation
from livebridge import devices, polar, wallet
from livebridge.models import Package
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services_views import _error, _rate_limited, _read_json

MAX_BODY_BYTES = 16 * 1024
START_PER_ADDRESS = ratelimit.Limit('lb_start', 20, ratelimit.HOUR)


def _body(request) -> dict:
    data = _read_json(request, MAX_BODY_BYTES) if request._request.body else {}
    if not isinstance(data, dict):
        raise EnvelopeError('bad_json')
    return data


def _bearer_device(request):
    scheme, _, token = request.META.get('HTTP_AUTHORIZATION', '').partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        return None
    return devices.authenticate(token.strip())


def _pair(pair: devices.TokenPair) -> dict:
    return {'access_token': pair.access_token, 'refresh_token': pair.refresh_token, 'token_type': 'Bearer',
            'expires_in': pair.expires_in}


class _LiveBridgeView(APIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)
    throttle_classes = ()

    def handle_exception(self, exc):
        if isinstance(exc, EnvelopeError):
            return _error(exc.code, exc.status)
        return super().handle_exception(exc)


class _AccountView(_LiveBridgeView):
    """Needs `Authorization: Bearer <access token>`; sets `self.device`."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.device = _bearer_device(request)


def _require_device(view_method):
    def wrapped(self, request, *args, **kwargs):
        if self.device is None:
            return _error('invalid_token', status.HTTP_401_UNAUTHORIZED)
        return view_method(self, request, *args, **kwargs)
    return wrapped


class DeviceStartView(_LiveBridgeView):
    http_method_names = ('post', 'options')

    def post(self, request):
        retry = ratelimit.hit(START_PER_ADDRESS, ratelimit.address_hash(request))
        if retry:
            return _rate_limited(retry)
        data = _body(request)
        device_id, device_name = data.get('device_id'), data.get('device_name', '')
        if not isinstance(device_name, str):
            return _error('invalid_device', status.HTTP_400_BAD_REQUEST)
        try:
            grant, device_code = devices.start_grant(device_id, device_name)
        except ValueError:
            return _error('invalid_device', status.HTTP_400_BAD_REQUEST)
        with translation.override('en'):
            verification_uri = request.build_absolute_uri(reverse('account_connect'))
        return Response({
            'device_code': device_code,
            'user_code': grant.user_code,
            'verification_uri': verification_uri,
            'verification_uri_complete': f'{verification_uri}?code={grant.user_code}',
            'expires_in': int(devices.GRANT_TTL.total_seconds()),
            'interval': grant.interval,
        }, status=status.HTTP_201_CREATED)


class DeviceTokenView(_LiveBridgeView):
    http_method_names = ('post', 'options')

    def post(self, request):
        device_code = _body(request).get('device_code')
        result = devices.poll(device_code if isinstance(device_code, str) else '')
        if isinstance(result, str):
            return _error(result, status.HTTP_400_BAD_REQUEST)
        return Response(_pair(result))


class TokenRefreshView(_LiveBridgeView):
    http_method_names = ('post', 'options')

    def post(self, request):
        refresh_token = _body(request).get('refresh_token')
        pair = devices.refresh(refresh_token) if isinstance(refresh_token, str) else None
        if pair is None:
            return _error('invalid_grant', status.HTTP_401_UNAUTHORIZED)
        return Response(_pair(pair))


class LogoutView(_AccountView):
    http_method_names = ('post', 'options')

    @_require_device
    def post(self, request):
        devices.revoke(self.device)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(_AccountView):
    http_method_names = ('get', 'options')

    @_require_device
    def get(self, request):
        account = self.device.account
        return Response({
            'account_id': str(account.public_id),
            'email': account.email,
            'name': account.name,
            'balance_units': account.balance_units,
            'units_per_minute': settings.LIVEBRIDGE_UNITS_PER_MINUTE,
            'rates': {'stt_units_per_second': settings.LIVEBRIDGE_STT_UNITS_PER_SECOND,
                      'tts_units_per_char': settings.LIVEBRIDGE_TTS_UNITS_PER_CHAR},
            'has_purchase': wallet.has_purchase(account),
        })


class PackagesView(_LiveBridgeView):
    http_method_names = ('get', 'options')

    def get(self, request):
        return Response([
            {'code': p.code, 'price_cents': p.price_cents, 'currency': 'usd', 'units': p.units,
             'minutes': wallet.minutes(p.units)}
            for p in Package.objects.filter(is_active=True).order_by('sort_order')
        ])


def purchase_success_url(request) -> str:
    """Where Polar sends the buyer back: the purchase page in the request's language (Polar fills the id)."""
    return request.build_absolute_uri(reverse('account_purchase_done')) + '?checkout_id={CHECKOUT_ID}'


class CheckoutView(_AccountView):
    http_method_names = ('post', 'options')

    @_require_device
    def post(self, request):
        code = _body(request).get('package')
        package = Package.objects.filter(code=code, is_active=True).first() if isinstance(code, str) else None
        if package is None:
            return _error('unknown_package', status.HTTP_404_NOT_FOUND)
        try:
            url = polar.create_checkout(self.device.account, package, purchase_success_url(request))
        except polar.PolarError:
            return _error('checkout_unavailable', status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({'url': url}, status=status.HTTP_201_CREATED)
