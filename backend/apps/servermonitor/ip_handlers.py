"""
Telegram bot handlers for the shared admin IP allowlist.

Owner-only. Three ways to add an IP, all ending in an explicit confirm tap:
  1. /ip add 1.2.3.4 [label]           — direct command
  2. paste a bare IP in private chat    — bot offers to add it
  3. https://jaysonkhan.com/myip/       — one-tap deep link back to the bot

The bot writes ONLY the shared JSON file (core.allowed_ips) — it never
touches any project's .env, and no service restart is needed: every site's
admin middleware re-reads the file per request.

All texts render via core.bot_i18n (uz/ru, resolved per chat).
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
from core.bot_i18n import t
from core.emoji import ce
from django.conf import settings
from django.utils.html import escape
from interactions.notifications.lang import resolve_lang
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


def _fail_text(res, lang: str) -> str:
    """Render an allowed_ips failure tuple (key, params) in *lang*."""
    if isinstance(res, tuple) and len(res) == 2:
        return t(res[0], lang, **res[1])
    return str(res)


def _panel_text(lang: str) -> str:
    data = load_data()
    lines = [t('ip.panel_title', lang, icon=ce('lock', '🛡')) + '\n']

    lines.append(t('ip.dynamic_header', lang, icon=ce('bot', '🤖')))
    if data['ips']:
        for e in data['ips']:
            label = f' — {escape(e.get("label", ""))}' if e.get('label') else ''
            added = (e.get('added') or '')[:16].replace('T', ' ')
            lines.append(f'  • <code>{e["ip"]}</code>{label} <i>({added})</i>')
    else:
        lines.append(f'  {t("ip.empty", lang)}')

    lines.append('\n' + t('ip.env_header', lang, icon=ce('config_icon', '⚙️')))
    own = getattr(settings, 'ADMIN_ALLOWED_IPS', [])
    lines.append(f'  jaysonkhan: <code>{", ".join(own) or "—"}</code>')
    for name, paths in ENV_PEEKS.items():
        ips = _peek_env_ips(paths)
        if ips:
            shown = ', '.join(ips)
        elif ips == []:
            shown = t('ip.env_empty', lang)
        else:
            shown = t('ip.env_unreadable', lang)
        lines.append(f'  {name}: <code>{shown}</code>')

    history = data.get('history', [])
    if history:
        lines.append('\n' + t('ip.history_header', lang, icon=ce('clock', '🕐')))
        for h in reversed(history[-5:]):
            op = '➕' if h.get('op') == 'add' else '➖'
            at = (h.get('at') or '')[:16].replace('T', ' ')
            lines.append(f'  {op} <code>{h.get("ip", "?")}</code> <i>({at})</i>')

    lines.append('\n' + t('ip.footer', lang, icon=ce('scam_warn', 'ℹ️')))
    return '\n'.join(lines)


def _panel_keyboard(lang: str) -> dict:
    return {'inline_keyboard': [
        [
            {'text': t('ip.btn_add', lang), 'callback_data': 'ip_addhelp'},
            {'text': t('ip.btn_del', lang), 'callback_data': 'ip_delmenu'},
        ],
        [
            {'text': t('ip.btn_detect', lang), 'url': MYIP_URL},
        ],
        [
            {'text': t('ip.btn_refresh', lang), 'callback_data': 'ip_menu'},
        ],
    ]}


def send_panel(tg_id: int, api: TelegramBotAPI, lang: str | None = None) -> None:
    lang = lang or resolve_lang(chat_id=tg_id)
    api.send_message(tg_id, _panel_text(lang), reply_markup=_panel_keyboard(lang))


def _confirm_add_prompt(
    tg_id: int, ip: str, api: TelegramBotAPI, *, label: str = '', lang: str = 'uz',
) -> None:
    token = encode_ip(ip)
    note = t('ip.note', lang, label=escape(label)) if label else ''
    api.send_message(
        tg_id,
        t('ip.confirm_add', lang, icon=ce('lock', '🛡'), ip=ip, note=note),
        reply_markup={'inline_keyboard': [[
            {'text': t('ip.btn_confirm_add', lang), 'callback_data': f'ipaok_{token}'},
            {'text': t('ip.btn_cancel', lang), 'callback_data': 'ip_menu'},
        ]]},
    )


def handle_ip_command(command: str, message: dict, api: TelegramBotAPI) -> bool:
    """/ip [add <ip> [label] | del <ip>] — owner check is done by the caller."""
    if command != '/ip':
        return False

    tg_from = message.get('from', {})
    tg_id = tg_from['id']
    lang = resolve_lang(tg_from)
    parts = message.get('text', '').split()
    sub = parts[1].lower() if len(parts) > 1 else ''

    if sub == 'add' and len(parts) > 2:
        ip = normalize_ip(parts[2])
        if not ip:
            api.send_message(
                tg_id,
                t('ip.invalid', lang, icon=ce('error', '❌'), raw=escape(parts[2][:40])),
            )
            return True
        _confirm_add_prompt(tg_id, ip, api, label=' '.join(parts[3:]), lang=lang)
    elif sub == 'del' and len(parts) > 2:
        ok, res = remove_ip(parts[2], by=tg_id)
        if ok:
            api.send_message(tg_id, t('ip.deleted', lang, icon=ce('success', '✅'), ip=res))
            send_panel(tg_id, api, lang)
        else:
            api.send_message(tg_id, f'{ce("error", "❌")} {_fail_text(res, lang)}')
    else:
        send_panel(tg_id, api, lang)
    return True


def handle_start_payload(payload: str, tg_from: dict, api: TelegramBotAPI) -> bool:
    """Deep link: t.me/<bot>?start=addip_<b64ip> (from the /myip/ page)."""
    if not payload.startswith('addip_'):
        return False
    tg_id = tg_from['id']
    lang = resolve_lang(tg_from)
    ip = decode_ip(payload[len('addip_'):])
    if not ip:
        api.send_message(tg_id, t('ip.link_bad', lang, icon=ce('error', '❌')))
        return True
    _confirm_add_prompt(tg_id, ip, api, lang=lang)
    return True


def maybe_offer_ip_add(message: dict, api: TelegramBotAPI) -> bool:
    """Owner pasted a bare IP in private chat → offer to allowlist it."""
    text = (message.get('text') or '').strip()
    if not text or len(text) > 45:
        return False
    ip = normalize_ip(text)
    if not ip:
        return False
    tg_from = message.get('from', {})
    _confirm_add_prompt(tg_from['id'], ip, api, lang=resolve_lang(tg_from))
    return True


def handle_ip_callback(data: str, callback_query: dict, api: TelegramBotAPI) -> bool:
    """Callback family: ip_menu / ip_addhelp / ip_delmenu / ipaok_ / ipd_ / ipdok_."""
    if not (data.startswith('ip_') or data.startswith('ipaok_')
            or data.startswith('ipd_') or data.startswith('ipdok_')):
        return False

    tg_from = callback_query.get('from', {})
    tg_id = tg_from['id']
    cb_id = callback_query['id']
    lang = resolve_lang(tg_from)

    from .handlers import is_owner  # local import — avoids a circular import
    if not is_owner(tg_id):
        api.answer_callback_query(cb_id, t('cb.owner_only', lang))
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
        _edit_or_send(_panel_text(lang), _panel_keyboard(lang))
        api.answer_callback_query(cb_id, t('cb.updated', lang))

    elif data == 'ip_addhelp':
        api.answer_callback_query(cb_id)
        api.send_message(
            chat_id,
            t('ip.addhelp', lang, icon=ce('scam_warn', 'ℹ️'), url=MYIP_URL),
        )

    elif data == 'ip_delmenu':
        entries = load_data()['ips']
        if not entries:
            api.answer_callback_query(cb_id, t('ip.delmenu_empty', lang))
            return True
        rows = [
            [{
                'text': f'🗑 {e["ip"]}' + (f' ({e["label"]})' if e.get('label') else ''),
                'callback_data': f'ipd_{encode_ip(e["ip"])}',
            }]
            for e in entries
        ]
        rows.append([{'text': t('ip.btn_back', lang), 'callback_data': 'ip_menu'}])
        api.answer_callback_query(cb_id)
        _edit_or_send(
            t('ip.delmenu_title', lang, icon=ce('ban', '🗑')),
            {'inline_keyboard': rows},
        )

    elif data.startswith('ipd_'):
        ip = decode_ip(data[len('ipd_'):])
        if not ip:
            api.answer_callback_query(cb_id, t('ip.toast_bad_ip', lang))
            return True
        api.answer_callback_query(cb_id)
        _edit_or_send(
            t('ip.confirm_del', lang, icon=ce('scam_warn', '⚠️'), ip=ip),
            {'inline_keyboard': [[
                {'text': t('ip.btn_confirm_del', lang),
                 'callback_data': f'ipdok_{data[len("ipd_"):]}'},
                {'text': t('ip.btn_cancel', lang), 'callback_data': 'ip_menu'},
            ]]},
        )

    elif data.startswith('ipdok_'):
        ip = decode_ip(data[len('ipdok_'):])
        ok, res = remove_ip(ip or '', by=tg_id)
        api.answer_callback_query(
            cb_id, t('ip.toast_deleted', lang) if ok else t('ip.toast_error', lang),
        )
        if ok:
            _edit_or_send(_panel_text(lang), _panel_keyboard(lang))
        else:
            api.send_message(chat_id, f'{ce("error", "❌")} {_fail_text(res, lang)}')

    elif data.startswith('ipaok_'):
        ip = decode_ip(data[len('ipaok_'):])
        ok, res = add_ip(ip or '', by=tg_id)
        api.answer_callback_query(
            cb_id, t('ip.toast_added', lang) if ok else t('ip.toast_error', lang),
        )
        if ok:
            api.send_message(
                chat_id, t('ip.added', lang, icon=ce('success', '✅'), ip=res),
            )
            send_panel(chat_id, api, lang)
        else:
            api.send_message(chat_id, f'{ce("error", "❌")} {_fail_text(res, lang)}')

    return True
