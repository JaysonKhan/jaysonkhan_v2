"""
Telegram bot handlers for the shared admin IP allowlist.

Owner-only. Three ways to add an IP, all ending in an explicit confirm tap:
  1. /ip add 1.2.3.4 [label]           — direct command
  2. paste a bare IP in private chat    — bot offers to add it
  3. https://jaysonkhan.com/myip/       — one-tap deep link back to the bot

The bot writes ONLY the shared JSON file (core.allowed_ips) — it never
touches any project's .env, and no service restart is needed: every site's
admin middleware re-reads the file per request.
"""
from __future__ import annotations

import re

from core.allowed_ips import (
    add_ip,
    decode_ip,
    encode_ip,
    load_data,
    normalize_ip,
    remove_ip,
)
from core.emoji import ce
from django.conf import settings
from django.utils.html import escape
from interactions.notifications.telegram_api import TelegramBotAPI

MYIP_URL = 'https://jaysonkhan.com/myip/'

# Best-effort read-only peek at the OTHER projects' .env base lists so the
# panel shows the full effective picture per site. Never written to.
ENV_PEEKS = {
    'uzexam': ('/var/www/uzexam/backend/.env', '/var/www/uzexam/.env'),
    'edustats-web': ('/var/www/talabaovozi_web/web/.env',),
}

_ENV_LINE = re.compile(r'^ADMIN_ALLOWED_IPS\s*=\s*(.*)$')


def _peek_env_ips(paths: tuple[str, ...]) -> list[str] | None:
    """Parse ADMIN_ALLOWED_IPS out of a .env file. None = unreadable."""
    for path in paths:
        try:
            with open(path, encoding='utf-8') as fh:
                for line in fh:
                    m = _ENV_LINE.match(line.strip())
                    if m:
                        raw = m.group(1).strip().strip('"\'')
                        return [p.strip() for p in raw.split(',') if p.strip()]
            return []  # file readable, key absent
        except OSError:
            continue
    return None


def _panel_text() -> str:
    data = load_data()
    shield = ce('lock', '🛡')
    lines = [f'{shield} <b>Admin IP Allowlist</b> — barcha saytlar\n']

    lines.append(f'{ce("bot", "🤖")} <b>Dinamik (bot boshqaradi, restart kerak emas):</b>')
    if data['ips']:
        for e in data['ips']:
            label = f' — {escape(e.get("label", ""))}' if e.get('label') else ''
            added = (e.get('added') or '')[:16].replace('T', ' ')
            lines.append(f'  • <code>{e["ip"]}</code>{label} <i>({added})</i>')
    else:
        lines.append('  <i>bo\'sh — hali IP qo\'shilmagan</i>')

    gear = ce('config_icon', '⚙️')
    lines.append(f'\n{gear} <b>.env bazaviy ro\'yxatlar</b> (faqat ma\'lumot):')
    own = getattr(settings, 'ADMIN_ALLOWED_IPS', [])
    lines.append(f'  jaysonkhan: <code>{", ".join(own) or "—"}</code>')
    for name, paths in ENV_PEEKS.items():
        ips = _peek_env_ips(paths)
        shown = ', '.join(ips) if ips else ('bo\'sh' if ips == [] else 'o\'qib bo\'lmadi')
        lines.append(f'  {name}: <code>{shown}</code>')

    history = data.get('history', [])
    if history:
        lines.append(f'\n{ce("clock", "🕐")} <b>So\'nggi o\'zgarishlar:</b>')
        for h in reversed(history[-5:]):
            op = '➕' if h.get('op') == 'add' else '➖'
            at = (h.get('at') or '')[:16].replace('T', ' ')
            lines.append(f'  {op} <code>{h.get("ip", "?")}</code> <i>({at})</i>')

    lines.append(
        f'\n{ce("scam_warn", "ℹ️")} Yangi IP <b>bir zumda</b> jaysonkhan + uzexam + '
        f'edustats admin panellariga tarqaladi. .env fayllarga tegilmaydi.'
    )
    return '\n'.join(lines)


