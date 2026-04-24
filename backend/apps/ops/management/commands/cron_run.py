"""
Wrap any Django management command with execution logging.

Usage:
    python manage.py cron_run check_cpu_alert
    python manage.py cron_run <target> [args…] [--triggered-by=admin]

Creates a CronRun row, calls the target via call_command, captures
stdout/stderr, records duration + exit code. Re-emits output to real
streams so existing crontab logging keeps working.
"""
from __future__ import annotations

import io
import socket
import sys
import time
import traceback

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ops.models import CronRun, CronStatus, ManagedCron


MAX_OUTPUT_CHARS = 100_000


class Command(BaseCommand):
    help = 'Wrap another management command, logging its run to CronRun.'

    def add_arguments(self, parser):
        parser.add_argument('target', help='Target management command name.')
        parser.add_argument('target_args', nargs='*')
        parser.add_argument('--triggered-by', default='cron')

    def handle(self, *args, **opts):
        target = opts['target']
        target_args = list(opts['target_args'] or [])
        triggered_by = opts['triggered_by']

        ManagedCron.objects.get_or_create(
            command=target,
            defaults={
                'verbose_name': target.replace('_', ' ').title(),
                'enabled': True,
            },
        )

        run = CronRun.objects.create(
            command=target,
            args=target_args,
            status=CronStatus.RUNNING,
            triggered_by=triggered_by,
            hostname=socket.gethostname()[:80],
            meta={},
        )

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        start = time.monotonic()
        exit_code = 0
        error_summary = ''

        try:
            call_command(target, *target_args, stdout=stdout_buf, stderr=stderr_buf)
            status = CronStatus.SUCCESS
        except CommandError as e:
            status = CronStatus.FAILED
            exit_code = 1
            error_summary = f'CommandError: {e}'[:300]
            stderr_buf.write(f'\n✖ CommandError: {e}\n')
        except SystemExit as e:
            code = int(e.code) if isinstance(e.code, int) else 1
            status = CronStatus.SUCCESS if code == 0 else CronStatus.FAILED
            exit_code = code
            if code != 0:
                error_summary = f'SystemExit({code})'
                stderr_buf.write(f'\n✖ SystemExit({code})\n')
        except Exception as e:  # noqa: BLE001
            status = CronStatus.FAILED
            exit_code = 1
            error_summary = f'{type(e).__name__}: {e}'[:300]
            stderr_buf.write(f'\n✖ {type(e).__name__}: {e}\n')
            traceback.print_exc(file=stderr_buf)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        stdout_text = stdout_buf.getvalue()
        stderr_text = stderr_buf.getvalue()

        if stdout_text:
            sys.stdout.write(stdout_text)
        if stderr_text:
            sys.stderr.write(stderr_text)

        run.refresh_from_db(fields=['meta'])
        run.status = status
        run.finished_at = timezone.now()
        run.duration_ms = elapsed_ms
        run.exit_code = exit_code
        run.stdout = _clip(stdout_text)
        run.stderr = _clip(stderr_text)
        run.error_summary = error_summary
        run.save(update_fields=[
            'status', 'finished_at', 'duration_ms', 'exit_code',
            'stdout', 'stderr', 'error_summary',
        ])

        if status == CronStatus.FAILED:
            sys.exit(exit_code or 1)


def _clip(s: str) -> str:
    if len(s) <= MAX_OUTPUT_CHARS:
        return s
    kept = s[-MAX_OUTPUT_CHARS:]
    return f'[… truncated, {len(s) - MAX_OUTPUT_CHARS} chars dropped …]\n{kept}'
