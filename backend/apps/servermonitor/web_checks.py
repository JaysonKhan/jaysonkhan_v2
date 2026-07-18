"""
HTTP / SSL / journal-error / database probes for the owner bot.

Everything here is collection only — formatting lives in formatters.py.
All probes degrade to an error string per target instead of raising, so a
single unreachable site never kills a whole /web or /ssl reply.
"""
from __future__ import annotations

import re
import shutil
import socket
import ssl
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

# edustats.uz (and friends) 403 non-browser UAs — probe with a browser UA,
# exactly like deploy.sh health checks do.
BROWSER_UA = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)

# (label, url) — public sites first, then localhost-only internal APIs.
PUBLIC_SITES: list[tuple[str, str]] = [
    ('jaysonkhan.com', 'https://jaysonkhan.com/health/'),
    ('uzexam.uz', 'https://uzexam.uz/'),
    ('edustats.uz', 'https://edustats.uz/'),
    ('vaygo.uz', 'https://vaygo.uz/'),
]
INTERNAL_APIS: list[tuple[str, str]] = [
    ('edustats bot API', 'http://127.0.0.1:8433/api/v1/health'),
    ('vaygo API', 'http://127.0.0.1:8101/api/v1/health/'),
]

SSL_DOMAINS = ['jaysonkhan.com', 'uzexam.uz', 'edustats.uz', 'vaygo.uz']

# journalctl error scan — app units + nginx (infra noise like postgres
# autovacuum chatter is not worth counting).
ERROR_SCAN_UNITS = [
    'jaysonkhan', 'uzexam', 'uzexam-bot',
    'edustats-web', 'edustats-bot',
    'vaygo-web', 'vaygo-bot', 'nginx',
]
_ERROR_RE = re.compile(r'error|critical|traceback|exception', re.IGNORECASE)

_JOURNALCTL = (
    shutil.which('journalctl', path='/usr/bin:/bin:/usr/sbin:/sbin')
    or '/usr/bin/journalctl'
)
_SUDO = shutil.which('sudo', path='/usr/bin:/bin') or '/usr/bin/sudo'


@dataclass
class HttpCheck:
    label: str
    url: str
    status: int  # 0 = connection failure
    ms: int
    error: str = ''
    internal: bool = False


@dataclass
class SslCheck:
    domain: str
    days_left: int
    expires: str
    error: str = ''


@dataclass
class ErrorScan:
    unit: str
    count: int
    sample: str = ''  # last matching line, trimmed
    error: str = ''


def check_http() -> list[HttpCheck]:
    results: list[HttpCheck] = []
    with httpx.Client(
        timeout=8.0, follow_redirects=True, headers={'User-Agent': BROWSER_UA},
    ) as client:
        for label, url in PUBLIC_SITES + INTERNAL_APIS:
            internal = url.startswith('http://127.')
            start = time.monotonic()
            try:
                resp = client.get(url)
                ms = int((time.monotonic() - start) * 1000)
                results.append(HttpCheck(label, url, resp.status_code, ms, internal=internal))
            except Exception as exc:  # noqa: BLE001 — per-site degrade
                ms = int((time.monotonic() - start) * 1000)
                results.append(HttpCheck(label, url, 0, ms, error=str(exc)[:80], internal=internal))
    return results


def check_ssl(domains: list[str] | None = None) -> list[SslCheck]:
    results: list[SslCheck] = []
    for domain in domains or SSL_DOMAINS:
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=6) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
            not_after = cert.get('notAfter', '')
            expires_ts = ssl.cert_time_to_seconds(not_after)
            expires_dt = datetime.fromtimestamp(expires_ts, tz=timezone.utc)
            days_left = (expires_dt - datetime.now(tz=timezone.utc)).days
            results.append(SslCheck(domain, days_left, expires_dt.strftime('%Y-%m-%d')))
        except Exception as exc:  # noqa: BLE001
            results.append(SslCheck(domain, -1, '', error=str(exc)[:80]))
    return results


def scan_journal_errors(hours: int = 6) -> list[ErrorScan]:
    """Count error-ish lines per unit in the last N hours (capped sample)."""
    results: list[ErrorScan] = []
    for unit in ERROR_SCAN_UNITS:
        try:
            r = subprocess.run(
                [_JOURNALCTL, '-u', unit, '--since', f'-{hours}h',
                 '-n', '4000', '--no-pager', '-o', 'cat'],
                capture_output=True, text=True, timeout=15,
            )
            count = 0
            sample = ''
            for line in r.stdout.splitlines():
                if _ERROR_RE.search(line):
                    count += 1
                    sample = line.strip()[:120]
            results.append(ErrorScan(unit, count, sample))
        except FileNotFoundError:
            results.append(ErrorScan(unit, -1, error='journalctl yo\'q'))
        except Exception as exc:  # noqa: BLE001
            results.append(ErrorScan(unit, -1, error=str(exc)[:60]))
    return results


def check_databases() -> tuple[list[dict], int, str]:
    """Postgres DB sizes + active connection count via psql (as postgres).

    Returns (rows, connections, error). rows = [{'name': ..., 'size': ...}].
    The service runs as root, so ``sudo -u postgres`` needs no sudoers entry.
    """
    query = (
        'SELECT datname, pg_size_pretty(pg_database_size(datname)) '
        'FROM pg_database WHERE NOT datistemplate '
        'ORDER BY pg_database_size(datname) DESC'
    )
    try:
        r = subprocess.run(
            [_SUDO, '-n', '-u', 'postgres', 'psql', '-tA', '-F', '|', '-c', query],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            return [], 0, (r.stderr.strip() or 'psql xato')[:120]
        rows = []
        for line in r.stdout.strip().splitlines():
            if '|' in line:
                name, size = line.split('|', 1)
                rows.append({'name': name.strip(), 'size': size.strip()})

        conn = subprocess.run(
            [_SUDO, '-n', '-u', 'postgres', 'psql', '-tA', '-c',
             'SELECT count(*) FROM pg_stat_activity'],
            capture_output=True, text=True, timeout=10,
        )
        connections = int(conn.stdout.strip() or 0) if conn.returncode == 0 else 0
        return rows, connections, ''
    except Exception as exc:  # noqa: BLE001
        return [], 0, str(exc)[:120]
