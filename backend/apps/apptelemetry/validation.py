"""Validation of the telemetry / feedback wire format (contract: LiveBridge `docs/telemetry-api.md` v1).

Pure functions over already-decoded JSON. Anything a client sends is untrusted: unknown keys are
ignored, integers are clamped to 0…600 000, a record that breaks its type's rules is dropped and
counted as ignored. Only a broken envelope rejects the whole request.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .models import APPS, NO_TURN, UI_LANGUAGES, TelemetryRecord

MAX_BODY_BYTES = 256 * 1024
MAX_RECORDS = 500
INT_MAX = 600_000
SCHEMA = 1
MESSAGE_MAX = 2000
EMAIL_MAX = 254
# Bug reports: the whole body, the diagnostic log and the device object (UTF-8 bytes).
BUG_REPORT_MAX_BODY_BYTES = 320 * 1024
LOG_MAX_BYTES = 256 * 1024
DEVICES_MAX_BYTES = 16 * 1024
CONNECTION_MODES = ('account', 'keys', 'gateway', 'none')
# A client clock this far ahead is not trusted: the record is ignored.
MAX_CLOCK_SKEW = timedelta(days=1)

DIRECTIONS = ('out', 'in')
MODES = ('captions', 'incoming', 'bidirectional')
# Session languages: the codes of the client's language table (ISO 639-1, or 639-3 where there is none).
LANG_RE = re.compile(r'[a-z]{2,3}')
DEFAULT_MY_LANG = 'uz'
OUT_COMMITS = ('manual', 'vad', 'turn_prediction')
RATINGS = ('good', 'bad', 'none')
ERROR_CODE_RE = re.compile(r'[a-z0-9_]{1,48}')

# wire key -> model field, for the optional integers of a `turn` record
TURN_INTS = {
    'e2eMs': 'e2e_ms',
    'sttCommitMs': 'stt_commit_ms',
    'translateFirstMs': 'translate_first_ms',
    'translateTotalMs': 'translate_total_ms',
    'ttsFirstAudioMs': 'tts_first_audio_ms',
    'ttsTotalMs': 'tts_total_ms',
    'audioMs': 'audio_ms',
    'sourceChars': 'source_chars',
    'translationChars': 'translation_chars',
}


class EnvelopeError(ValueError):
    """The request as a whole is invalid. `code` is the client-facing error string."""

    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code = code
        self.status = status


class _Invalid(Exception):
    """One record breaks its type's rules."""


# ── primitives ──────────────────────────────────────────────────────────────

def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def clamp(value: int) -> int:
    return max(0, min(INT_MAX, value))


def _int(record: dict, key: str) -> int:
    value = record.get(key)
    if not _is_int(value):
        raise _Invalid(key)
    return clamp(value)


def _optional_int(record: dict, key: str) -> int | None:
    value = record.get(key)
    return clamp(value) if _is_int(value) else None


def _choice(record: dict, key: str, choices: tuple) -> str:
    value = record.get(key)
    if value not in choices:
        raise _Invalid(key)
    return value


def _lang(value) -> str:
    if not isinstance(value, str) or not LANG_RE.fullmatch(value):
        raise _Invalid('lang')
    return value


def optional_str(value, max_len: int) -> str:
    """A short optional string; anything else (wrong type, too long) is dropped."""
    if isinstance(value, str) and len(value) <= max_len:
        return value.strip()
    return ''


def parse_uuid4(value) -> uuid.UUID | None:
    if not isinstance(value, str) or len(value) != 36:
        return None
    try:
        parsed = uuid.UUID(value)
    except ValueError:
        return None
    return parsed if parsed.version == 4 else None


def parse_time(value) -> datetime | None:
    """ISO-8601 with an explicit offset (the contract sends UTC, `Z`), returned in UTC."""
    if not isinstance(value, str) or not 10 <= len(value) <= 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(dt_timezone.utc)


def ui_language(value) -> str:
    return value if value in UI_LANGUAGES else ''


# ── telemetry ───────────────────────────────────────────────────────────────

def parse_envelope(data) -> dict:
    """Validate the telemetry envelope. Raises EnvelopeError; returns the cleaned envelope."""
    if not isinstance(data, dict):
        raise EnvelopeError('bad_json')
    if data.get('app') not in APPS:
        raise EnvelopeError('unknown_app')
    if data.get('schema') != SCHEMA or not _is_int(data.get('schema')):
        raise EnvelopeError('bad_schema')
    install_id = parse_uuid4(data.get('install_id'))
    if install_id is None:
        raise EnvelopeError('bad_install_id')
    records = data.get('records')
    if not isinstance(records, list) or not records:
        raise EnvelopeError('no_records')
    if len(records) > MAX_RECORDS:
        raise EnvelopeError('too_large', status=413)
    return {
        'app': data['app'],
        'install_id': install_id,
        'app_version': optional_str(data.get('app_version'), 32),
        'os_version': optional_str(data.get('os_version'), 64),
        'ui_language': ui_language(data.get('ui_language')),
        'records': records,
    }


def parse_record(record, now: datetime) -> dict | None:
    """Model field values for one record, or None when it is invalid (counted as ignored)."""
    try:
        return _parse_record(record, now)
    except _Invalid:
        return None


