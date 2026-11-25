"""My Services ingestion API — `POST /api/services/v1/telemetry/` and `/feedback/`.

Contract: LiveBridge repo `docs/telemetry-api.md` (v1). The client is open source, so these are
public and unauthenticated: no session, no cookies, CSRF-exempt (DRF APIView without
SessionAuthentication), strict validation, our own rate limits (`apptelemetry.ratelimit`) with
the contract's `{"error": "rate_limited"}` body. Bodies are never logged; no raw IP is stored.
"""
import json

from apptelemetry import ratelimit
from apptelemetry.services import TelemetryService
from apptelemetry.validation import (
    MAX_BODY_BYTES,
    EnvelopeError,
    parse_envelope,
    parse_feedback,
)
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

# Feedback is at most 2000 characters; anything near this is not a real form submission.
FEEDBACK_MAX_BODY_BYTES = 32 * 1024


def _error(code: str, http_status: int) -> Response:
    return Response({'error': code}, status=http_status)


def _rate_limited(retry_after: int) -> Response:
    response = _error('rate_limited', status.HTTP_429_TOO_MANY_REQUESTS)
    response['Retry-After'] = str(retry_after)
    return response


def _read_json(request, max_bytes: int):
    """Decoded JSON body, or raises EnvelopeError (413 'too_large' / 400 'bad_json')."""
    try:
        declared = int(request.META.get('CONTENT_LENGTH') or 0)
    except ValueError:
        declared = 0
    if declared > max_bytes:
        raise EnvelopeError('too_large', status=413)
    body = request._request.body  # raw bytes; DRF's parsers are not used here
    if len(body) > max_bytes:
        raise EnvelopeError('too_large', status=413)
    try:
        return json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise EnvelopeError('bad_json') from None


class _PublicIngestView(APIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)
    throttle_classes = ()  # DRF throttles key on REMOTE_ADDR/XFF; we limit in apptelemetry.ratelimit
    http_method_names = ('post', 'options')


class TelemetryIngestView(_PublicIngestView):
    def post(self, request):
        retry = ratelimit.hit(ratelimit.TELEMETRY_PER_ADDRESS, ratelimit.address_hash(request))
        if retry:
            return _rate_limited(retry)
        try:
            envelope = parse_envelope(_read_json(request, MAX_BODY_BYTES))
        except EnvelopeError as exc:
            return _error(exc.code, exc.status)
        retry = ratelimit.hit(
            ratelimit.RECORDS_PER_INSTALL, str(envelope['install_id']), amount=len(envelope['records']),
        )
        if retry:
            return _rate_limited(retry)
        accepted, ignored = TelemetryService().ingest(envelope)
        return Response({'accepted': accepted, 'ignored': ignored}, status=status.HTTP_202_ACCEPTED)


class FeedbackView(_PublicIngestView):
    def post(self, request):
        retry = ratelimit.hit(ratelimit.FEEDBACK_PER_ADDRESS, ratelimit.address_hash(request))
        if retry:
            return _rate_limited(retry)
        try:
            data = _read_json(request, FEEDBACK_MAX_BODY_BYTES)
        except EnvelopeError as exc:
            # The contract lists only 201/400/429 for feedback, so an oversized body is a 400.
            return _error(exc.code, status.HTTP_400_BAD_REQUEST)
        try:
            fields = parse_feedback(data)
        except EnvelopeError as exc:
            return _error(exc.code, status.HTTP_400_BAD_REQUEST)
        TelemetryService().create_feedback(fields)
        return Response({'ok': True}, status=status.HTTP_201_CREATED)
