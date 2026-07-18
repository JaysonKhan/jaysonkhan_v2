"""
Telegram bot command handlers for server monitoring.

All commands require the sender to be the site owner (telegram_owner_id).
Commands: /status, /services, /disk, /tariff, /logs, /backup
v2:       /panel, /web, /ssl, /errors, /top, /db, /restart, /ip
"""
from __future__ import annotations

import logging
import subprocess
import time

from core.emoji import ce
from core.services import SiteSettingsService
from interactions.notifications.telegram_api import TelegramBotAPI

from .contabo import analyze_tariff, format_tariff_advice
from .formatters import (
    format_cpu_alert,
    format_db_report,
    format_disk_detailed,
    format_error_scan,
    format_services,
    format_ssl_checks,
    format_status_report,
    format_top_processes,
    format_web_checks,
)
from .ip_handlers import handle_ip_command
from .ip_handlers import send_panel as send_ip_panel
from .metrics import (
    MONITORED_SERVICES,
    collect_all_service_status,
    collect_cpu,
    collect_disk,
    collect_full_snapshot,
    collect_memory,
    collect_partitions,
    collect_top_processes_sampled,
)
from .web_checks import check_databases, check_http, check_ssl, scan_journal_errors

logger = logging.getLogger('servermonitor')

# Commands this module handles
SERVER_COMMANDS = {
    '/status', '/services', '/disk', '/tariff', '/logs', '/backup',
    '/panel', '/web', '/ssl', '/errors', '/top', '/db', '/restart', '/ip',
}

# Allowed systemd unit names (MONITORED_SERVICES is list[dict]; we only ever
# accept/operate on these exact unit strings). Ordered for stable display.
_UNIT_NAMES = tuple(cfg['unit'] for cfg in MONITORED_SERVICES)

# /restart menu targets: app units + nginx only. Postgres/Redis/mail restarts
# take EVERY site down at once — those stay manual (or via the /services
# inactive-service button when one is already down).
_RESTARTABLE_UNITS = tuple(
    cfg['unit'] for cfg in MONITORED_SERVICES if cfg['group'] == 'apps'
) + ('nginx',)

# Units whose restart has a known side effect worth a louder confirm.
_RESTART_WARNINGS = {
    'edustats-bot': (
        '⚠️ edustats-bot restartdan 60s keyin uzbmb FULL sync boshlanadi — '
        'edustats.uz ~10 daqiqa sekinlashadi/000 beradi (o\'zi tiklanadi, '
        'qayta restart QILMANG).'
    ),
}


def _collect_all_services() -> list:
    """Collect status for every monitored service (batched: 2 systemctl calls)."""
    return collect_all_service_status(MONITORED_SERVICES)


def is_owner(telegram_id: int) -> bool:
    """Check if the Telegram user is the site owner."""
    site = SiteSettingsService.get()
    return site.telegram_owner_id and telegram_id == site.telegram_owner_id


def handle_server_command(command: str, message: dict, api: TelegramBotAPI) -> bool:
    """
    Handle a server monitoring command.
    Returns True if the command was handled, False if not a server command.
    """
    if command not in SERVER_COMMANDS:
        return False

    tg_id = message['from']['id']

    if not is_owner(tg_id):
        api.send_message(tg_id, f'{ce("lock", "🔒")} Bu komanda faqat server egasi uchun.')
        return True

    if command == '/status':
        _handle_status(tg_id, api)
    elif command == '/services':
        _handle_services(tg_id, api)
    elif command == '/disk':
        _handle_disk(tg_id, api)
    elif command == '/tariff':
        _handle_tariff(tg_id, api)
    elif command == '/logs':
        _handle_logs(tg_id, message, api)
    elif command == '/backup':
        _handle_backup(tg_id, api)
    elif command == '/panel':
        _handle_panel(tg_id, api)
    elif command == '/web':
        _handle_web(tg_id, api)
    elif command == '/ssl':
        _handle_ssl(tg_id, api)
    elif command == '/errors':
        _handle_errors(tg_id, message, api)
    elif command == '/top':
        _handle_top(tg_id, api)
    elif command == '/db':
        _handle_db(tg_id, api)
    elif command == '/restart':
        _handle_restart_menu(tg_id, api)
    elif command == '/ip':
        handle_ip_command(command, message, api)

    return True