def _panel_keyboard() -> dict:
    return {'inline_keyboard': [
        [
            {'text': '➕ IP qo\'shish', 'callback_data': 'ip_addhelp'},
            {'text': '🗑 O\'chirish', 'callback_data': 'ip_delmenu'},
        ],
        [
            {'text': '🌍 IP manzilimni aniqlash', 'url': MYIP_URL},
        ],
        [
            {'text': '🔄 Yangilash', 'callback_data': 'ip_menu'},
        ],
    ]}


def send_panel(tg_id: int, api: TelegramBotAPI) -> None:
    api.send_message(tg_id, _panel_text(), reply_markup=_panel_keyboard())


def _confirm_add_prompt(tg_id: int, ip: str, api: TelegramBotAPI, *, label: str = '') -> None:
    token = encode_ip(ip)
    note = f' (izoh: {escape(label)})' if label else ''
    api.send_message(
        tg_id,
        f'{ce("lock", "🛡")} <code>{ip}</code>{note} barcha saytlarning admin '
        f'allowlist\'iga qo\'shilsinmi?',
        reply_markup={'inline_keyboard': [[
            {'text': '✅ Qo\'shish', 'callback_data': f'ipaok_{token}'},
            {'text': '❌ Bekor', 'callback_data': 'ip_menu'},
        ]]},
    )


def handle_ip_command(command: str, message: dict, api: TelegramBotAPI) -> bool:
    """/ip [add <ip> [label] | del <ip>] — owner check is done by the caller."""
    if command != '/ip':
        return False

    tg_id = message['from']['id']
    parts = message.get('text', '').split()
    sub = parts[1].lower() if len(parts) > 1 else ''

    if sub == 'add' and len(parts) > 2:
        ip = normalize_ip(parts[2])
        if not ip:
            api.send_message(tg_id, f'{ce("error", "❌")} Noto\'g\'ri IP: <code>{escape(parts[2][:40])}</code>')
            return True
        _confirm_add_prompt(tg_id, ip, api, label=' '.join(parts[3:]))
    elif sub == 'del' and len(parts) > 2:
        ok, msg = remove_ip(parts[2], by=tg_id)
        icon = ce('success', '✅') if ok else ce('error', '❌')
        text = f'{icon} <code>{msg}</code> o\'chirildi.' if ok else f'{icon} {escape(msg)}'
        api.send_message(tg_id, text)
        if ok:
            send_panel(tg_id, api)
    else:
        send_panel(tg_id, api)
    return True


def handle_start_payload(payload: str, tg_id: int, api: TelegramBotAPI) -> bool:
    """Deep link: t.me/<bot>?start=addip_<b64ip> (from the /myip/ page)."""
    if not payload.startswith('addip_'):
        return False
    ip = decode_ip(payload[len('addip_'):])
    if not ip:
        api.send_message(tg_id, f'{ce("error", "❌")} Havoladagi IP o\'qilmadi.')
        return True
    _confirm_add_prompt(tg_id, ip, api)
    return True


def maybe_offer_ip_add(message: dict, api: TelegramBotAPI) -> bool:
    """Owner pasted a bare IP in private chat → offer to allowlist it."""
    text = (message.get('text') or '').strip()
    if not text or len(text) > 45:
        return False
    ip = normalize_ip(text)
    if not ip:
        return False
    _confirm_add_prompt(message['from']['id'], ip, api)
    return True


