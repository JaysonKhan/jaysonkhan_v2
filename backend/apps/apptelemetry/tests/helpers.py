"""Builders shared by the My Services tests."""
import json
import uuid
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

TELEMETRY_URL = '/api/services/v1/telemetry/'
FEEDBACK_URL = '/api/services/v1/feedback/'
CLIENT_IP = '203.0.113.77'


def iso(dt: datetime) -> str:
    return dt.astimezone(dt_timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def recent(minutes: int = 0) -> str:
    return iso(datetime.now(dt_timezone.utc) - timedelta(minutes=minutes))


def session_start(session=1, target='en', minutes=10, my=None):
    record = {'type': 'session_start', 't': recent(minutes), 'session': session, 'mode': 'bidirectional',
              'targetLang': target, 'outCommit': 'manual'}
    if my:
        record['myLang'] = my
    return record


def turn(session=1, turn_id=1, e2e=1350, direction='out', minutes=9, **extra):
    record = {'type': 'turn', 't': recent(minutes), 'session': session, 'direction': direction,
              'turnId': turn_id, 'e2eMs': e2e, 'sttCommitMs': 302, 'model': 'gemini-3.5-flash-lite'}
    record.update(extra)
    return record


def envelope(records, install_id=None, **extra):
    body = {'app': 'livebridge', 'schema': 1, 'install_id': install_id or str(uuid.uuid4()),
            'app_version': '1.0.0+1', 'os_version': 'macOS 26.6.2', 'ui_language': 'uz', 'records': records}
    body.update(extra)
    return body


class ServicesTestCase(TestCase):
    def setUp(self):
        cache.clear()  # rate-limit counters and the public stats cache live in the cache

    def post_json(self, url, body, ip=CLIENT_IP, client=None):
        raw = body if isinstance(body, (str, bytes)) else json.dumps(body)
        return (client or self.client).post(url, data=raw, content_type='application/json', HTTP_X_REAL_IP=ip)

    def send(self, records, install_id=None, ip=CLIENT_IP, **extra):
        return self.post_json(TELEMETRY_URL, envelope(records, install_id, **extra), ip=ip)

    @staticmethod
    def livebridge_url():
        return reverse('services_livebridge')
