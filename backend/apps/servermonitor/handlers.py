"""
Telegram bot command handlers for server monitoring.

All commands require the sender to be the site owner (telegram_owner_id).
Commands: /status, /services, /disk, /tariff, /logs, /backup
"""
from __future__ import annotations

import logging
import subprocess
from typing import Optional

from core.services import SiteSettingsService
from interactions.notifications.telegram_api import TelegramBotAPI

from core.emoji import ce

from .contabo import analyze_tariff, format_tariff_advice
from .formatters import (
    format_cpu,
    format_cpu_alert,
    format_disk_detailed,
    format_full_report,
    format_services,
    format_status_report,
)
from .metrics import (
    collect_cpu,
    collect_disk,
    collect_full_snapshot,
    collect_memory,
    collect_partitions,
    collect_service_status,
    MONITORED_SERVICES,
)

logger = logging.getLogger('servermonitor')

# Commands this module handles
SERVER_COMMANDS = {'/status', '/services', '/disk', '/tariff', '/logs', '/backup'}


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
        api.send_message(tg_id, f'❌ Xatolik: <code>{exc}</code>')


def _handle_services(tg_id: int, api: TelegramBotAPI) -> None:
    """Systemd services status."""
    api.send_chat_action(tg_id, 'typing')
    try:
        services = [collect_service_status(s) for s in MONITORED_SERVICES]
        text = format_services(services)

        # Add inline keyboard for restart actions
        keyboard = _build_services_keyboard(services)
        api.send_message(tg_id, text, reply_markup=keyboard)
    except Exception as exc:
        logger.error('Failed to collect services: %s', exc)
        api.send_message(tg_id, f'❌ Xatolik: <code>{exc}</code>')


def _build_services_keyboard(services: list) -> dict:
    """Build inline keyboard with restart buttons for inactive services."""
    rows = []
    for svc in services:
        if not svc.active:
            rows.append([{
                'text': f'🔄 Restart {svc.name}',
                'callback_data': f'svc_restart_{svc.name}',
            }])
    if not rows:
        return {}
    rows.append([{'text': '🔄 Barchasini yangilash', 'callback_data': 'svc_refresh'}])
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
        api.send_message(tg_id, f'❌ Xatolik: <code>{exc}</code>')


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
        api.send_message(tg_id, f'❌ Xatolik: <code>{exc}</code>')


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

    if service not in MONITORED_SERVICES:
        api.send_message(
            tg_id,
            f'⚠️ Noma\'lum servis: <code>{service}</code>\n'
            f'Mavjud: {", ".join(MONITORED_SERVICES)}',
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
            f'📋 <b>Logs: {service}</b> (oxirgi {n_lines} qator)\n\n'
            f'<pre>{output}</pre>'
        )
        api.send_message(tg_id, text)
    except FileNotFoundError:
        api.send_message(tg_id, '⚠️ journalctl topilmadi (systemd yo\'q)')
    except Exception as exc:
        api.send_message(tg_id, f'❌ Xatolik: <code>{exc}</code>')


def _handle_backup(tg_id: int, api: TelegramBotAPI) -> None:
    """Trigger a PostgreSQL database backup."""
    api.send_message(tg_id, '🔄 Backup boshlanmoqda...')
    try:
        result = subprocess.run(
            ['pg_dump', '-Fc', '-f', '/tmp/jaysonkhan_backup.dump', 'jaysonkhan_db'],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            # Get file size
            import os
            size_mb = 0
            try:
                size_mb = round(os.path.getsize('/tmp/jaysonkhan_backup.dump') / (1024 * 1024), 1)
            except OSError:
                pass
            api.send_message(
                tg_id,
                f'✅ <b>Backup tayyor!</b>\n'
                f'📁 <code>/tmp/jaysonkhan_backup.dump</code>\n'
                f'💾 Hajm: {size_mb}MB',
            )
        else:
            api.send_message(tg_id, f'❌ Backup xatolik:\n<pre>{result.stderr[:1000]}</pre>')
    except Exception as exc:
        api.send_message(tg_id, f'❌ Backup xatolik: <code>{exc}</code>')


def handle_server_callback(callback_data: str, callback_query: dict, api: TelegramBotAPI) -> bool:
    """Handle callback queries for server monitor inline buttons."""
    if not callback_data.startswith('svc_'):
        return False

    tg_id = callback_query['from']['id']
    cb_id = callback_query['id']

    if not is_owner(tg_id):
        api.answer_callback_query(cb_id, '🔒 Faqat owner uchun')
        return True

    if callback_data == 'svc_refresh':
        # Refresh services list
        services = [collect_service_status(s) for s in MONITORED_SERVICES]
        text = format_services(services)
        keyboard = _build_services_keyboard(services)
        msg = callback_query.get('message', {})
        if msg.get('message_id') and msg.get('chat', {}).get('id'):
            api.edit_message_reply_markup(
                chat_id=msg['chat']['id'],
                message_id=msg['message_id'],
                reply_markup=keyboard,
            )
        api.answer_callback_query(cb_id, 'Yangilandi ✓')
        return True

    if callback_data.startswith('svc_restart_'):
        service_name = callback_data.replace('svc_restart_', '')
        if service_name not in MONITORED_SERVICES:
            api.answer_callback_query(cb_id, '⚠️ Noma\'lum servis')
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