def _handle_status(tg_id: int, api: TelegramBotAPI) -> None:
    """Quick server health snapshot."""
    api.send_chat_action(tg_id, 'typing')
    try:
        snapshot = collect_full_snapshot()
        text = format_status_report(snapshot)

        # Check for CPU alert
        alert = format_cpu_alert(snapshot.cpu, threshold=75.0)
        if alert:
            text += '\n\n' + alert

        api.send_message(tg_id, text)
    except Exception as exc:
        logger.error('Failed to collect status: %s', exc)
        api.send_message(tg_id, f'{ce("error", "❌")} Xatolik: <code>{exc}</code>')


def _handle_services(tg_id: int, api: TelegramBotAPI) -> None:
    """Systemd services status."""
    api.send_chat_action(tg_id, 'typing')
    try:
        services = _collect_all_services()
        text = format_services(services)

        # Add inline keyboard for restart actions
        keyboard = _build_services_keyboard(services)
        api.send_message(tg_id, text, reply_markup=keyboard)
    except Exception as exc:
        logger.error('Failed to collect services: %s', exc)
        api.send_message(tg_id, f'{ce("error", "❌")} Xatolik: <code>{exc}</code>')


def _build_services_keyboard(services: list) -> dict:
    """Build inline keyboard with restart buttons for inactive services."""
    rows = []
    for svc in services:
        if not svc.active:
            rows.append([{
                'text': f'{ce("swap", "🔄")} Restart {svc.name}',
                'callback_data': f'svc_restart_{svc.name}',
            }])
    if not rows:
        return {}
    rows.append([{'text': f'{ce("swap", "🔄")} Yangilash', 'callback_data': 'svc_refresh'}])
    return {'inline_keyboard': rows}


def _handle_disk(tg_id: int, api: TelegramBotAPI) -> None:
    """Detailed disk usage breakdown."""
    api.send_chat_action(tg_id, 'typing')
    try:
        partitions = collect_partitions()
        text = format_disk_detailed(partitions)
        api.send_message(tg_id, text)
    except Exception as exc:
        logger.error('Failed to collect disk: %s', exc)
        api.send_message(tg_id, f'{ce("error", "❌")} Xatolik: <code>{exc}</code>')


def _handle_tariff(tg_id: int, api: TelegramBotAPI) -> None:
    """Contabo tariff advisor."""
    api.send_chat_action(tg_id, 'typing')
    try:
        cpu = collect_cpu()
        mem = collect_memory()
        disk = collect_disk('/')
        advice = analyze_tariff(cpu, mem, disk)
        text = format_tariff_advice(advice)
        api.send_message(tg_id, text)
    except Exception as exc:
        logger.error('Failed tariff analysis: %s', exc)
        api.send_message(tg_id, f'{ce("error", "❌")} Xatolik: <code>{exc}</code>')


def _handle_logs(tg_id: int, message: dict, api: TelegramBotAPI) -> None:
    """Last N lines of journalctl for a service. Usage: /logs [service] [lines]"""
    parts = message.get('text', '').split()
    service = parts[1] if len(parts) > 1 else 'jaysonkhan'
    n_lines = 20

    if len(parts) > 2:
        try:
            n_lines = min(int(parts[2]), 50)
        except ValueError:
            pass

    if service not in _UNIT_NAMES:
        api.send_message(
            tg_id,
            f'{ce("scam_warn", "⚠️")} Noma\'lum servis: <code>{service}</code>\n'
            f'Mavjud: {", ".join(_UNIT_NAMES)}',
        )
        return

    try:
        result = subprocess.run(
            ['journalctl', '-u', service, '-n', str(n_lines), '--no-pager', '-o', 'short-iso'],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.strip() or result.stderr.strip() or 'Log topilmadi'
        # Truncate to fit Telegram message limit (4096 chars)
        if len(output) > 3800:
            output = output[-3800:]
            output = '... (kesildi)\n' + output

        text = (
            f'{ce("logs_icon", "📋")} <b>Logs: {service}</b> (oxirgi {n_lines} qator)\n\n'
            f'<pre>{output}</pre>'
        )
        api.send_message(tg_id, text)
    except FileNotFoundError:
        api.send_message(tg_id, f'{ce("scam_warn", "⚠️")} journalctl topilmadi (systemd yo\'q)')
    except Exception as exc:
        api.send_message(tg_id, f'{ce("error", "❌")} Xatolik: <code>{exc}</code>')


def _handle_backup(tg_id: int, api: TelegramBotAPI) -> None:
    """Trigger a PostgreSQL database backup.

    The dump is written to a deploy-user-owned directory (mode 0700) with the
    file itself locked to 0600 — never to world-readable /tmp.
    """
    import os

    api.send_message(tg_id, f'{ce("swap", "🔄")} Backup boshlanmoqda...')

    backup_dir = '/var/www/jaysonkhan/backups'
    backup_path = os.path.join(backup_dir, 'jaysonkhan_db.dump')
    try:
        # Private, owner-only directory; tighten even if it pre-existed.
        os.makedirs(backup_dir, mode=0o700, exist_ok=True)
        os.chmod(backup_dir, 0o700)
        # Pre-create the target file at 0600 so pg_dump never leaves a
        # world-readable window (pg_dump -f opens an existing file in place).
        fd = os.open(backup_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.close(fd)

        result = subprocess.run(
            ['pg_dump', '-Fc', '-f', backup_path, 'jaysonkhan_db'],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            os.chmod(backup_path, 0o600)
            size_mb = 0
            try:
                size_mb = round(os.path.getsize(backup_path) / (1024 * 1024), 1)
            except OSError:
                pass
            api.send_message(
                tg_id,
                f'{ce("success", "✅")} <b>Backup tayyor!</b>\n'
                f'{ce("backup_icon", "📁")} <code>{backup_path}</code>\n'
                f'{ce("backup_icon", "💾")} Hajm: {size_mb}MB',
            )
        else:
            api.send_message(tg_id, f'{ce("error", "❌")} Backup xatolik:\n<pre>{result.stderr[:1000]}</pre>')
    except Exception as exc:
        api.send_message(tg_id, f'❌ Backup xatolik: <code>{exc}</code>')


# ── v2 handlers ──────────────────────────────────────────────────────────────


def _handle_web(tg_id: int, api: TelegramBotAPI) -> None:
    """HTTP health of every public site + localhost-only internal APIs."""
    api.send_chat_action(tg_id, 'typing')
    try:
        api.send_message(tg_id, format_web_checks(check_http()))
    except Exception as exc:
        logger.error('web check failed: %s', exc)
        api.send_message(tg_id, f'{ce("error", "❌")} Xatolik: <code>{exc}</code>')


def _handle_ssl(tg_id: int, api: TelegramBotAPI) -> None:
    """TLS certificate expiry for every domain (manual DNS-01 renewals)."""
    api.send_chat_action(tg_id, 'typing')
    try:
        api.send_message(tg_id, format_ssl_checks(check_ssl()))
    except Exception as exc:
        logger.error('ssl check failed: %s', exc)
        api.send_message(tg_id, f'{ce("error", "❌")} Xatolik: <code>{exc}</code>')


def _handle_errors(tg_id: int, message: dict, api: TelegramBotAPI) -> None:
    """journalctl error counts. Usage: /errors [soat] (default 6, max 48)."""
    api.send_chat_action(tg_id, 'typing')
    parts = message.get('text', '').split()
    hours = 6
    if len(parts) > 1:
        try:
            hours = max(1, min(int(parts[1]), 48))
        except ValueError:
            pass
    try:
        api.send_message(tg_id, format_error_scan(scan_journal_errors(hours), hours))
    except Exception as exc:
        logger.error('error scan failed: %s', exc)
        api.send_message(tg_id, f'{ce("error", "❌")} Xatolik: <code>{exc}</code>')


def _handle_top(tg_id: int, api: TelegramBotAPI) -> None:
    """Top processes by CPU (sampled) with RAM column."""
    api.send_chat_action(tg_id, 'typing')
    try:
        procs = collect_top_processes_sampled(8)
        api.send_message(tg_id, format_top_processes(procs))
    except Exception as exc:
        logger.error('top failed: %s', exc)
        api.send_message(tg_id, f'{ce("error", "❌")} Xatolik: <code>{exc}</code>')


def _handle_db(tg_id: int, api: TelegramBotAPI) -> None:
    """PostgreSQL database sizes + active connections."""
    api.send_chat_action(tg_id, 'typing')
    try:
        rows, connections, error = check_databases()
        api.send_message(tg_id, format_db_report(rows, connections, error))
    except Exception as exc:
        logger.error('db check failed: %s', exc)
        api.send_message(tg_id, f'{ce("error", "❌")} Xatolik: <code>{exc}</code>')


def _handle_restart_menu(tg_id: int, api: TelegramBotAPI) -> None:
    """Two-step restart: pick a unit, then confirm."""
    rows = [
        [{'text': f'🔄 {unit}', 'callback_data': f'rst_{unit}'}]
        for unit in _RESTARTABLE_UNITS
    ]
    rows.append([{'text': '❌ Bekor', 'callback_data': 'rst_cancel'}])
    api.send_message(
        tg_id,
        f'{ce("swap", "🔄")} <b>Qaysi servis restart qilinsin?</b>\n'
        f'(tasdiq so\'raladi; infra servislarga /services orqali)',
        reply_markup={'inline_keyboard': rows},
    )


def _handle_panel(tg_id: int, api: TelegramBotAPI) -> None:
    """Control center — every view one tap away."""
    keyboard = {'inline_keyboard': [
        [
            {'text': '📊 Status', 'callback_data': 'pnl_status'},
            {'text': '🔧 Servislar', 'callback_data': 'pnl_services'},
        ],
        [
            {'text': '🌐 Web', 'callback_data': 'pnl_web'},
            {'text': '🔐 SSL', 'callback_data': 'pnl_ssl'},
        ],
        [
            {'text': '🧾 Errorlar', 'callback_data': 'pnl_errors'},
            {'text': '💿 Disk', 'callback_data': 'pnl_disk'},
        ],
        [
            {'text': '🏆 Top', 'callback_data': 'pnl_top'},
            {'text': '🐘 DB', 'callback_data': 'pnl_db'},
        ],
        [
            {'text': '🛡 IP Allowlist', 'callback_data': 'pnl_ip'},
            {'text': '🔄 Restart', 'callback_data': 'pnl_restart'},
        ],
    ]}
    api.send_message(
        tg_id,
        f'{ce("server", "🎛")} <b>Boshqaruv paneli</b>\n'
        f'Kerakli bo\'limni tanlang:',
        reply_markup=keyboard,
    )


def handle_server_callback(callback_data: str, callback_query: dict, api: TelegramBotAPI) -> bool:
    """Handle callback queries for server monitor inline buttons."""
    if not callback_data.startswith(('svc_', 'pnl_', 'rst_', 'rstok_')):
        return False

    tg_id = callback_query['from']['id']
    cb_id = callback_query['id']

    if not is_owner(tg_id):
        api.answer_callback_query(cb_id, '🔒 Faqat owner uchun')
        return True

    # ── Control panel buttons → run the matching view as a fresh message ──
    if callback_data.startswith('pnl_'):
        key = callback_data[len('pnl_'):]
        api.answer_callback_query(cb_id)
        simple = {
            'status': _handle_status,
            'services': _handle_services,
            'web': _handle_web,
            'ssl': _handle_ssl,
            'disk': _handle_disk,
            'top': _handle_top,
            'db': _handle_db,
            'restart': _handle_restart_menu,
        }
        if key == 'errors':
            _handle_errors(tg_id, {'text': '/errors'}, api)
        elif key == 'ip':
            send_ip_panel(tg_id, api)
        elif key in simple:
            simple[key](tg_id, api)
        return True

    # ── Two-step restart flow ─────────────────────────────────────────────
    if callback_data == 'rst_cancel':
        api.answer_callback_query(cb_id, 'Bekor qilindi')
        return True

    if callback_data.startswith('rstok_'):
        unit = callback_data[len('rstok_'):]
        if unit not in _RESTARTABLE_UNITS:
            api.answer_callback_query(cb_id, 'Noma\'lum servis')
            return True
        api.answer_callback_query(cb_id, f'🔄 {unit} restart...')
        try:
            subprocess.run(
                ['sudo', 'systemctl', 'restart', unit],
                capture_output=True, timeout=60,
            )
            time.sleep(2)
            cfg = [c for c in MONITORED_SERVICES if c['unit'] == unit]
            status = collect_all_service_status(cfg or [{'unit': unit}])
            state = status[0].status if status else '?'
            icon = ce('success', '✅') if (status and status[0].active) else ce('critical', '🔴')
            api.send_message(
                tg_id,
                f'{icon} <code>{unit}</code> restart yakunlandi — '
                f'holat: <code>{state}</code>',
            )
        except Exception as exc:
            api.send_message(tg_id, f'{ce("error", "❌")} Restart xato: <code>{exc}</code>')
        return True

    if callback_data.startswith('rst_'):
        unit = callback_data[len('rst_'):]
        if unit not in _RESTARTABLE_UNITS:
            api.answer_callback_query(cb_id, 'Noma\'lum servis')
            return True
        warn = _RESTART_WARNINGS.get(unit, '')
        text = f'{ce("swap", "🔄")} <code>{unit}</code> restart qilinsinmi?'
        if warn:
            text += f'\n\n{warn}'
        api.answer_callback_query(cb_id)
        api.send_message(tg_id, text, reply_markup={'inline_keyboard': [[
            {'text': '✅ Ha, restart', 'callback_data': f'rstok_{unit}'},
            {'text': '❌ Bekor', 'callback_data': 'rst_cancel'},
        ]]})
        return True

    if callback_data == 'svc_refresh':
        # Refresh services list
        services = _collect_all_services()
        text = format_services(services)
        keyboard = _build_services_keyboard(services)
        msg = callback_query.get('message', {})
        if msg.get('message_id') and msg.get('chat', {}).get('id'):
            api.edit_message_text(
                chat_id=msg['chat']['id'],
                message_id=msg['message_id'],
                text=text,
                reply_markup=keyboard,
            )
        api.answer_callback_query(cb_id, 'Yangilandi ✓')
        return True

    if callback_data.startswith('svc_restart_'):
        service_name = callback_data.replace('svc_restart_', '')
        if service_name not in _UNIT_NAMES:
            api.answer_callback_query(cb_id, 'Noma\'lum servis')
            return True

        try:
            subprocess.run(
                ['sudo', 'systemctl', 'restart', service_name],
                capture_output=True, timeout=30,
            )
            api.answer_callback_query(cb_id, f'🔄 {service_name} restart qilindi')
        except Exception as exc:
            api.answer_callback_query(cb_id, f'❌ {exc}')
        return True

    return False
