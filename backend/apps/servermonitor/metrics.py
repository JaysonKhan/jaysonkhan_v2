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

import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import psutil

# Absolute path to systemctl, resolved once at import. The gunicorn
# systemd unit ships PATH=<venv>/bin only — when admin "Run now"
# spawns a subprocess from a worker, a bare `systemctl` lookup raises
# FileNotFoundError and the whole monitor falsely reports every unit
# as "no-systemctl". Resolving against a known set of system paths
# avoids that without depending on the inherited PATH.
_SYSTEMCTL = (
    shutil.which('systemctl', path='/usr/bin:/bin:/usr/sbin:/sbin')
    or '/usr/bin/systemctl'
)


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

    interval=5 — sustained sample. Recommended for cron-driven reports and
    alerts where we care about real overload, not transient bursts.

    total_percent is derived as the average of per-core values so it always
    reflects the same measurement window as the individual cores. Using a
    separate psutil.cpu_percent(interval=0) call for total was wrong: it
    measured a different (and uncontrolled) time window, producing impossible
    combinations like total=2.6% while all cores showed 76-100%.
    """
    per_core = psutil.cpu_percent(interval=interval, percpu=True)
    load = psutil.getloadavg()
    cores = [CpuCoreInfo(core=i, percent=p) for i, p in enumerate(per_core)]
    total = round(sum(per_core) / len(per_core), 1) if per_core else 0.0
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
            [_SYSTEMCTL, *args],
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
                mem_bytes = int(val)
                if 0 < mem_bytes < (1 << 62):
                    mem_mb = round(mem_bytes / (1024 * 1024), 1)

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
    {'unit': 'edustats-web',       'group': 'apps',     'display': 'EduStats Web',          'critical': True},
    {'unit': 'edustats-bot',       'group': 'apps',     'display': 'EduStats Bot',          'critical': True},
    {'unit': 'uzexam',             'group': 'apps',     'display': 'UzExam Web',            'critical': True},
    {'unit': 'uzexam-bot',         'group': 'apps',     'display': 'UzExam Bot',            'critical': True},
    {'unit': 'vaygo-web',          'group': 'apps',     'display': 'Vaygo Web',             'critical': True},
    {'unit': 'vaygo-bot',          'group': 'apps',     'display': 'Vaygo Bot',             'critical': True},
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


def collect_all_service_status(
    configs: Optional[list[dict]] = None,
) -> list[ServiceStatus]:
    """Batched status for many units — 2 systemctl calls total, not 3N.

    The per-unit ``collect_service_status`` spawns 3 subprocesses (is-active
    + 2× show); for the 11 monitored units that is 33 spawns (~1s wall) on
    every /status and every health-check run. ``systemctl`` takes many units
    per call:

      - ``is-active u1 u2 …``   → one status line per unit, in order
      - ``show u1 u2 … -p …``   → one blank-line-separated block per unit

    so the whole sweep collapses to 2 spawns (~0.06s). Unprobeable results
    ('no-systemctl' when the binary is unreachable) are reported per unit
    exactly as the single-unit path does, so the health-check's
    flap-suppression logic is unchanged.
    """
    cfgs = configs if configs is not None else MONITORED_SERVICES
    units = [c['unit'] for c in cfgs]
    if not units:
        return []

    raw = _systemctl('is-active', *units)
    lines = raw.split('\n') if raw else []
    # Empty output AND no systemctl binary → every unit is unprobeable.
    no_systemctl = (not raw) and (not _systemctl('--version'))

    statuses: list[str] = []
    for i in range(len(units)):
        if no_systemctl:
            statuses.append('no-systemctl')
        elif i < len(lines) and lines[i].strip():
            statuses.append(lines[i].strip())
        else:
            statuses.append('unknown')

    # Memory + uptime only for active units — one show call for all of them.
    active_units = [u for u, s in zip(units, statuses) if s == 'active']
    mem_by_unit: dict[str, float] = {}
    up_by_unit: dict[str, str] = {}
    if active_units:
        shown = _systemctl(
            'show', *active_units,
            '--property=MemoryCurrent,ActiveEnterTimestamp',
        )
        # `systemctl show` emits one property block per unit, in argument
        # order, separated by a blank line. Parse by key, not position.
        for unit, block in zip(active_units, shown.split('\n\n')):
            for ln in block.splitlines():
                if ln.startswith('MemoryCurrent='):
                    val = ln.split('=', 1)[1].strip()
                    if val.isdigit():
                        mem_bytes = int(val)
                        if 0 < mem_bytes < (1 << 62):
                            up_mb = round(mem_bytes / (1024 * 1024), 1)
                            mem_by_unit[unit] = up_mb
                elif ln.startswith('ActiveEnterTimestamp='):
                    stamp = ln.split('=', 1)[1].strip()
                    if stamp:
                        up_by_unit[unit] = stamp

    return [
        ServiceStatus(
            name=cfg['unit'],
            active=(status_text == 'active'),
            status=status_text,
            group=cfg.get('group', ''),
            display=cfg.get('display') or cfg['unit'],
            critical=cfg.get('critical', True),
            uptime=up_by_unit.get(cfg['unit']),
            memory_mb=mem_by_unit.get(cfg['unit']),
        )
        for cfg, status_text in zip(cfgs, statuses)
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


def collect_top_processes_sampled(n: int = 8, *, sample: float = 0.8) -> list[dict]:
    """Top N processes by CPU over a real sample window.

    ``collect_top_processes`` calls ``cpu_percent`` on brand-new Process
    objects, whose first reading is always 0.0 — fine for the daily report
    (long-lived cron gathers other metrics first), useless for an
    interactive /top. Prime every process, sleep, then read the delta.
    """
    procs = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            proc.cpu_percent(None)  # prime the counter
            procs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    time.sleep(sample)
    out = []
    for proc in procs:
        try:
            out.append({
                'pid': proc.pid,
                'name': proc.name(),
                'cpu': round(proc.cpu_percent(None), 1),
                'mem': round(proc.memory_percent(), 1),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    out.sort(key=lambda x: (x['cpu'], x['mem']), reverse=True)
    return out[:n]


def collect_uptime() -> timedelta:
    boot = datetime.fromtimestamp(psutil.boot_time())
    return datetime.now() - boot


def collect_hostname() -> str:
    import socket
    return socket.gethostname()


def collect_full_snapshot(*, cpu_interval: float = 1.0) -> ServerSnapshot:
    """Collect all server metrics in one call.

    cpu_interval=1 (default) for interactive /status.
    cpu_interval=5 for cron-driven reports to avoid false-positive spikes.
    """
    services = collect_all_service_status(MONITORED_SERVICES)
    return ServerSnapshot(
        timestamp=datetime.now(),
        hostname=collect_hostname(),
        uptime=collect_uptime(),
        cpu=collect_cpu(interval=cpu_interval),
        memory=collect_memory(),
        swap=collect_swap(),
        disk=collect_disk('/'),
        partitions=collect_partitions(),
        services=services,
        top_processes=collect_top_processes(),
    )
