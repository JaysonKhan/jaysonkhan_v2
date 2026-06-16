"""Monthly log report → Telegram owner, then rotate (truncate) the logs.

At the start of each month a cron fires this command. It:
  1. Parses the production log files (``django_errors.log`` + ``security.log``)
     into a compact summary — 4xx / 5xx counts, real 500 signatures, blocked
     bot-scan stats, top offending paths & IPs.
  2. Sends an HTML summary message to the Telegram owner, plus each non-empty
     log gzipped as a document (size + sha256 caption, EduStats-backup style).
  3. ONLY after every send succeeds: archives are already in Telegram, so the
     live logs are truncated in place (copytruncate — safe with the append-mode
     FileHandler, no gunicorn restart needed). This is the "tozalab borish" step.

Usage:
    python manage.py monthly_log_report              # send + truncate (cron)
    python manage.py monthly_log_report --dry-run    # print summary, send nothing, keep logs
    python manage.py monthly_log_report --no-truncate # send but keep logs
    python manage.py monthly_log_report --send        # alias: explicit send (default)

Cron (1st of month, 00:05; reports the month that just ended):
    5 0 1 * * ... cron_run monthly_log_report
"""
from __future__ import annotations

import gzip
import hashlib
import os
import re
import tempfile
from collections import Counter

from core.services import SiteSettingsService
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from interactions.notifications.telegram_api import TelegramBotAPI

# Log line: "LEVEL 2026-06-14 23:21:57,704 <module> <pid> <thread> <message>"
# (verbose formatter). security.log is prefixed "[SECURITY] " — we strip it.
LINE_RE = re.compile(
    r'^(?:\[SECURITY\] )?(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL) '
    r'(?P<date>\d{4}-\d{2}-\d{2}) [\d:,]+ '
    r'(?P<module>\S+)(?: \d+ \d+)? (?P<msg>.*)$'
)
IP_RE = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
# Trailing request path inside a message, e.g. "Not Found: /x.php"
PATH_RE = re.compile(r'(/\S*)')

UZ_MONTHS = [
    '', 'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
    'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr',
]


def _classify(msg: str) -> str | None:
    """Map a django.request log message to an HTTP-status bucket."""
    if msg.startswith('Not Found:'):
        return '404'
    if msg.startswith('Unauthorized'):
        return '401'
    if msg.startswith('Forbidden'):
        return '403'
    if msg.startswith('Bad Request:'):
        return '400'
    if msg.startswith('Internal Server Error:'):
        return '500'
    if 'Invalid HTTP_HOST header' in msg:
        return 'hosthdr'
    return None


def _norm_signature(text: str) -> str:
    """Collapse a traceback's last meaningful line into a dedupe key."""
    t = re.sub(r'0x[0-9a-fA-F]+', '0x', text)
    t = re.sub(r'\d+', 'N', t)
    return t.strip()[:200]


def parse_log(path: str) -> dict:
    """Single-pass parse of a Django log file into a stats dict."""
    stats = {
        'lines': 0,
        'levels': Counter(),
        'status': Counter(),          # 404/403/500/401/400/hosthdr
        'blocked': 0,                  # security_middleware blocked scans
        'scan_paths': Counter(),       # top probed paths (4xx + blocked)
        'attacker_ips': Counter(),     # IPs from blocked-scan lines
        'err_signatures': Counter(),   # real ERROR signatures (500 tracebacks)
        'first_date': None,
        'last_date': None,
    }
    if not os.path.isfile(path):
        return stats

    pending_err = None  # accumulate traceback lines after an ERROR
    with open(path, 'r', errors='replace') as fh:
        for raw in fh:
            stats['lines'] += 1
            m = LINE_RE.match(raw)
            if not m:
                # continuation line (traceback body) — append to pending error
                if pending_err is not None:
                    pending_err.append(raw.rstrip())
                continue

            # flush a finished error block into a signature
            if pending_err is not None:
                stats['err_signatures'][_signature_of(pending_err)] += 1
                pending_err = None

            level = m.group('level')
            module = m.group('module')
            msg = m.group('msg')
            date = m.group('date')
            stats['levels'][level] += 1
            stats['first_date'] = stats['first_date'] or date
            stats['last_date'] = date

            if 'Blocked extension request' in msg or '[Security] Blocked' in msg:
                stats['blocked'] += 1
                ip = IP_RE.search(msg)
                if ip:
                    stats['attacker_ips'][ip.group(1)] += 1
                p = PATH_RE.search(msg)
                if p:
                    stats['scan_paths'][p.group(1)[:80]] += 1
                continue

            bucket = _classify(msg)
            if bucket:
                stats['status'][bucket] += 1
                if bucket in ('404', '403') and module == 'log':
                    p = PATH_RE.search(msg)
                    if p:
                        stats['scan_paths'][p.group(1)[:80]] += 1

            if level in ('ERROR', 'CRITICAL'):
                # start a new error block; first line is the message itself
                pending_err = [msg]

    if pending_err is not None:
        stats['err_signatures'][_signature_of(pending_err)] += 1
    return stats


