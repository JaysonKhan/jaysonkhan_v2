"""
Kreativ emoji dizayn for server health reports.

Visual elements:
- Custom premium emoji from SiteSettings (with Unicode fallback)
- Color badges: 🟢 OK, 🟡 Warning, 🔴 Critical
- Progress bars: ▓▓▓▓▓░░░░░ 50%
- Box drawing for structure
- Medal emojis for top processes
- Telegram custom emoji: <tg-emoji emoji-id="ID">fallback</tg-emoji>
"""
from __future__ import annotations

from datetime import timedelta

from .metrics import (
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

# ── Emoji Registry (loaded from SiteSettings) ───────────────────────────────

_emoji_cache: dict | None = None


def _load_emojis() -> dict:
    """Load custom emoji IDs from SiteSettings, cache in module."""
    global _emoji_cache
    if _emoji_cache is not None:
        return _emoji_cache
    try:
        from core.services import SiteSettingsService
        site = SiteSettingsService.get()
        _emoji_cache = {
            'server': getattr(site, 'tg_emoji_server', '') or '',
            'cpu': getattr(site, 'tg_emoji_cpu', '') or '',
            'ram': getattr(site, 'tg_emoji_ram', '') or '',
            'disk': getattr(site, 'tg_emoji_disk', '') or '',
            'ok': getattr(site, 'tg_emoji_ok', '') or '',
            'warn': getattr(site, 'tg_emoji_warn', '') or '',
            'critical': getattr(site, 'tg_emoji_critical', '') or '',
            'chart': getattr(site, 'tg_emoji_chart', '') or '',
            'alert': getattr(site, 'tg_emoji_alert', '') or '',
            'money': getattr(site, 'tg_emoji_money', '') or '',
        }
        # Merge dynamic extras from JSONField
        extras = getattr(site, 'tg_emoji_extra', None) or {}
        if isinstance(extras, dict):
            for key, eid in extras.items():
                if eid and isinstance(eid, str):
                    _emoji_cache[key] = eid
    except Exception:
        import logging
        logging.getLogger('servermonitor').error(
            'Failed to load emoji cache', exc_info=True,
        )
        _emoji_cache = {}
    return _emoji_cache


def reset_emoji_cache():
    """Reset cache (call after SiteSettings change)."""
    global _emoji_cache
    _emoji_cache = None


def _ce(emoji_key: str, fallback: str) -> str:
    """Custom Emoji — returns <tg-emoji> tag if ID exists, else fallback Unicode."""
    emojis = _load_emojis()
    eid = emojis.get(emoji_key, '')
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'
    return fallback


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


def _service_icon(svc_name: str) -> str:
    icons = {
        'jaysonkhan': '🌐',
        'talabaovozi': '🤖',
        'nginx': '⚡',
        'postgresql': '🐘',
        'redis-server': '🔴',
    }
    return icons.get(svc_name, '⚙️')


def _service_badge(status: ServiceStatus) -> str:
    if status.active:
        return _ce('ok', '🟢')
    if status.status in ('inactive', 'dead'):
        return _ce('critical', '🔴')
    return '⚪'


MEDAL_EMOJIS = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣']


# ── Section Formatters ───────────────────────────────────────────────────────


def format_header(snapshot: ServerSnapshot) -> str:
    chart = _ce('chart', '📊')
    server = _ce('server', '🖥')
    return (
        f'{chart} <b>Server Health Report</b>\n'
        f'┌─────────────────────────\n'
        f'│ {server} <b>{snapshot.hostname}</b>\n'
        f'│ 🕐 {snapshot.timestamp.strftime("%Y-%m-%d %H:%M")}\n'
        f'│ ⏱ Uptime: <b>{_format_uptime(snapshot.uptime)}</b>\n'
        f'└─────────────────────────'
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
        f'  📈 Load: {cpu.load_avg_1} / {cpu.load_avg_5} / {cpu.load_avg_15}'
    )
    return '\n'.join(lines)


def format_cpu_compact(cpu: CpuMetrics) -> str:
    cpu_icon = _ce('cpu', '🧠')
    return (
        f'\n{cpu_icon} <b>CPU</b> ({cpu.core_count} cores)\n'
        f'  {_badge(cpu.total_percent)} {_progress_bar(cpu.total_percent)} <b>{cpu.total_percent}%</b>\n'
        f'  📈 Load: {cpu.load_avg_1} / {cpu.load_avg_5} / {cpu.load_avg_15}'
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
        return '\n🔄 <b>Swap</b>: not configured'
    return (
        f'\n🔄 <b>Swap</b>\n'
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
    lines = ['\n🔧 <b>Services</b>']
    for svc in services:
        icon = _service_icon(svc.name)
        badge = _service_badge(svc)
        mem_info = f' ({svc.memory_mb}MB)' if svc.memory_mb else ''
        lines.append(f'  {badge} {icon} <b>{svc.name}</b>: {svc.status}{mem_info}')
    return '\n'.join(lines)


def format_top_processes(procs: list[dict]) -> str:
    lines = ['\n🏆 <b>Top Processes (CPU)</b>']
    for i, p in enumerate(procs):
        medal = MEDAL_EMOJIS[i] if i < len(MEDAL_EMOJIS) else '  '
        lines.append(
            f'  {medal} <code>{p["name"][:15]:<15}</code> CPU:{p["cpu"]:5.1f}% MEM:{p["mem"]:4.1f}%'
        )
    return '\n'.join(lines)


# ── CPU Alert (core-level) ───────────────────────────────────────────────────


def format_cpu_alert(cpu: CpuMetrics, threshold: float = 75.0) -> str | None:
    """Return alert message if any core exceeds threshold. None if all OK."""
    hot_cores = [c for c in cpu.cores if c.percent >= threshold]
    if not hot_cores:
        return None

    alert_icon = _ce('alert', '🚨')
    lines = [
        f'{alert_icon} <b>CPU Alert!</b> {len(hot_cores)}/{cpu.core_count} cores above {threshold}%\n',
        '┌─────────────────────────',
    ]
    for c in hot_cores:
        lines.append(
            f'│ {_badge(c.percent)} Core {c.core}: {_progress_bar(c.percent)} <b>{c.percent}%</b>'
        )
    lines.append('└─────────────────────────')
    lines.append(
        f'\n⚠️ <b>Server kuchaytirish kerak bo\'lishi mumkin!</b>\n'
        f'CPU overload — ko\'proq yadro yoki kuchliroq protsessor tavsiya etiladi.'
    )
    return '\n'.join(lines)


# ── Full Report ──────────────────────────────────────────────────────────────


def format_full_report(snapshot: ServerSnapshot) -> str:
    """Complete daily health report with all sections."""
    sections = [
        format_header(snapshot),
        format_cpu(snapshot.cpu),
        format_memory(snapshot.memory),
        format_swap(snapshot.swap),
        format_disk(snapshot.disk),
        format_services(snapshot.services),
        format_top_processes(snapshot.top_processes),
    ]
    return '\n'.join(sections)


def format_status_report(snapshot: ServerSnapshot) -> str:
    """Quick /status snapshot — compact version."""
    sections = [
        format_header(snapshot),
        format_cpu_compact(snapshot.cpu),
        format_memory(snapshot.memory),
        format_disk(snapshot.disk),
        format_services(snapshot.services),
    ]
    return '\n'.join(sections)