def handle_ip_callback(data: str, callback_query: dict, api: TelegramBotAPI) -> bool:
    """Callback family: ip_menu / ip_addhelp / ip_delmenu / ipaok_ / ipd_ / ipdok_."""
    if not (data.startswith('ip_') or data.startswith('ipaok_')
            or data.startswith('ipd_') or data.startswith('ipdok_')):
        return False

    tg_id = callback_query['from']['id']
    cb_id = callback_query['id']

    from .handlers import is_owner  # local import — avoids a circular import
    if not is_owner(tg_id):
        api.answer_callback_query(cb_id, '🔒 Faqat owner uchun')
        return True
    msg = callback_query.get('message', {}) or {}
    chat_id = (msg.get('chat') or {}).get('id') or tg_id
    message_id = msg.get('message_id')

    def _edit_or_send(text: str, keyboard: dict | None) -> None:
        if message_id:
            api.edit_message_text(
                chat_id=chat_id, message_id=message_id,
                text=text, reply_markup=keyboard,
            )
        else:
            api.send_message(chat_id, text, reply_markup=keyboard)

    if data == 'ip_menu':
        _edit_or_send(_panel_text(), _panel_keyboard())
        api.answer_callback_query(cb_id, 'Yangilandi ✓')

    elif data == 'ip_addhelp':
        api.answer_callback_query(cb_id)
        api.send_message(
            chat_id,
            f'{ce("scam_warn", "ℹ️")} <b>IP qo\'shish yo\'llari:</b>\n\n'
            f'1. Menga IP manzilni oddiy xabar qilib yuboring — '
            f'masalan <code>84.54.12.7</code>\n'
            f'2. <code>/ip add 84.54.12.7 uy-wifi</code> (izoh ixtiyoriy)\n'
            f'3. <a href="{MYIP_URL}">jaysonkhan.com/myip</a> sahifasini oching — '
            f'IP\'ingizni ko\'rsatadi va bir bosishda botga qaytaradi.\n\n'
            f'Har qanday yo\'lda ham men tasdiq so\'rayman.',
        )

    elif data == 'ip_delmenu':
        entries = load_data()['ips']
        if not entries:
            api.answer_callback_query(cb_id, 'Dinamik ro\'yxat bo\'sh')
            return True
        rows = [
            [{
                'text': f'🗑 {e["ip"]}' + (f' ({e["label"]})' if e.get('label') else ''),
                'callback_data': f'ipd_{encode_ip(e["ip"])}',
            }]
            for e in entries
        ]
        rows.append([{'text': '⬅️ Orqaga', 'callback_data': 'ip_menu'}])
        api.answer_callback_query(cb_id)
        _edit_or_send(
            f'{ce("ban", "🗑")} <b>Qaysi IP o\'chirilsin?</b>\n'
            f'(.env bazaviy IP\'lariga tegilmaydi)',
            {'inline_keyboard': rows},
        )

    elif data.startswith('ipd_'):
        ip = decode_ip(data[len('ipd_'):])
        if not ip:
            api.answer_callback_query(cb_id, 'IP o\'qilmadi')
            return True
        api.answer_callback_query(cb_id)
        _edit_or_send(
            f'{ce("scam_warn", "⚠️")} <code>{ip}</code> barcha saytlar '
            f'allowlist\'idan o\'chirilsinmi?',
            {'inline_keyboard': [[
                {'text': '✅ Ha, o\'chir', 'callback_data': f'ipdok_{data[len("ipd_"):]}'},
                {'text': '❌ Bekor', 'callback_data': 'ip_menu'},
            ]]},
        )

    elif data.startswith('ipdok_'):
        ip = decode_ip(data[len('ipdok_'):])
        ok, res = remove_ip(ip or '', by=tg_id)
        api.answer_callback_query(cb_id, '✓ O\'chirildi' if ok else 'Xatolik')
        if ok:
            _edit_or_send(_panel_text(), _panel_keyboard())
        else:
            api.send_message(chat_id, f'{ce("error", "❌")} {escape(res)}')

    elif data.startswith('ipaok_'):
        ip = decode_ip(data[len('ipaok_'):])
        ok, res = add_ip(ip or '', by=tg_id)
        api.answer_callback_query(cb_id, '✓ Qo\'shildi' if ok else 'Xatolik')
        if ok:
            api.send_message(
                chat_id,
                f'{ce("success", "✅")} <code>{res}</code> qo\'shildi — '
                f'jaysonkhan, uzexam va edustats admin panellarida darhol amal qiladi.',
            )
            send_panel(chat_id, api)
        else:
            api.send_message(chat_id, f'{ce("error", "❌")} {escape(res)}')

    return True