def _signature_of(block: list[str]) -> str:
    """Build a dedupe signature from an error + its traceback block.

    Prefers the final exception line (``XError: ...``); falls back to the
    request line (``Internal Server Error: /path``).
    """
    exc_line = ''
    for line in reversed(block):
        s = line.strip()
        if re.match(r'^[A-Za-z_][\w.]*(Error|Exception|Warning):', s):
            exc_line = s
            break
    head = block[0].strip()
    sig = f'{head} → {exc_line}' if exc_line else head
    return _norm_signature(sig)


def _gzip_to_temp(src_path: str, out_name: str) -> tuple[str, int, str] | None:
    """gzip ``src_path`` into a temp file. Returns (temp_path, size, sha256)."""
    if not os.path.isfile(src_path) or os.path.getsize(src_path) == 0:
        return None
    tmp_dir = tempfile.gettempdir()
    out_path = os.path.join(tmp_dir, out_name)
    h = hashlib.sha256()
    with open(src_path, 'rb') as fin, gzip.open(out_path, 'wb') as fout:
        for chunk in iter(lambda: fin.read(65536), b''):
            h.update(chunk)
            fout.write(chunk)
    size = os.path.getsize(out_path)
    return out_path, size, h.hexdigest()


def _fmt_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f'{n / 1024 / 1024:.1f}M'
    if n >= 1024:
        return f'{n / 1024:.1f}K'
    return f'{n}B'


def build_summary(period_label: str, host: str, err: dict, sec: dict) -> str:
    """Compose the HTML Telegram message from parsed django_errors stats."""
    st = err['status']
    real_5xx = st.get('500', 0)
    total_4xx = st.get('404', 0) + st.get('403', 0) + st.get('401', 0) + st.get('400', 0)
    blocked = err['blocked'] + sec['blocked']
    verdict = '✅ Server sog‘lom' if real_5xx == 0 else '⚠️ Diqqat: real xatolar bor'

    lines = [
        f'📋 <b>Oylik log hisoboti — {period_label}</b>',
        f'<code>{host}</code>',
        '',
        verdict,
        '',
        f'🔴 <b>5xx (real xatolar):</b> {real_5xx}',
        f'🟡 <b>4xx:</b> {total_4xx}  '
        f'<i>(404:{st.get("404", 0)} · 403:{st.get("403", 0)} · '
        f'401:{st.get("401", 0)} · 400:{st.get("400", 0)})</i>',
        f'🛡 <b>Bloklangan skanerlar:</b> {blocked}',
        f'📊 <b>Jami:</b> ERROR {err["levels"].get("ERROR", 0)} · '
        f'WARNING {err["levels"].get("WARNING", 0)}',
    ]

    if real_5xx:
        lines.append('')
        lines.append('🔎 <b>Top server xatolari:</b>')
        for sig, cnt in err['err_signatures'].most_common(5):
            short = sig if len(sig) <= 110 else sig[:107] + '…'
            lines.append(f'• <code>{_esc(short)}</code> ×{cnt}')

    top_scans = err['scan_paths'].most_common(5)
    if top_scans:
        lines.append('')
        lines.append('🎯 <b>Eng ko‘p urinilgan yo‘llar:</b>')
        for p, cnt in top_scans:
            lines.append(f'• <code>{_esc(p)}</code> ×{cnt}')

    top_ips = (err['attacker_ips'] + sec['attacker_ips']).most_common(5)
    if top_ips:
        lines.append('')
        lines.append('🌐 <b>Faol skaner IP‘lari:</b>')
        for ip, cnt in top_ips:
            lines.append(f'• <code>{ip}</code> ×{cnt}')

    span = ''
    if err['first_date'] and err['last_date']:
        span = f'{err["first_date"]} — {err["last_date"]} · '
    lines.append('')
    lines.append(
        f'<i>Loglar arxivlandi va tozalandi. '
        f'{span}{err["lines"] + sec["lines"]:,} qator.</i>'
    )
    return '\n'.join(lines)


