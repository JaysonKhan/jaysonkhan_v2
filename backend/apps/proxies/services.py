"""Proxy pool: reading a provider's TXT export, importing it, publishing the shared file.

The shared file (default ``/var/www/shared/proxies.json``) is the ONLY interface to the other
sites on this server. UzExam and EduStats read it at call time with their own small reader
(per-repo copy, the same convention as ``core.allowed_ips``), so a change made in the admin
applies there without a deploy or a restart.

File format, version 1 — the readers live in other repos, keep it backward compatible:

    {"version": 1, "updated_at": "2026-11-25T12:00:00", "proxies": ["http://user:pass@1.2.3.4:3129"]}

Only active proxies are published. The file holds provider credentials, so it is written 0600
and handed to the owner of its directory: this service runs as root, the readers run as
``deploy``, and ``/var/www/shared`` belongs to ``deploy``.
"""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Proxy

logger = logging.getLogger(__name__)

DEFAULT_POOL_FILE = '/var/www/shared/proxies.json'

# ``user:pass@host:port`` (the provider's export), also without credentials or with ``http://``.
_LINE = re.compile(
    r'^(?:http://)?'
    r'(?:(?P<username>[^:@\s]+):(?P<password>[^@\s]*)@)?'
    r'(?P<host>[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?)'
    r':(?P<port>\d{1,5})/?$'
)


@dataclass(frozen=True)
class Entry:
    host: str
    port: int
    username: str = ''
    password: str = ''

    @property
    def key(self) -> tuple:
        return self.host, self.port, self.username


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    invalid_lines: list = field(default_factory=list)


def pool_file() -> str:
    return getattr(settings, 'PROXY_POOL_FILE', DEFAULT_POOL_FILE)


def parse_proxy_list(text: str) -> tuple[list[Entry], list[int]]:
    """Entries (a repeated endpoint keeps its last line) and the numbers of unreadable lines.

    Blank lines and ``#`` comments are skipped silently.
    """
    entries: dict = {}
    invalid: list[int] = []
    for number, raw in enumerate((text or '').splitlines(), 1):
        line = raw.strip().lstrip('﻿')
        if not line or line.startswith('#'):
            continue
        match = _LINE.match(line)
        port = int(match['port']) if match else 0
        if not 1 <= port <= 65535:
            invalid.append(number)
            continue
        entry = Entry(match['host'].lower(), port, match['username'] or '', match['password'] or '')
        entries[entry.key] = entry
    return list(entries.values()), invalid


@transaction.atomic
def import_proxies(text: str, *, source: str = '', replace: bool = False) -> ImportResult:
    """Add the proxies of a TXT export; a known endpoint only gets its password refreshed.

    ``is_active`` of a known proxy is left alone: a re-import must not switch back on what the
    owner switched off. With ``replace`` the proxies missing from the list are deleted — unless
    the list has no readable line at all, so a wrong file can never empty the pool.
    """
    entries, invalid = parse_proxy_list(text)
    result = ImportResult(invalid_lines=invalid)
    existing = {(p.host, p.port, p.username): p for p in Proxy.objects.all()}

    new, changed = [], []
    now = timezone.now()
    for entry in entries:
        row = existing.get(entry.key)
        if row is None:
            new.append(Proxy(host=entry.host, port=entry.port, username=entry.username,
                             password=entry.password, source=source[:150]))
        elif row.password != entry.password:
            row.password = entry.password
            row.updated_at = now
            changed.append(row)
        else:
            result.unchanged += 1
    Proxy.objects.bulk_create(new)
    Proxy.objects.bulk_update(changed, ['password', 'updated_at'])
    result.created, result.updated = len(new), len(changed)

    if replace and entries:
        keep = {entry.key for entry in entries}
        stale = [row.pk for key, row in existing.items() if key not in keep]
        Proxy.objects.filter(pk__in=stale).delete()
        result.removed = len(stale)
    return result


def export_shared() -> tuple[bool, str]:
    """Publish the active proxies to the shared file. Returns ``(ok, error)``; never raises on I/O."""
    urls = [proxy.url for proxy in Proxy.objects.filter(is_active=True).order_by('pk')]
    data = {'version': 1, 'updated_at': timezone.now().isoformat(timespec='seconds'), 'proxies': urls}
    path = pool_file()
    directory = os.path.dirname(path) or '.'
    try:
        os.makedirs(directory, mode=0o755, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix='.proxies.')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                json.dump(data, fh)
                fh.flush()
                os.fsync(fh.fileno())
            os.chmod(tmp_path, 0o600)
            _hand_to_directory_owner(tmp_path, directory)
            os.replace(tmp_path, path)  # atomic: a reader never sees a torn file
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except OSError as exc:
        logger.error('[proxies] shared file not written (%s): %s', path, exc)
        return False, str(exc)
    return True, ''


def _hand_to_directory_owner(path: str, directory: str) -> None:
    owner = os.stat(directory)
    if (owner.st_uid, owner.st_gid) == (os.geteuid(), os.getegid()):
        return
    try:
        os.chown(path, owner.st_uid, owner.st_gid)
    except OSError as exc:  # not root: the file stays with the writer, readers may not see it
        logger.warning('[proxies] could not hand %s to the directory owner: %s', path, exc)
