"""
Kreativ emoji dizayn for server health reports.
Uses centralized core.emoji.ce() for custom emoji support.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from core.emoji import ce as _ce, reset_cache as reset_emoji_cache  # noqa: F401

from .metrics import (
    CpuMetrics,
    DiskMetrics,
    DiskPartitionInfo,
    MemoryMetrics,
    SERVICE_GROUPS,
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


# Per-unit icons. Unit names with `@` keep the part before the `@`
# for matching (e.g. `postgresql@16-main` → `postgresql`).
_SERVICE_ICONS = {
    'jaysonkhan':      '🌐',
    'talabaovozi-web': '📊',
    'talabaovozi':     '🤖',
    'uzexam':          '🎓',
    'uzexam-bot':      '🤖',
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


def format_header(snapshot: ServerSnapshot) -> str:
    chart = _ce('chart', '📊')
    server = _ce('server', '🖥')
    web = _ce('web', '🌐')
    return (
        f'{chart} <b>Server Health Report</b>\n\n'
        f'{web} jaysonkhan.com\n'
        f'{server} {snapshot.hostname}\n'
        f'{_ce("clock", "🕐")} {snapshot.timestamp.strftime("%Y-%m-%d %H:%M")}\n'
        f'{_ce("uptime", "⏱")} Uptime: <b>{_format_uptime(snapshot.uptime)}</b>'
    )


def format_cpu(cpu: CpuMetrics) -> str:
    cpu_icon = _ce('cpu', '🧠')
    lines = [
        f'\n{cpu_icon} <b>CPU</b> ({cpu.core_count} cores)',
        f'  {_badge(cpu.total_percent)} Total: {_progress_bar(cpu.total_percent)} <b>{cpu.total_percent}%</b>',
    ]
    for c in cpu.cores:
        lines.append(
            f'  {_badge(c.percent)} Core {c.core}: {_progress_bar(c.percent, 8)} {c.percent}%'
        )
    lines.append(
        f'  {_ce("load", "📈")} Load: {cpu.load_avg_1} / {cpu.load_avg_5} / {cpu.load_avg_15}'
    )
    return '\n'.join(lines)


def format_cpu_compact(cpu: CpuMetrics) -> str:
    cpu_icon = _ce('cpu', '🧠')
    return (
        f'\n{cpu_icon} <b>CPU</b> ({cpu.core_count} cores)\n'
        f'  {_badge(cpu.total_percent)} {_progress_bar(cpu.total_percent)} <b>{cpu.total_percent}%</b>\n'
        f'  {_ce("load", "📈")} Load: {cpu.load_avg_1} / {cpu.load_avg_5} / {cpu.load_avg_15}'
    )


def format_memory(mem: MemoryMetrics) -> str:
    ram_icon = _ce('ram', '💾')
    return (
        f'\n{ram_icon} <b>RAM</b>\n'
        f'  {_badge(mem.percent)} {_progress_bar(mem.percent)} <b>{mem.percent}%</b>\n'
        f'  {mem.used_gb}GB / {mem.total_gb}GB (free: {mem.available_gb}GB)'
    )


def format_swap(swap: SwapMetrics) -> str:
    if swap.total_gb == 0:
        return f'\n{_ce("swap", "🔄")} <b>Swap</b>: not configured'
    return (
        f'\n{_ce("swap", "🔄")} <b>Swap</b>\n'
        f'  {_badge(swap.percent)} {_progress_bar(swap.percent)} <b>{swap.percent}%</b>\n'
        f'  {swap.used_gb}GB / {swap.total_gb}GB'
    )


def format_disk(disk: DiskMetrics) -> str:
    disk_icon = _ce('disk', '💿')
    return (
        f'\n{disk_icon} <b>Disk</b> ({disk.mountpoint})\n'
        f'  {_badge(disk.percent)} {_progress_bar(disk.percent)} <b>{disk.percent}%</b>\n'
        f'  {disk.used_gb}GB / {disk.total_gb}GB (free: {disk.free_gb}GB)'
    )


def format_disk_detailed(partitions: list[DiskPartitionInfo]) -> str:
    disk_icon = _ce('disk', '💿')
    lines = [f'\n{disk_icon} <b>Disk Usage (all partitions)</b>']
    for p in partitions:
        lines.append(
            f'  {_badge(p.percent)} <code>{p.mountpoint}</code> '
            f'{_progress_bar(p.percent, 8)} {p.percent}% '
            f'({p.used_gb}/{p.total_gb}GB)'
        )
    return '\n'.join(lines)


def format_services(services: list[ServiceStatus]) -> str:
    """Flat services list — kept for the /status compact snapshot."""
    lines = [f'\n{_ce("services_icon", "🔧")} <b>Services</b>']
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

    lines = [f'\n{_ce("services_icon", "🔧")} <b>Services</b>']
    # Render in declared group order (apps → infra → mail → security → other)
    declared = list(SERVICE_GROUPS.keys()) + [g for g in by_group if g not in SERVICE_GROUPS]
    for group_key in declared:
        bucket = by_group.get(group_key)
        if not bucket:
            continue
        meta = SERVICE_GROUPS.get(group_key, {'label': group_key.title(), 'icon': '⚙️'})
        active_n = sum(1 for s in bucket if s.active)
        total_n = len(bucket)
        health_dot = '🟢' if active_n == total_n else '🔴' if active_n == 0 else '🟡'
        lines.append(
            f'\n  {meta["icon"]} <b>{meta["label"]}</b> {health_dot} ({active_n}/{total_n} up)'
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


def format_top_processes(procs: list[dict]) -> str:
    lines = [f'\n{_ce("trophy", "🏆")} <b>Top Processes (CPU)</b>']
    for i, p in enumerate(procs):
        medal = MEDAL_EMOJIS[i] if i < len(MEDAL_EMOJIS) else '  '
        lines.append(
            f'  {medal} <code>{p["name"][:15]:<15}</code> CPU:{p["cpu"]:5.1f}% MEM:{p["mem"]:4.1f}%'
        )
    return '\n'.join(lines)


# ── CPU Alert (core-level) ───────────────────────────────────────────────────


def format_cpu_alert(cpu: CpuMetrics, threshold: float = 85.0) -> str | None:
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
        f'{alert_icon} <b>CPU Alert!</b> {len(hot_cores)}/{cpu.core_count} cores above {threshold}%\n',
    ]
    for c in hot_cores:
        lines.append(
            f'{_badge(c.percent)} Core {c.core}: {_progress_bar(c.percent)} <b>{c.percent}%</b>'
        )
    lines.append(
        f'\n⚠️ <b>Server kuchaytirish kerak bo\'lishi mumkin!</b>\n'
        f'CPU overload — ko\'proq yadro yoki kuchliroq protsessor tavsiya etiladi.'
    )
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
) -> str:
    """Per-service alert for state transitions.

    Sent ONLY when current check differs from previous one — so
    a clean restart produces 1 DOWN message followed by 1 UP message,
    never the same alert twice for the same status.
    """
    icon = _service_icon(unit)
    group_meta = SERVICE_GROUPS.get(group, {'label': 'Other', 'icon': '⚙️'})
    arrow = '→'
    prev_label = 'active' if previous_active else 'inactive'
    new_label = 'active' if new_active else 'inactive'

    if not new_active:
        title = f'🚨 <b>Service DOWN</b>'
        body = f'{icon} <b>{display}</b> — endi ishlamayapti.'
        action = (
            'Tekshirish:\n'
            f'  <code>journalctl -u {unit} -n 50</code>\n'
            f'  <code>systemctl status {unit}</code>\n\n'
            'Koʼp marta DOWN boʼlsa restart yoki deploy.sh bilan qayta koʼtarish kerak.'
        )
    else:
        title = '✅ <b>Service Recovered</b>'
        body = f'{icon} <b>{display}</b> — qayta ishlayapti.'
        action = 'Avtomatik tiklandi yoki deploy/restart natijasi.'

    return (
        f'{title}\n\n'
        f'{body}\n'
        f'<b>Guruh:</b> {group_meta["icon"]} {group_meta["label"]}\n'
        f'<b>Unit:</b> <code>{unit}</code>\n'
        f'<b>Holat:</b> <code>{prev_label}</code> {arrow} <code>{new_label}</code>'
        + (f' ({status_text})' if status_text and status_text != new_label else '')
        + f'\n\n{action}'
    )


# ── Cron health alert ────────────────────────────────────────────────────────


def format_cron_failure_alert(
    *,
    failures: list[dict],
    overdue: list[dict],
) -> str | None:
    """Cron failure / overdue summary. None if everything's fine.

    failures: [{command, started_at, duration_ms, error_summary}, ...]
    overdue:  [{command, schedule, last_seen}, ...]
    """
    if not failures and not overdue:
        return None

    lines = ['🚨 <b>Cron Health Alert</b>']

    if failures:
        lines.append(f'\n❌ <b>Failed runs ({len(failures)})</b>')
        for f in failures[:10]:
            ts = f['started_at'].strftime('%H:%M:%S') if f.get('started_at') else '?'
            dur = f.get('duration_ms')
            dur_s = f'{dur / 1000:.1f}s' if dur else '?'
            err = (f.get('error_summary') or '').strip()[:80]
            err_part = f' — {err}' if err else ''
            lines.append(f'  • <code>{f["command"]}</code> [{ts}, {dur_s}]{err_part}')
        if len(failures) > 10:
            lines.append(f'  …va yana {len(failures) - 10} ta')

    if overdue:
        lines.append(f'\n⏳ <b>Overdue (no recent run)</b>')
        for o in overdue[:10]:
            last = o['last_seen'].strftime('%Y-%m-%d %H:%M') if o.get('last_seen') else 'never'
            lines.append(f'  • <code>{o["command"]}</code> — last: {last}')

    return '\n'.join(lines)


# ── Full Report ──────────────────────────────────────────────────────────────


def format_full_report(
    snapshot: ServerSnapshot,
    *,
    restart_counts: dict[str, int] | None = None,
    cron_summary: dict | None = None,
) -> str:
    """Complete daily health report with all sections.

    `cron_summary` is an optional dict from server_health_report:
        {'success': N, 'failed': M, 'recent_failures': [{...}], 'overdue': [{...}]}
    """
    sections = [
        format_header(snapshot),
        format_cpu(snapshot.cpu),
        format_memory(snapshot.memory),
        format_swap(snapshot.swap),
        format_disk(snapshot.disk),
        format_services_grouped(snapshot.services, restart_counts=restart_counts),
        format_top_processes(snapshot.top_processes),
    ]
    if cron_summary:
        sections.append(format_cron_summary(cron_summary))
    return '\n'.join(sections)


def format_cron_summary(s: dict) -> str:
    success = s.get('success', 0)
    failed = s.get('failed', 0)
    overdue = s.get('overdue', [])
    icon_ok = _ce('ok', '🟢')
    icon_bad = _ce('critical', '🔴')
    head = f'\n{_ce("clock", "🕐")} <b>Cron (24h)</b>'
    body = f'  {icon_ok} {success} muvaffaqiyat · {icon_bad} {failed} xato'
    extras = []
    if overdue:
        extras.append(f'  ⏳ Overdue: {len(overdue)} ta')
    if extras:
        body = body + '\n' + '\n'.join(extras)
    return f'{head}\n{body}'


def format_status_report(snapshot: ServerSnapshot) -> str:
    """Quick /status snapshot — compact version."""
    sections = [
        format_header(snapshot),
        format_cpu_compact(snapshot.cpu),
        format_memory(snapshot.memory),
        format_disk(snapshot.disk),
        format_services_grouped(snapshot.services),
    ]
    return '\n'.join(sections)
