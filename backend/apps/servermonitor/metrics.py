"""
Server metrics collection.

Uses psutil to gather CPU, RAM, disk, swap, uptime, and load averages.
All functions return plain dataclasses — formatting is in formatters.py.

Service inventory now lives in ``MONITORED_SERVICES`` as structured
dicts (unit / group / display / critical). Earlier the list was a flat
collection of unit names — that meant adding a new app required
sprinkling the icon, group, and display name across formatters and
the daily report. Today the list is the single source of truth.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import psutil


@dataclass
class CpuCoreInfo:
    core: int
    percent: float


@dataclass
class CpuMetrics:
    total_percent: float
    core_count: int
    cores: list[CpuCoreInfo] = field(default_factory=list)
    load_avg_1: float = 0.0
    load_avg_5: float = 0.0
    load_avg_15: float = 0.0


@dataclass
class MemoryMetrics:
    total_gb: float
    used_gb: float
    available_gb: float
    percent: float


@dataclass
class SwapMetrics:
    total_gb: float
    used_gb: float
    percent: float


@dataclass
class DiskMetrics:
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float
    mountpoint: str = '/'


@dataclass
class DiskPartitionInfo:
    device: str
    mountpoint: str
    fstype: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


@dataclass
class ServiceStatus:
    name: str                   # systemd unit name (e.g. "uzexam-bot", "postgresql@16-main")
    active: bool
    status: str                 # 'active', 'inactive', 'failed', 'no-systemctl', 'error'
    group: str = ''             # 'apps' / 'infra' / 'mail' / 'security'
    display: str = ''           # human-readable name (e.g. "UzExam Bot")
    critical: bool = True       # alert on state change?
    uptime: Optional[str] = None
    memory_mb: Optional[float] = None


@dataclass
class ServerSnapshot:
    timestamp: datetime
    hostname: str
    uptime: timedelta
    cpu: CpuMetrics
    memory: MemoryMetrics
    swap: SwapMetrics
    disk: DiskMetrics
    partitions: list[DiskPartitionInfo]
    services: list[ServiceStatus]
    top_processes: list[dict]


def _bytes_to_gb(b: int) -> float:
    return round(b / (1024 ** 3), 2)


def collect_cpu(*, interval: float = 1.0) -> CpuMetrics:
    """Sample per-core CPU usage.

    interval=1 (default) — quick snapshot for interactive /status. Cheap
    but susceptible to sub-second spikes (e.g., a single Postgres parallel
    query can briefly max several cores during the 1s sample window and
    cause a false-positive alert in check_cpu_alert).

    interval=5 — sustained sample. Recommended for cron-driven alerts where
    we care about real overload, not transient bursts. Adds 4s to the
    measurement, which is negligible for a 10-minute cron tick.
    """
    per_core = psutil.cpu_percent(interval=interval, percpu=True)
    total = psutil.cpu_percent(interval=0)
    load = psutil.getloadavg()
    cores = [CpuCoreInfo(core=i, percent=p) for i, p in enumerate(per_core)]
    return CpuMetrics(
        total_percent=total,
        core_count=psutil.cpu_count(logical=True),
        cores=cores,
        load_avg_1=round(load[0], 2),
        load_avg_5=round(load[1], 2),
        load_avg_15=round(load[2], 2),
    )


def collect_memory() -> MemoryMetrics:
    m = psutil.virtual_memory()
    return MemoryMetrics(
        total_gb=_bytes_to_gb(m.total),
        used_gb=_bytes_to_gb(m.used),
        available_gb=_bytes_to_gb(m.available),
        percent=m.percent,
    )


def collect_swap() -> SwapMetrics:
    s = psutil.swap_memory()
    return SwapMetrics(
        total_gb=_bytes_to_gb(s.total),
        used_gb=_bytes_to_gb(s.used),
        percent=s.percent,
    )


def collect_disk(mountpoint: str = '/') -> DiskMetrics:
    d = psutil.disk_usage(mountpoint)
    return DiskMetrics(
        total_gb=_bytes_to_gb(d.total),
        used_gb=_bytes_to_gb(d.used),
        free_gb=_bytes_to_gb(d.free),
        percent=d.percent,
        mountpoint=mountpoint,
    )


def collect_partitions() -> list[DiskPartitionInfo]:
    result = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue
        result.append(DiskPartitionInfo(
            device=part.device,
            mountpoint=part.mountpoint,
            fstype=part.fstype,
            total_gb=_bytes_to_gb(usage.total),
            used_gb=_bytes_to_gb(usage.used),
            free_gb=_bytes_to_gb(usage.free),
            percent=usage.percent,
        ))
    return result


def _systemctl(*args: str) -> str:
    """Tiny wrapper. Returns stripped stdout, '' on error/timeout."""
    try:
        r = subprocess.run(
            ['systemctl', *args],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):  # noqa: BLE001
        return ''


def collect_service_status(
    service_name: str,
    *,
    group: str = '',
    display: str = '',
    critical: bool = True,
) -> ServiceStatus:
    """Check systemd service status via systemctl. Always returns a row.

    Status text mirrors ``systemctl is-active``:
      - 'active'          → up
      - 'inactive'        → stopped (clean)
      - 'failed'          → crashed (still in unit registry, won't restart)
      - 'activating'      → mid-restart
      - 'no-systemctl'    → systemctl binary missing (dev box)
      - 'error'           → unexpected exception
    """
    status_text = _systemctl('is-active', service_name) or 'unknown'
    if status_text == 'unknown' and not _systemctl('--version'):
        status_text = 'no-systemctl'
    active = status_text == 'active'

    mem_mb: Optional[float] = None
    uptime_str: Optional[str] = None

    if active:
        # MemoryCurrent is bytes; format is `MemoryCurrent=12345`.
        mem_line = _systemctl('show', service_name, '--property=MemoryCurrent')
        if '=' in mem_line:
            val = mem_line.split('=', 1)[1]
            if val.isdigit():
                mem_mb = round(int(val) / (1024 * 1024), 1)

        ts_line = _systemctl('show', service_name, '--property=ActiveEnterTimestamp')
        if '=' in ts_line:
            stamp = ts_line.split('=', 1)[1].strip()
            if stamp:
                uptime_str = stamp

    return ServiceStatus(
        name=service_name,
        active=active,
        status=status_text,
        group=group,
        display=display or service_name,
        critical=critical,
        uptime=uptime_str,
        memory_mb=mem_mb,
    )


# ── Service inventory ──────────────────────────────────────────────────────
#
# Single source of truth for "which services do we monitor and how".
# Adding a new service: add a dict entry + run `service_health_check`.
# `critical=False` means logged but no Telegram alert on state change
# (used for ancillary services where flap-on-deploy is acceptable).

SERVICE_GROUPS = {
    'apps':     {'label': 'Applications',   'icon': '🚀'},
    'infra':    {'label': 'Infrastructure', 'icon': '🛠'},
    'mail':     {'label': 'Mail Server',    'icon': '📬'},
    'security': {'label': 'Security',       'icon': '🛡'},
}


MONITORED_SERVICES: list[dict] = [
    # ── Apps (user-visible) ──
    {'unit': 'jaysonkhan',         'group': 'apps',     'display': 'JaysonKhan Portfolio',  'critical': True},
    {'unit': 'talabaovozi-web',    'group': 'apps',     'display': 'EduStats Web',          'critical': True},
    {'unit': 'talabaovozi',        'group': 'apps',     'display': 'TalabaOvozi Bot',       'critical': True},
    {'unit': 'uzexam',             'group': 'apps',     'display': 'UzExam Web',            'critical': True},
    {'unit': 'uzexam-bot',         'group': 'apps',     'display': 'UzExam Bot',            'critical': True},
    # ── Infrastructure (everyone depends on these) ──
    {'unit': 'nginx',              'group': 'infra',    'display': 'Nginx',                 'critical': True},
    {'unit': 'postgresql@16-main', 'group': 'infra',    'display': 'PostgreSQL 16',         'critical': True},
    {'unit': 'redis-server',       'group': 'infra',    'display': 'Redis',                 'critical': True},
    # ── Mail (VIP-grade, alert if flap) ──
    {'unit': 'postfix@-',          'group': 'mail',     'display': 'Postfix',               'critical': True},
    {'unit': 'dovecot',            'group': 'mail',     'display': 'Dovecot (IMAP/POP3)',   'critical': True},
    # ── Security ──
    {'unit': 'fail2ban',           'group': 'security', 'display': 'Fail2ban',              'critical': True},
]


def collect_top_processes(n: int = 5) -> list[dict]:
    """Top N processes by CPU usage."""
    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            info = proc.info
            procs.append({
                'pid': info['pid'],
                'name': info['name'],
                'cpu': info['cpu_percent'] or 0,
                'mem': round(info['memory_percent'] or 0, 1),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x['cpu'], reverse=True)
    return procs[:n]


def collect_uptime() -> timedelta:
    boot = datetime.fromtimestamp(psutil.boot_time())
    return datetime.now() - boot


def collect_hostname() -> str:
    import socket
    return socket.gethostname()


def collect_full_snapshot() -> ServerSnapshot:
    """Collect all server metrics in one call."""
    services = [
        collect_service_status(
            cfg['unit'],
            group=cfg['group'],
            display=cfg['display'],
            critical=cfg.get('critical', True),
        )
        for cfg in MONITORED_SERVICES
    ]
    return ServerSnapshot(
        timestamp=datetime.now(),
        hostname=collect_hostname(),
        uptime=collect_uptime(),
        cpu=collect_cpu(),
        memory=collect_memory(),
        swap=collect_swap(),
        disk=collect_disk('/'),
        partitions=collect_partitions(),
        services=services,
        top_processes=collect_top_processes(),
    )
