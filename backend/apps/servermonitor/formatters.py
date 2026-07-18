"""
Kreativ emoji dizayn for server health reports.
Uses centralized core.emoji.ce() for custom emoji support.

Every formatter takes ``lang`` ('uz' default / 'ru') and renders word-bearing
strings via core.bot_i18n.t(); hardware labels (CPU/RAM/Swap/Disk/Load) stay
as universal technical terms.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from core.bot_i18n import t
from core.emoji import ce as _ce  # noqa: F401
from django.utils.timezone import localtime as _localtime

from .metrics import (
    SERVICE_GROUPS,
    CpuMetrics,
    DiskMetrics,
    DiskPartitionInfo,
    MemoryMetrics,
    ServerSnapshot,
    ServiceStatus,
    SwapMetrics,
)

# ── Thresholds ───────────────────────────────────────────────────────────────

WARN_THRESHOLD = 75
CRIT_THRESHOLD = 90


# ── Helpers ──────────────────────────────────────────────────────────────────


def _badge(percent: float) -> str:
    if percent >= CRIT_THRESHOLD:
        return _ce('critical', '🔴')
    if percent >= WARN_THRESHOLD:
        return _ce('warn', '🟡')
    return _ce('ok', '🟢')


def _progress_bar(percent: float, width: int = 10) -> str:
    filled = round(percent / 100 * width)
    empty = width - filled
    return '▓' * filled + '░' * empty


def _format_uptime(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    parts = []
    if days:
        parts.append(f'{days}d')
    if hours:
        parts.append(f'{hours}h')
    parts.append(f'{minutes}m')
    return ' '.join(parts)


def _group_label(group_key: str) -> tuple[str, str]:
    """(label_key, fallback) for a service group."""
    meta = SERVICE_GROUPS.get(group_key)
    if meta:
        return f'grp.{group_key}', meta['label']
    return '', group_key.title()


# Per-unit icons. Unit names with `@` keep the part before the `@`
# for matching (e.g. `postgresql@16-main` → `postgresql`).
_SERVICE_ICONS = {
    'jaysonkhan':      '🌐',
    'edustats-web':    '📊',
    'edustats-bot':    '🤖',
    'uzexam':          '🎓',
    'uzexam-bot':      '🤖',
    'vaygo-web':       '🛍',
    'vaygo-bot':       '🤖',
    'nginx':           '⚡',
    'postgresql':      '🐘',
    'redis-server':    '🧠',
    'postfix':         '📬',
    'dovecot':         '📨',
    'fail2ban':        '🛡',
}


def _service_icon(svc_name: str) -> str:
    base = svc_name.split('@')[0]
    return _SERVICE_ICONS.get(svc_name) or _SERVICE_ICONS.get(base) or '⚙️'


def _service_badge(status: ServiceStatus) -> str:
    if status.active:
        return _ce('ok', '🟢')
    if status.status in ('inactive', 'dead', 'failed'):
        return _ce('critical', '🔴')
    if status.status == 'activating':
        return _ce('warn', '🟡')
    return _ce('warn', '🟡')


MEDAL_EMOJIS = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣']


# ── Section Formatters ───────────────────────────────────────────────────────


def format_header(snapshot: ServerSnapshot, lang: str = 'uz') -> str:
    chart = _ce('chart', '📊')
    server = _ce('server', '🖥')
    web = _ce('web', '🌐')
    return (
        f'{chart} {t("rep.title", lang)}\n\n'
        f'{web} jaysonkhan.com\n'
        f'{server} {snapshot.hostname}\n'
        f'{_ce("clock", "🕐")} {snapshot.timestamp.strftime("%Y-%m-%d %H:%M")}\n'
        f'{_ce("uptime", "⏱")} {t("rep.uptime", lang, up=_format_uptime(snapshot.uptime))}'
    )


def format_cpu(cpu: CpuMetrics, lang: str = 'uz') -> str:
    cpu_icon = _ce('cpu', '🧠')
    lines = [
        f'\n{cpu_icon} <b>CPU</b> {t("rep.cores", lang, n=cpu.core_count)}',
        f'  {_badge(cpu.total_percent)} Total: {_progress_bar(cpu.total_percent)} <b>{cpu.total_percent}%</b>',
    ]
    for c in cpu.cores:
        lines.append(
            f'  {_badge(c.percent)} {t("rep.core", lang, i=c.core)}: {_progress_bar(c.percent, 8)} {c.percent}%'
        )
    lines.append(
        f'  {_ce("load", "📈")} Load: {cpu.load_avg_1} / {cpu.load_avg_5} / {cpu.load_avg_15}'
    )
    return '\n'.join(lines)


def format_cpu_compact(cpu: CpuMetrics, lang: str = 'uz') -> str:
    cpu_icon = _ce('cpu', '🧠')
    return (
        f'\n{cpu_icon} <b>CPU</b> {t("rep.cores", lang, n=cpu.core_count)}\n'
        f'  {_badge(cpu.total_percent)} {_progress_bar(cpu.total_percent)} <b>{cpu.total_percent}%</b>\n'
        f'  {_ce("load", "📈")} Load: {cpu.load_avg_1} / {cpu.load_avg_5} / {cpu.load_avg_15}'
    )


def format_memory(mem: MemoryMetrics, lang: str = 'uz') -> str:
    ram_icon = _ce('ram', '💾')
    return (
        f'\n{ram_icon} <b>RAM</b>\n'
        f'  {_badge(mem.percent)} {_progress_bar(mem.percent)} <b>{mem.percent}%</b>\n'
        f'  {mem.used_gb}GB / {mem.total_gb}GB ({t("rep.free", lang)}: {mem.available_gb}GB)'
    )


def format_swap(swap: SwapMetrics, lang: str = 'uz') -> str:
    if swap.total_gb == 0:
        return f'\n{_ce("swap", "🔄")} {t("rep.swap_none", lang)}'
    return (
        f'\n{_ce("swap", "🔄")} <b>Swap</b>\n'
        f'  {_badge(swap.percent)} {_progress_bar(swap.percent)} <b>{swap.percent}%</b>\n'
        f'  {swap.used_gb}GB / {swap.total_gb}GB'
    )


def format_disk(disk: DiskMetrics, lang: str = 'uz') -> str:
    disk_icon = _ce('disk', '💿')
    return (
        f'\n{disk_icon} <b>Disk</b> ({disk.mountpoint})\n'
        f'  {_badge(disk.percent)} {_progress_bar(disk.percent)} <b>{disk.percent}%</b>\n'
        f'  {disk.used_gb}GB / {disk.total_gb}GB ({t("rep.free", lang)}: {disk.free_gb}GB)'
    )


def format_disk_detailed(partitions: list[DiskPartitionInfo], lang: str = 'uz') -> str:
    disk_icon = _ce('disk', '💿')
    lines = [f'\n{disk_icon} <b>Disk</b>']
    for p in partitions:
        lines.append(
            f'  {_badge(p.percent)} <code>{p.mountpoint}</code> '
            f'{_progress_bar(p.percent, 8)} {p.percent}% '
            f'({p.used_gb}/{p.total_gb}GB)'
        )
    return '\n'.join(lines)


def format_services(services: list[ServiceStatus], lang: str = 'uz') -> str:
    """Flat services list — kept for the /status compact snapshot."""
    lines = [f'\n{_ce("services_icon", "🔧")} {t("rep.services", lang)}']
    for svc in services:
        icon = _service_icon(svc.name)
        badge = _service_badge(svc)
        mem_info = f' ({svc.memory_mb}MB)' if svc.memory_mb else ''
        label = svc.display or svc.name
        lines.append(f'  {badge} {icon} <b>{label}</b>: {svc.status}{mem_info}')
    return '\n'.join(lines)


def format_services_grouped(
    services: list[ServiceStatus],
    *,
    restart_counts: dict[str, int] | None = None,
    lang: str = 'uz',
) -> str:
    """Grouped services view with optional 24h restart counts.

    `restart_counts` is a {unit: count} dict — pulled from
    ServiceCheckResult by the caller. Shown inline next to each unit
    when > 0 to surface flapping services in the daily report.
    """
    restart_counts = restart_counts or {}
    by_group: dict[str, list[ServiceStatus]] = defaultdict(list)
    for svc in services:
        by_group[svc.group or 'other'].append(svc)

    lines = [f'\n{_ce("services_icon", "🔧")} {t("rep.services", lang)}']
    # Render in declared group order (apps → infra → mail → security → other)
    declared = list(SERVICE_GROUPS.keys()) + [g for g in by_group if g not in SERVICE_GROUPS]
    for group_key in declared:
        bucket = by_group.get(group_key)
        if not bucket:
            continue
        meta = SERVICE_GROUPS.get(group_key, {'label': group_key.title(), 'icon': '⚙️'})
        label_key, fallback = _group_label(group_key)
        group_name = t(label_key, lang) if label_key else fallback
        active_n = sum(1 for s in bucket if s.active)
        total_n = len(bucket)
        health_dot = '🟢' if active_n == total_n else '🔴' if active_n == 0 else '🟡'
        lines.append(
            f'\n  {meta["icon"]} <b>{group_name}</b> {health_dot} '
            f'{t("rep.up", lang, a=active_n, b=total_n)}'
        )
        for svc in bucket:
            icon = _service_icon(svc.name)
            badge = _service_badge(svc)
            mem_info = f' · {svc.memory_mb}MB' if svc.memory_mb else ''
            label = svc.display or svc.name
            restarts = restart_counts.get(svc.name, 0)
            restart_info = f' · 🔁 {restarts}x/24h' if restarts else ''
            lines.append(
                f'    {badge} {icon} {label} <code>{svc.status}</code>{mem_info}{restart_info}'
            )
    return '\n'.join(lines)


def format_top_processes(procs: list[dict], lang: str = 'uz') -> str:
    lines = [f'\n{_ce("trophy", "🏆")} {t("rep.top_procs", lang)}']
    for i, p in enumerate(procs):
        medal = MEDAL_EMOJIS[i] if i < len(MEDAL_EMOJIS) else '  '
        lines.append(
            f'  {medal} <code>{p["name"][:15]:<15}</code> CPU:{p["cpu"]:5.1f}% MEM:{p["mem"]:4.1f}%'
        )
    return '\n'.join(lines)


# ── CPU Alert (core-level) ───────────────────────────────────────────────────


def format_cpu_alert(cpu: CpuMetrics, threshold: float = 85.0, lang: str = 'uz') -> str | None:
    """Return alert message if any core exceeds threshold. None if all OK.

    Default threshold raised to 85% (was 75%) on 2026-04-27 after
    transient sub-second bursts kept tripping the 75% line. WARN_THRESHOLD
    above stays at 75% — that drives the yellow visual badge, which is
    informational, not paging.
    """
    hot_cores = [c for c in cpu.cores if c.percent >= threshold]
    if not hot_cores:
        return None

    alert_icon = _ce('alert', '🚨')
    lines = [
        t('alert.cpu_title', lang, icon=alert_icon,
          hot=len(hot_cores), total=cpu.core_count, thr=threshold),
    ]
    for c in hot_cores:
        lines.append(
            f'{_badge(c.percent)} {t("rep.core", lang, i=c.core)}: '
            f'{_progress_bar(c.percent)} <b>{c.percent}%</b>'
        )
    lines.append(t('alert.cpu_advice', lang))
    return '\n'.join(lines)


# ── Service state-change alert ───────────────────────────────────────────────


def format_service_alert(
    *,
    unit: str,
    display: str,
    group: str,
    new_active: bool,
    previous_active: bool | None,
    status_text: str = '',
    lang: str = 'uz',
) -> str:
    """Per-service alert for state transitions.

    Sent ONLY when current check differs from previous one — so
    a clean restart produces 1 DOWN message followed by 1 UP message,
    never the same alert twice for the same status.
    """
    icon = _service_icon(unit)
    group_meta = SERVICE_GROUPS.get(group, {'label': 'Other', 'icon': '⚙️'})
    label_key, fallback = _group_label(group)
    group_name = t(label_key, lang) if label_key else fallback
    arrow = '→'
    prev_label = 'active' if previous_active else 'inactive'
    new_label = 'active' if new_active else 'inactive'

    if not new_active:
        title = t('alert.svc_down_title', lang)
        body = t('alert.svc_down_body', lang, icon=icon, display=display)
        action = t('alert.svc_down_action', lang, unit=unit)
    else:
        title = t('alert.svc_up_title', lang)
        body = t('alert.svc_up_body', lang, icon=icon, display=display)
        action = t('alert.svc_up_action', lang)

    return (
        f'{title}\n\n'
        f'{body}\n'
        f'<b>{t("alert.svc_group", lang)}:</b> {group_meta["icon"]} {group_name}\n'
        f'<b>Unit:</b> <code>{unit}</code>\n'
        f'<b>{t("alert.svc_state", lang)}:</b> <code>{prev_label}</code> {arrow} <code>{new_label}</code>'
        + (f' ({status_text})' if status_text and status_text != new_label else '')
        + f'\n\n{action}'
    )


# ── Cron health alert ────────────────────────────────────────────────────────


def format_cron_failure_alert(
    *,
    failures: list[dict],
    overdue: list[dict],
    lang: str = 'uz',
) -> str | None:
    """Cron failure / overdue summary. None if everything's fine.

    failures: [{command, started_at, duration_ms, error_summary}, ...]
    overdue:  [{command, schedule, last_seen}, ...]
    """
    if not failures and not overdue:
        return None

    lines = [t('alert.cron_title', lang)]

    if failures:
        lines.append(t('alert.cron_failed', lang, n=len(failures)))
        for f in failures[:10]:
            ts = _localtime(f['started_at']).strftime('%H:%M:%S') if f.get('started_at') else '?'
            dur = f.get('duration_ms')
            dur_s = f'{dur / 1000:.1f}s' if dur else '?'
            err = (f.get('error_summary') or '').strip()[:80]
            err_part = f' — {err}' if err else ''
            lines.append(f'  • <code>{f["command"]}</code> [{ts}, {dur_s}]{err_part}')
        if len(failures) > 10:
            lines.append(t('alert.cron_more', lang, n=len(failures) - 10))

    if overdue:
        lines.append(t('alert.cron_overdue', lang))
        for o in overdue[:10]:
            last = _localtime(o['last_seen']).strftime('%Y-%m-%d %H:%M') if o.get('last_seen') else 'never'
            lines.append(f'  • <code>{o["command"]}</code> — {t("alert.cron_last", lang, last=last)}')

    return '\n'.join(lines)


# ── Full Report ──────────────────────────────────────────────────────────────


def format_full_report(
    snapshot: ServerSnapshot,
    *,
    restart_counts: dict[str, int] | None = None,
    cron_summary: dict | None = None,
    lang: str = 'uz',
) -> str:
    """Complete daily health report with all sections.

    `cron_summary` is an optional dict from server_health_report:
        {'success': N, 'failed': M, 'recent_failures': [{...}], 'overdue': [{...}]}
    """
    sections = [
        format_header(snapshot, lang),
        format_cpu(snapshot.cpu, lang),
        format_memory(snapshot.memory, lang),
        format_swap(snapshot.swap, lang),
        format_disk(snapshot.disk, lang),
        format_services_grouped(snapshot.services, restart_counts=restart_counts, lang=lang),
        format_top_processes(snapshot.top_processes, lang),
    ]
    if cron_summary:
        sections.append(format_cron_summary(cron_summary, lang))
    return '\n'.join(sections)


def format_cron_summary(s: dict, lang: str = 'uz') -> str:
    success = s.get('success', 0)
    failed = s.get('failed', 0)
    overdue = s.get('overdue', [])
    icon_ok = _ce('ok', '🟢')
    icon_bad = _ce('critical', '🔴')
    head = f'\n{_ce("clock", "🕐")} {t("rep.cron", lang)}'
    body = f'  {t("rep.cron_line", lang, ok=icon_ok, n_ok=success, bad=icon_bad, n_bad=failed)}'
    if overdue:
        body += f'\n  {t("rep.cron_overdue", lang, n=len(overdue))}'
    return f'{head}\n{body}'


def format_status_report(snapshot: ServerSnapshot, lang: str = 'uz') -> str:
    """Quick /status snapshot — compact version."""
    sections = [
        format_header(snapshot, lang),
        format_cpu_compact(snapshot.cpu, lang),
        format_memory(snapshot.memory, lang),
        format_disk(snapshot.disk, lang),
        format_services_grouped(snapshot.services, lang=lang),
    ]
    return '\n'.join(sections)


# ── v2: HTTP / SSL / error-scan / DB views ───────────────────────────────────


def format_web_checks(checks: list, lang: str = 'uz') -> str:
    """/web — HTTP health of public sites + localhost APIs."""
    lines = [t('web.title', lang, icon=_ce('web', '🌐'))]
    internal_started = False
    for c in checks:
        if c.internal and not internal_started:
            internal_started = True
            lines.append(t('web.internal', lang, icon=_ce('server', '🖥')))
        if c.status == 0:
            lines.append(t('web.no_conn', lang, label=c.label, err=c.error))
        elif 200 <= c.status < 400:
            speed = '🟢' if c.ms < 1500 else '🟡'
            lines.append(f'  {speed} <b>{c.label}</b> — {c.status} · {c.ms}ms')
        else:
            lines.append(f'  🔴 <b>{c.label}</b> — HTTP {c.status} · {c.ms}ms')
    return '\n'.join(lines)


def format_ssl_checks(checks: list, lang: str = 'uz') -> str:
    """/ssl — Let's Encrypt expiry per domain (manual DNS-01 renewals!)."""
    lines = [t('ssl.title', lang, icon=_ce('lock', '🔐'))]
    for c in checks:
        if c.error:
            lines.append(t('ssl.fail', lang, domain=c.domain, err=c.error))
        elif c.days_left < 7:
            lines.append(t('ssl.crit', lang, domain=c.domain, d=c.days_left, exp=c.expires))
        elif c.days_left < 14:
            lines.append(t('ssl.warn', lang, domain=c.domain, d=c.days_left, exp=c.expires))
        else:
            lines.append(t('ssl.ok', lang, domain=c.domain, d=c.days_left, exp=c.expires))
    lines.append(t('ssl.footer', lang, icon=_ce('scam_warn', 'ℹ️')))
    return '\n'.join(lines)


