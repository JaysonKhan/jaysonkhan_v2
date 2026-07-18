"""
Dynamic admin IP allowlist — shared by every site on this server.

The owner Telegram bot (@Jaysonkhanbot) writes a single JSON file
(default ``/var/www/shared/admin_allowed_ips.json``); each Django app's
AdminIPRestrictionMiddleware unions the IPs from that file with its own
``.env`` ``ADMIN_ALLOWED_IPS`` base list at request time. The ``.env``
files are NEVER touched and no service restart is needed for an IP change.

File format (version 1):

    {
      "version": 1,
      "ips":     [{"ip": "1.2.3.4", "label": "uy", "added": "2026-07-18T12:00:00"}],
      "history": [{"op": "add", "ip": "1.2.3.4", "label": "uy",
                   "at": "2026-07-18T12:00:00", "by": 12345}]
    }

Rules:
  - Readers FAIL OPEN to [] — a missing or corrupt file must never lock the
    admin out (the .env base list still applies) and must never 500 a request.
  - Writes are atomic (tempfile in the same directory + os.replace) so a
    reader never sees a torn file.
  - uzexam / edustats-web carry their own trimmed read-only copy of
    ``get_dynamic_ips`` (per-repo copy is the workspace convention) — keep the
    on-disk format backward compatible.
"""
from __future__ import annotations

import base64
import ipaddress
import json
import logging
import os
import tempfile
from datetime import datetime

from django.conf import settings

logger = logging.getLogger('django.security')

DEFAULT_IPS_FILE = '/var/www/shared/admin_allowed_ips.json'

MAX_LABEL_LEN = 30
MAX_HISTORY = 50
MAX_IPS = 50

# Per-process read cache — invalidated whenever the file's (mtime_ns, size)
# changes. os.stat on admin-path requests only; negligible.
_cache: dict = {'key': None, 'ips': []}


def _ips_file() -> str:
    return getattr(settings, 'ADMIN_ALLOWED_IPS_FILE', DEFAULT_IPS_FILE)


def normalize_ip(raw: str) -> str | None:
    """Return the canonical text form of a valid IPv4/IPv6 address, else None."""
    try:
        return str(ipaddress.ip_address((raw or '').strip()))
    except ValueError:
        return None


def get_dynamic_ips() -> list[str]:
    """Bot-managed IPs from the shared file. Fails open to []."""
    path = _ips_file()
    try:
        st = os.stat(path)
    except OSError:
        return []
    key = (st.st_mtime_ns, st.st_size)
    if _cache['key'] == key:
        return _cache['ips']

    ips: list[str] = []
    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
        for entry in data.get('ips', []):
            ip = normalize_ip(entry.get('ip', '') if isinstance(entry, dict) else '')
            if ip:
                ips.append(ip)
    except Exception as exc:  # noqa: BLE001 — corrupt file must not 500 requests
        logger.warning('[allowed_ips] unreadable %s: %s', path, exc)
        ips = []

    # Cache even the failure result so a corrupt file isn't re-parsed per request.
    _cache['key'] = key
    _cache['ips'] = ips
    return ips


def load_data() -> dict:
    """Full file contents for the bot UI. Fails open to an empty structure."""
    try:
        with open(_ips_file(), encoding='utf-8') as fh:
            data = json.load(fh)
        if isinstance(data, dict) and isinstance(data.get('ips'), list):
            return data
    except OSError:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning('[allowed_ips] load_data failed: %s', exc)
    return {'version': 1, 'ips': [], 'history': []}


def _atomic_save(data: dict) -> tuple[bool, str]:
    """Write the JSON atomically (0644 so every app's worker can read it)."""
    path = _ips_file()
    directory = os.path.dirname(path) or '.'
    try:
        os.makedirs(directory, mode=0o755, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix='.admin_ips.')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                json.dump(data, fh, ensure_ascii=False, indent=1)
                fh.flush()
                os.fsync(fh.fileno())
            os.chmod(tmp_path, 0o644)
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        return True, ''
    except OSError as exc:
        logger.error('[allowed_ips] save failed: %s', exc)
        return False, str(exc)


def add_ip(raw_ip: str, *, label: str = '', by: int = 0) -> tuple[bool, str]:
    """Validate + append an IP. Returns (ok, human message — HTML-safe text)."""
    ip = normalize_ip(raw_ip)
    if not ip:
        return False, f'Noto\'g\'ri IP: {raw_ip.strip()[:40]}'

    label = ' '.join((label or '').split())[:MAX_LABEL_LEN]
    data = load_data()
    if any(e.get('ip') == ip for e in data['ips']):
        return False, f'{ip} allaqachon ro\'yxatda.'
    if len(data['ips']) >= MAX_IPS:
        return False, f'Ro\'yxat to\'la ({MAX_IPS} ta) — avval eskisini o\'chiring.'

    now = datetime.now().isoformat(timespec='seconds')
    data['ips'].append({'ip': ip, 'label': label, 'added': now})
    history = data.setdefault('history', [])
    history.append({'op': 'add', 'ip': ip, 'label': label, 'at': now, 'by': by})
    data['history'] = history[-MAX_HISTORY:]

    ok, err = _atomic_save(data)
    if not ok:
        return False, f'Yozib bo\'lmadi: {err}'
    return True, ip


def remove_ip(raw_ip: str, *, by: int = 0) -> tuple[bool, str]:
    """Remove a bot-managed IP. .env base IPs are not managed here."""
    ip = normalize_ip(raw_ip)
    if not ip:
        return False, f'Noto\'g\'ri IP: {raw_ip.strip()[:40]}'

    data = load_data()
    remaining = [e for e in data['ips'] if e.get('ip') != ip]
    if len(remaining) == len(data['ips']):
        return False, f'{ip} dinamik ro\'yxatda yo\'q (.env bazasini bot boshqarmaydi).'

    now = datetime.now().isoformat(timespec='seconds')
    data['ips'] = remaining
    history = data.setdefault('history', [])
    history.append({'op': 'remove', 'ip': ip, 'at': now, 'by': by})
    data['history'] = history[-MAX_HISTORY:]

    ok, err = _atomic_save(data)
    if not ok:
        return False, f'Yozib bo\'lmadi: {err}'
    return True, ip


# ── Deep-link helpers (t.me/<bot>?start=addip_<token>) ────────────────────────
# Telegram start payloads allow only [A-Za-z0-9_-], so the IP is carried as
# unpadded urlsafe base64 (IPv4 and IPv6 both fit the 64-char limit).

def encode_ip(ip: str) -> str:
    return base64.urlsafe_b64encode(ip.encode()).decode().rstrip('=')


def decode_ip(token: str) -> str | None:
    try:
        padded = token + '=' * (-len(token) % 4)
        return normalize_ip(base64.urlsafe_b64decode(padded.encode()).decode())
    except Exception:  # noqa: BLE001 — arbitrary user input
        return None