def _parse_record(record, now: datetime) -> dict:
    if not isinstance(record, dict):
        raise _Invalid('record')
    kind = record.get('type')
    if kind not in TelemetryRecord.Type.values:
        raise _Invalid('type')
    t = parse_time(record.get('t'))
    if t is None or t > now + MAX_CLOCK_SKEW:
        raise _Invalid('t')
    session = record.get('session')
    if not _is_int(session) or session < 0:
        raise _Invalid('session')

    fields = {'type': kind, 't': t, 'session': clamp(session), 'turn_id': NO_TURN}
    T = TelemetryRecord.Type

    if kind == T.SESSION_START:
        fields['mode'] = _choice(record, 'mode', MODES)
        # `myLang` is optional (clients older than the language choice always spoke Uzbek).
        fields['my_lang'] = _lang(record.get('myLang', DEFAULT_MY_LANG))
        fields['target_lang'] = _lang(record.get('targetLang'))
        if fields['my_lang'] == fields['target_lang']:
            raise _Invalid('lang')
        fields['out_commit'] = _choice(record, 'outCommit', OUT_COMMITS)
    elif kind == T.TURN:
        fields['direction'] = _choice(record, 'direction', DIRECTIONS)
        fields['turn_id'] = _int(record, 'turnId')
        for key, field in TURN_INTS.items():
            fields[field] = _optional_int(record, key)
        fields['model'] = optional_str(record.get('model'), 64)
    elif kind == T.E2E:
        fields['direction'] = _choice(record, 'direction', DIRECTIONS)
        fields['turn_id'] = _int(record, 'turnId')
        fields['e2e_ms'] = _int(record, 'e2eMs')
    elif kind == T.EMPTY_TURN:
        fields['direction'] = _choice(record, 'direction', DIRECTIONS)
    elif kind == T.ERROR:
        code = record.get('code')
        if not isinstance(code, str) or not ERROR_CODE_RE.fullmatch(code):
            raise _Invalid('code')
        fields['code'] = code
        direction = record.get('direction')
        fields['direction'] = direction if direction in DIRECTIONS else ''
        fatal = record.get('fatal', False)
        if not isinstance(fatal, bool):
            raise _Invalid('fatal')
        fields['fatal'] = fatal
    elif kind == T.RATING:
        fields['direction'] = _choice(record, 'direction', DIRECTIONS)
        fields['turn_id'] = _int(record, 'turnId')
        fields['rating'] = _choice(record, 'rating', RATINGS)
    elif kind == T.SESSION_END:
        fields['duration_sec'] = _int(record, 'durationSec')
        fields['turns'] = _int(record, 'turns')
    # T.RECONNECT has no extra fields.
    return fields


# ── feedback ────────────────────────────────────────────────────────────────

def _message_install_email(data) -> tuple[str, uuid.UUID | None, str]:
    """The fields feedback and bug reports share: app, message, install id, e-mail. Raises EnvelopeError (400)."""
    if not isinstance(data, dict):
        raise EnvelopeError('bad_json')
    if data.get('app') not in APPS:
        raise EnvelopeError('unknown_app')
    message = data.get('message')
    if not isinstance(message, str) or not message.strip() or len(message) > MESSAGE_MAX:
        raise EnvelopeError('bad_message')

    install_id = None
    if data.get('install_id') is not None:
        install_id = parse_uuid4(data['install_id'])
        if install_id is None:
            raise EnvelopeError('bad_install_id')

    email = data.get('email')
    if email is None or email == '':
        email = ''
    else:
        if not isinstance(email, str) or len(email) > EMAIL_MAX:
            raise EnvelopeError('bad_email')
        email = email.strip()
        try:
            validate_email(email)
        except ValidationError:
            raise EnvelopeError('bad_email') from None
    return message.strip(), install_id, email


def parse_feedback(data) -> dict:
    """Validate a feedback body. Raises EnvelopeError (always 400); returns cleaned fields."""
    message, install_id, email = _message_install_email(data)

    rating = data.get('rating')
    if rating is not None and (not _is_int(rating) or not 1 <= rating <= 5):
        raise EnvelopeError('bad_rating')

    return {
        'app': data['app'],
        'install_id': install_id,
        'message': message,
        'email': email,
        'rating': rating,
        'app_version': optional_str(data.get('app_version'), 32),
        'ui_language': ui_language(data.get('ui_language')),
    }


# ── bug reports ─────────────────────────────────────────────────────────────

def parse_bug_report(data) -> dict:
    """Validate a bug report body. Raises EnvelopeError (400); returns cleaned fields."""
    message, install_id, email = _message_install_email(data)

    devices = data.get('devices')
    if devices is None:
        devices = {}
    elif not isinstance(devices, dict) or len(json.dumps(devices).encode()) > DEVICES_MAX_BYTES:
        raise EnvelopeError('bad_devices')

    log = data.get('log')
    if log is None:
        log = ''
    elif not isinstance(log, str) or len(log.encode()) > LOG_MAX_BYTES:
        raise EnvelopeError('bad_log')

    mode = data.get('connection_mode')
    return {
        'app': data['app'],
        'install_id': install_id,
        'message': message,
        'email': email,
        'app_version': optional_str(data.get('app_version'), 32),
        'os_version': optional_str(data.get('os_version'), 64),
        'platform': optional_str(data.get('platform'), 32),
        'ui_language': ui_language(data.get('ui_language')),
        'connection_mode': mode if mode in CONNECTION_MODES else '',
        'device_info': devices,
        'log': log,
    }