def _esc(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class Command(BaseCommand):
    help = 'Send the monthly log report to the Telegram owner, then rotate logs.'

    LOG_FILES = ('django_errors.log', 'security.log')

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Print the summary; send nothing, keep logs.')
        parser.add_argument('--no-truncate', action='store_true',
                            help='Send the report but do NOT truncate the logs.')
        parser.add_argument('--send', action='store_true',
                            help='Explicit send (default behaviour).')

    def handle(self, *args, **opts):
        logs_dir = getattr(settings, 'LOGS_DIR', None) or os.path.join(
            settings.BASE_DIR, 'logs')
        err_path = os.path.join(logs_dir, 'django_errors.log')
        sec_path = os.path.join(logs_dir, 'security.log')

        err = parse_log(err_path)
        sec = parse_log(sec_path)

        # Period label = the month that just ended (cron fires on the 1st).
        # Computed arithmetically (no timedelta import — keeps the formatter
        # from stripping it, and sidesteps any DST edge).
        now = timezone.localtime()
        prev_year = now.year if now.month > 1 else now.year - 1
        prev_month = now.month - 1 if now.month > 1 else 12
        period_label = f'{UZ_MONTHS[prev_month]} {prev_year}'
        host = os.uname().nodename

        summary = build_summary(period_label, host, err, sec)

        if opts['dry_run']:
            self.stdout.write(summary.replace('<b>', '').replace('</b>', '')
                              .replace('<code>', '').replace('</code>', '')
                              .replace('<i>', '').replace('</i>', ''))
            self.stdout.write(self.style.WARNING(
                '\n[dry-run] nothing sent, logs untouched'))
            return

        site = SiteSettingsService.get()
        if not site.telegram_owner_id:
            self.stderr.write(self.style.ERROR(
                'telegram_owner_id not set in SiteSettings — aborting'))
            return

        api = TelegramBotAPI()
        tg_id = site.telegram_owner_id
        stamp = f'{prev_year}{prev_month:02d}'

        # 1) summary message
        msg_resp = api.send_message(tg_id, summary)
        if not (msg_resp and msg_resp.get('ok')):
            self.stderr.write(self.style.ERROR(
                'Summary send failed — logs NOT truncated (will retry next run)'))
            return

        # 2) gzip + send each non-empty log as a document
        sent_docs = []
        temps = []
        for fname in self.LOG_FILES:
            src = os.path.join(logs_dir, fname)
            packed = _gzip_to_temp(src, f'jaysonkhan_{fname}_{stamp}.gz')
            if not packed:
                continue
            tmp_path, size, sha = packed
            temps.append(tmp_path)
            caption = (f'{fname} · {period_label}\n'
                       f'{_fmt_size(size)} | sha256:{sha[:16]}')
            doc_resp = api.send_document(tg_id, tmp_path, caption=caption)
            if doc_resp and doc_resp.get('ok'):
                sent_docs.append(fname)
            else:
                self.stderr.write(self.style.ERROR(
                    f'{fname} document send failed — logs NOT truncated'))
                for t in temps:
                    _safe_unlink(t)
                return

        for t in temps:
            _safe_unlink(t)

        self.stdout.write(self.style.SUCCESS(
            f'Report sent to {tg_id} (docs: {", ".join(sent_docs) or "none"})'))

        # 3) rotate — truncate live logs (copytruncate; FileHandler is append-mode)
        if opts['no_truncate']:
            self.stdout.write('[--no-truncate] logs kept')
            return
        for fname in self.LOG_FILES:
            src = os.path.join(logs_dir, fname)
            if os.path.isfile(src):
                try:
                    os.truncate(src, 0)
                except OSError as exc:
                    self.stderr.write(self.style.WARNING(
                        f'truncate {fname} failed: {exc}'))
        self.stdout.write(self.style.SUCCESS('Logs truncated — fresh month started'))


def _safe_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass
