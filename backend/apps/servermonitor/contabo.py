"""
Contabo VPS tariff advisor.

Compares current server usage against the known Contabo plan limits
and suggests upgrade/downgrade based on utilization patterns.
"""
from __future__ import annotations

from dataclasses import dataclass

from .metrics import CpuMetrics, DiskMetrics, MemoryMetrics

# ── Current Contabo Plan ─────────────────────────────────────────────────────

CURRENT_PLAN = {
    'name': 'Cloud VPS 2',
    'cpu_cores': 6,
    'ram_gb': 11,
    'disk_gb': 96,
    'price_eur': 13.99,
}

# ── Contabo VPS Tiers (approximate EUR/month pricing, April 2026) ────────────

CONTABO_PLANS = [
    {'name': 'Cloud VPS 1', 'cpu_cores': 4, 'ram_gb': 6, 'disk_gb': 50, 'price_eur': 7.49},
    {'name': 'Cloud VPS 2', 'cpu_cores': 6, 'ram_gb': 11, 'disk_gb': 96, 'price_eur': 13.99},
    {'name': 'Cloud VPS 3', 'cpu_cores': 8, 'ram_gb': 16, 'disk_gb': 200, 'price_eur': 19.99},
    {'name': 'Cloud VPS 4', 'cpu_cores': 12, 'ram_gb': 24, 'disk_gb': 400, 'price_eur': 29.99},
]


@dataclass
class TariffAdvice:
    current_plan: dict
    recommendation: str  # 'upgrade', 'downgrade', 'keep'
    reason: str
    suggested_plan: dict | None
    details: list[str]


def analyze_tariff(
    cpu: CpuMetrics,
    mem: MemoryMetrics,
    disk: DiskMetrics,
) -> TariffAdvice:
    """Analyze usage vs plan limits and advise on tariff changes."""
    plan = CURRENT_PLAN
    details = []
    needs_upgrade = False
    can_downgrade = True

    # CPU analysis
    cpu_util = cpu.total_percent
    if cpu_util > 80:
        details.append(f'🔴 CPU: {cpu_util}% — consistently high, need more cores')
        needs_upgrade = True
    elif cpu_util > 60:
        details.append(f'🟡 CPU: {cpu_util}% — moderate load')
        can_downgrade = False
    else:
        details.append(f'🟢 CPU: {cpu_util}% — comfortable headroom')

    # Check individual cores at high load
    hot_cores = sum(1 for c in cpu.cores if c.percent > 80)
    if hot_cores >= plan['cpu_cores'] // 2:
        details.append(f'⚠️ {hot_cores}/{plan["cpu_cores"]} cores above 80%')
        needs_upgrade = True

    # RAM analysis
    ram_pct = mem.percent
    if ram_pct > 85:
        details.append(f'🔴 RAM: {ram_pct}% ({mem.used_gb}/{mem.total_gb}GB) — critically high')
        needs_upgrade = True
    elif ram_pct > 65:
        details.append(f'🟡 RAM: {ram_pct}% — moderate usage')
        can_downgrade = False
    else:
        details.append(f'🟢 RAM: {ram_pct}% — plenty of room')

    # Disk analysis
    disk_pct = disk.percent
    if disk_pct > 85:
        details.append(f'🔴 Disk: {disk_pct}% ({disk.used_gb}/{disk.total_gb}GB) — running low')
        needs_upgrade = True
    elif disk_pct > 60:
        details.append(f'🟡 Disk: {disk_pct}% — watch growth')
        can_downgrade = False
    else:
        details.append(f'🟢 Disk: {disk_pct}% — ample space')

    # Determine recommendation
    if needs_upgrade:
        suggested = _find_upgrade(plan)
        return TariffAdvice(
            current_plan=plan,
            recommendation='upgrade',
            reason='Resurlar limitga yaqinlashmoqda',
            suggested_plan=suggested,
            details=details,
        )
    elif can_downgrade:
        suggested = _find_downgrade(plan)
        if suggested:
            return TariffAdvice(
                current_plan=plan,
                recommendation='downgrade',
                reason='Resurslar kam ishlatilmoqda — tejash mumkin',
                suggested_plan=suggested,
                details=details,
            )

    return TariffAdvice(
        current_plan=plan,
        recommendation='keep',
        reason='Hozirgi plan optimal',
        suggested_plan=None,
        details=details,
    )


def _find_upgrade(current: dict) -> dict | None:
    for p in CONTABO_PLANS:
        if p['cpu_cores'] > current['cpu_cores'] and p['ram_gb'] > current['ram_gb']:
            return p
    return None


def _find_downgrade(current: dict) -> dict | None:
    for p in reversed(CONTABO_PLANS):
        if p['cpu_cores'] < current['cpu_cores'] and p['ram_gb'] < current['ram_gb']:
            return p
    return None


def format_tariff_advice(advice: TariffAdvice) -> str:
    """Format tariff advice as a Telegram-ready message."""
    from .formatters import _ce

    rec_emoji = {
        'upgrade': '⬆️',
        'downgrade': '⬇️',
        'keep': '✅',
    }
    emoji = rec_emoji.get(advice.recommendation, '📋')

    money = _ce('money', '💰')
    lines = [
        f'{money} <b>Contabo Tariff Advisor</b>\n',
        f'📦 Current: <b>{advice.current_plan["name"]}</b>',
        f'{advice.current_plan["cpu_cores"]} CPU / {advice.current_plan["ram_gb"]}GB RAM / {advice.current_plan["disk_gb"]}GB Disk',
        f'€{advice.current_plan["price_eur"]}/mo\n',
        f'{emoji} <b>Tavsiya: {advice.recommendation.upper()}</b>',
        f'📝 {advice.reason}\n',
    ]

    for d in advice.details:
        lines.append(f'  {d}')

    if advice.suggested_plan:
        sp = advice.suggested_plan
        lines.append(f'\n📦 Tavsiya etilgan plan: <b>{sp["name"]}</b>')
        lines.append(f'   {sp["cpu_cores"]} CPU / {sp["ram_gb"]}GB RAM / {sp["disk_gb"]}GB Disk')
        lines.append(f'   €{sp["price_eur"]}/mo')

        diff = sp['price_eur'] - advice.current_plan['price_eur']
        if diff > 0:
            lines.append(f'   💸 +€{diff:.2f}/mo qo\'shimcha')
        elif diff < 0:
            lines.append(f'   💰 €{abs(diff):.2f}/mo tejash!')

    return '\n'.join(lines)