def format_error_scan(scans: list, hours: int, lang: str = 'uz') -> str:
    """/errors — journalctl error counts per app unit."""
    lines = [t('err.title', lang, icon=_ce('logs_icon', '🧾'), h=hours)]
    total = 0
    worst = None
    for s in scans:
        if s.count < 0:
            reason = t('err.na', lang) if s.error == 'no-journalctl' else s.error
            lines.append(f'  ⚪ <code>{s.unit}</code> — {reason}')
            continue
        total += s.count
        dot = '🟢' if s.count == 0 else ('🟡' if s.count < 20 else '🔴')
        lines.append(f'  {dot} <code>{s.unit}</code> — {t("err.count", lang, n=s.count)}')
        if s.count and (worst is None or s.count > worst.count):
            worst = s
    if worst and worst.sample:
        from django.utils.html import escape as _esc
        lines.append(t('err.worst', lang, unit=worst.unit))
        lines.append(f'<pre>{_esc(worst.sample)}</pre>')
    if total == 0:
        lines.append(t('err.clean', lang, icon=_ce('ok', '✅')))
    lines.append(t('err.details', lang))
    return '\n'.join(lines)


def format_db_report(rows: list[dict], connections: int, error: str, lang: str = 'uz') -> str:
    """/db — PostgreSQL database sizes + connection count."""
    lines = ['🐘 <b>PostgreSQL</b>']
    if error:
        lines.append(f'  🔴 {error}')
        return '\n'.join(lines)
    for r in rows:
        lines.append(f'  • <code>{r["name"]}</code> — {r["size"]}')
    lines.append(t('db.conns', lang, n=connections))
    return '\n'.join(lines)
