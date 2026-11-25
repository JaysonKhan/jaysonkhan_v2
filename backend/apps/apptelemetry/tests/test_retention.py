"""`manage.py purge_service_telemetry`: raw records older than 180 days go, everything else stays."""
import uuid
from datetime import timedelta
from io import StringIO

from apptelemetry.models import AppFeedback, AppInstall, TelemetryRecord
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone


class RetentionTest(TestCase):
    def test_deletes_only_old_records(self):
        now = timezone.now()
        install = AppInstall.objects.create(app='livebridge', install_id=uuid.uuid4(), turns_count=2)
        old = TelemetryRecord.objects.create(install=install, type='turn', t=now - timedelta(days=200), session=1,
                                             turn_id=1, received_at=now - timedelta(days=181))
        fresh = TelemetryRecord.objects.create(install=install, type='turn', t=now - timedelta(days=10), session=1,
                                               turn_id=2, received_at=now - timedelta(days=179))
        feedback = AppFeedback.objects.create(app='livebridge', message='eski', created_at=now - timedelta(days=400))

        out = StringIO()
        call_command('purge_service_telemetry', '--dry-run', stdout=out)
        self.assertIn('1 records', out.getvalue())
        self.assertEqual(TelemetryRecord.objects.count(), 2)

        call_command('purge_service_telemetry', stdout=out)
        self.assertIn('Deleted 1 records', out.getvalue())
        self.assertFalse(TelemetryRecord.objects.filter(pk=old.pk).exists())
        self.assertTrue(TelemetryRecord.objects.filter(pk=fresh.pk).exists())
        self.assertTrue(AppFeedback.objects.filter(pk=feedback.pk).exists())
        self.assertEqual(AppInstall.objects.get(pk=install.pk).turns_count, 2)
