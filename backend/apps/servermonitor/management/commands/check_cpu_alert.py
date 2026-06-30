"""
Check CPU usage and send alert if any core exceeds threshold.

Designed to run every 5-15 minutes via cron/systemd timer.

Defaults updated 2026-04-27 after a flurry of false positives:
  - threshold raised 75 → 85 (75 still triggers the yellow visual badge,
    but only 85+ pages the operator)
  - measurement window extended 1s → 5s (sustained sample — Postgres
    parallel queries and gunicorn worker boots regularly spike a single
    1s window without representing real overload)

Usage:
    python manage.py check_cpu_alert                  # 85% / 5s sample
    python manage.py check_cpu_alert --threshold 90   # custom threshold
    python manage.py check_cpu_alert --interval 1     # tighter sample
"""
from core.services import SiteSettingsService
from django.core.management.base import BaseCommand
from interactions.notifications.telegram_api import TelegramBotAPI
from servermonitor.formatters import format_cpu_alert
from servermonitor.metrics import collect_cpu

# Konsekutiv yuqori-CPU holati fayli (cron jarayonlar orasida saqlanadi —
# LocMem cache fresh-process'da yo'qoladi). Deploy build+warmup = bir martalik
# spike (bitta cron run); haqiqiy overload = ketma-ket bir necha run.
_STATE_FILE = '/var/tmp/cpu_alert_consec'


def _read_consec() -> int:
    try:
        with open(_STATE_FILE) as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def _write_consec(n: int) -> None:
    try:
        with open(_STATE_FILE, 'w') as f:
            f.write(str(n))
    except OSError:
        pass


class Command(BaseCommand):
    help = 'Check CPU cores and alert if above threshold (sustained 5s sample)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold', type=float, default=85.0,
            help='CPU percent threshold for alert (default: 85)',
        )
        parser.add_argument(
            '--interval', type=float, default=5.0,
            help='psutil sample window in seconds (default: 5 — sustained)',
        )
        parser.add_argument(
            '--consecutive', type=int, default=2,
            help="Ketma-ket necha cron-run yuqori bo'lsa page (default: 2 — "
                 "deploy build/warmup bir martalik spike'ni filtrlaydi)",
        )

    def handle(self, *args, **options):
        threshold = options['threshold']
        interval = options['interval']
        need = options['consecutive']
        cpu = collect_cpu(interval=interval)

        alert_text = format_cpu_alert(cpu, threshold=threshold)
        if not alert_text:
            _write_consec(0)  # tushdi → hisoblagich reset
            self.stdout.write(self.style.SUCCESS(
                f'All {cpu.core_count} cores below {threshold}% '
                f'(sampled over {interval}s) — no alert'
            ))
            return

        # Yuqori CPU — lekin DARHOL page qilmaymiz. Deploy build+warmup bir
        # martalik spike (bitta run). Faqat KETMA-KET `need` run yuqori bo'lsa
        # = haqiqiy sustained overload → page.
        consec = _read_consec() + 1
        _write_consec(consec)
        if consec < need:
            self.stdout.write(self.style.WARNING(
                f'High CPU ({consec}/{need} ketma-ket) — deploy-burst guard, '
                f'hali page qilinmadi'
            ))
            return

        site = SiteSettingsService.get()
        if not site.telegram_owner_id:
            self.stderr.write(self.style.ERROR('telegram_owner_id not set'))
            return

        api = TelegramBotAPI()
        api.send_message(site.telegram_owner_id, alert_text)
        _write_consec(0)  # page qilindi → reset (har run spam qilmaslik)
        self.stdout.write(self.style.WARNING(
            f'CPU alert sent to {site.telegram_owner_id} ({consec} ketma-ket run)'))
