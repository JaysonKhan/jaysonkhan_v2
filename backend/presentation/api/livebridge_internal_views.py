"""The LiveBridge gateway's internal calls — `/internal/livebridge/v1/` (contract: docs/LIVEBRIDGE-ACCOUNTS.md).

Plain Django views on purpose: a request that is not internal (`livebridge.internal.is_internal_request`)
raises Http404 and gets exactly the page a missing route gets. Tokens are never logged.
"""
import json
import re
import uuid

from django.http import Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from livebridge import devices, internal, wallet
from livebridge.models import Account

SESSION_ID = re.compile(r'^[A-Za-z0-9-]{1,64}$')
LIMITS = {'seq': 10**9, 'stt_ms_out': 120_000, 'stt_ms_in': 120_000, 'tts_chars': 20_000}


def _internal_json(request) -> dict:
    """The decoded body of a verified gateway call; Http404 for anyone else."""
    if not internal.is_internal_request(request) or request.method != 'POST':
        raise Http404
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _error(code: str, status: int) -> JsonResponse:
    return JsonResponse({'error': code}, status=status)


def _whole(value, upper: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= upper


@csrf_exempt
def authorize(request):
    data = _internal_json(request)
    token = data.get('access_token')
    device = devices.authenticate(token) if isinstance(token, str) else None
    if device is None:
        return _error('invalid_token', 401)
    account = device.account
    return JsonResponse({'account_id': str(account.public_id), 'balance_units': account.balance_units,
                         'has_purchase': wallet.has_purchase(account)})


@csrf_exempt
def usage(request):
    data = _internal_json(request)
    session_id = data.get('session_id')
    try:
        public_id = uuid.UUID(str(data.get('account_id')))
    except ValueError:
        return _error('bad_request', 400)
    if (not isinstance(session_id, str) or not SESSION_ID.match(session_id)
            or not all(_whole(data.get(name), upper) for name, upper in LIMITS.items())):
        return _error('bad_request', 400)
    account = Account.objects.filter(public_id=public_id).first()
    if account is None:
        return _error('unknown_account', 404)
    charged, balance = wallet.record_usage(account, session_id, data['seq'], data['stt_ms_out'], data['stt_ms_in'],
                                           data['tts_chars'])
    return JsonResponse({'charged_units': charged, 'balance_units': balance})
