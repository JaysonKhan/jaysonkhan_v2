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

        # Disk piggy-backs on this 10-min cron: a full disk kills EVERY site
        # at once and the daily 09:00 report can be 20h away. Runs first so a
        # CPU early-return never skips it.
        self._check_disk()

        cpu = collect_cpu(interval=interval)

        from interactions.notifications.lang import owner_lang
        alert_text = format_cpu_alert(cpu, threshold=threshold, lang=owner_lang())
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

    # ── Disk alert (≥90%, kuniga 1 marta) ────────────────────────────────────

    _DISK_THRESHOLD = 90.0
    _DISK_MARKER = '/var/tmp/disk_alert_sent'

    def _check_disk(self) -> None:
        """Alert once per day when any real partition crosses 90%."""
        from datetime import date

        from servermonitor.metrics import collect_partitions

        try:
            hot = [p for p in collect_partitions() if p.percent >= self._DISK_THRESHOLD]
        except Exception as exc:  # noqa: BLE001 — never break the CPU check
            self.stderr.write(f'disk check failed: {exc}')
            return

        today = date.today().isoformat()
        if not hot:
            # Threshold cleared — arm the alert again for the next breach.
            try:
                import os
                os.unlink(self._DISK_MARKER)
            except OSError:
                pass
            return

        try:
            with open(self._DISK_MARKER) as fh:
                if fh.read().strip() == today:
                    return  # bugun allaqachon yuborilgan
        except OSError:
            pass

        site = SiteSettingsService.get()
        if not site.telegram_owner_id:
            return

        from core.bot_i18n import t
        from interactions.notifications.lang import owner_lang
        lang = owner_lang()
        lines = [t('alert.disk_title', lang)]
        for p in hot:
            lines.append(
                f'  🔴 <code>{p.mountpoint}</code> — <b>{p.percent}%</b> '
                f'({p.used_gb}/{p.total_gb}GB)'
            )
        lines.append(t('alert.disk_advice', lang))
        TelegramBotAPI().send_message(site.telegram_owner_id, '\n'.join(lines))
        try:
            with open(self._DISK_MARKER, 'w') as fh:
                fh.write(today)
        except OSError:
            pass
        self.stdout.write(self.style.WARNING('Disk alert sent'))
