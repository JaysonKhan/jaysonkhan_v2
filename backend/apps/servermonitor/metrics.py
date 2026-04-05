"""
Server metrics collection.

Uses psutil to gather CPU, RAM, disk, swap, uptime, and load averages.
All functions return plain dicts — formatting is in formatters.py.
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
    name: str
    active: bool
    status: str  # 'running', 'dead', 'inactive', 'not-found'
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


def collect_cpu() -> CpuMetrics:
    per_core = psutil.cpu_percent(interval=1, percpu=True)
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


def collect_service_status(service_name: str) -> ServiceStatus:
    """Check systemd service status via systemctl."""
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', service_name],
            capture_output=True, text=True, timeout=5,
        )
        status_text = result.stdout.strip()
        active = status_text == 'active'

        # Get memory usage
        mem_mb = None
        if active:
            try:
                mem_result = subprocess.run(
                    ['systemctl', 'show', service_name, '--property=MemoryCurrent'],
                    capture_output=True, text=True, timeout=5,
                )
                mem_line = mem_result.stdout.strip()
                if '=' in mem_line:
                    val = mem_line.split('=')[1]
                    if val.isdigit():
                        mem_mb = round(int(val) / (1024 * 1024), 1)
            except Exception:
                pass

        # Get uptime (ActiveEnterTimestamp)
        uptime_str = None
        if active:
            try:
                ts_result = subprocess.run(
                    ['systemctl', 'show', service_name, '--property=ActiveEnterTimestamp'],
                    capture_output=True, text=True, timeout=5,
                )
                ts_line = ts_result.stdout.strip()
                if '=' in ts_line and ts_line.split('=')[1].strip():
                    uptime_str = ts_line.split('=', 1)[1].strip()
            except Exception:
                pass

        return ServiceStatus(
            name=service_name,
            active=active,
            status=status_text if status_text else 'unknown',
            uptime=uptime_str,
            memory_mb=mem_mb,
        )
    except FileNotFoundError:
        return ServiceStatus(name=service_name, active=False, status='no-systemctl')
    except Exception:
        return ServiceStatus(name=service_name, active=False, status='error')


MONITORED_SERVICES = [
    'jaysonkhan',
    'talabaovozi',
    'nginx',
    'postgresql',
    'redis-server',
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
    services = [collect_service_status(s) for s in MONITORED_SERVICES]
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
