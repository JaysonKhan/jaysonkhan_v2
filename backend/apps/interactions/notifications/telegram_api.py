"""
Low-level Telegram Bot API client.

Synchronous (httpx), designed to be called from daemon threads.
All exceptions are caught and logged — notification failure never crashes a request.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

import httpx
from django.conf import settings

logger = logging.getLogger('interactions.notifications')


class TelegramBotAPI:
    """Thin wrapper around the Telegram Bot HTTP API."""

    def __init__(self, token: Optional[str] = None):
        self._token = token or getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        self._base = f'https://api.telegram.org/bot{self._token}'
        self._client = httpx.Client(timeout=10.0)

    # ── Public methods ───────────────────────────────────────────────────────

    def send_message(
        self,
        chat_id: int,
        text: str,
        *,
        parse_mode: str = 'HTML',
        reply_markup: Optional[dict] = None,
        disable_web_page_preview: bool = True,
    ) -> Optional[dict]:
        """POST /sendMessage. Returns full API response dict or None."""
        payload: dict = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': disable_web_page_preview,
        }
        if reply_markup:
            payload['reply_markup'] = reply_markup
        return self._post('sendMessage', payload)

    def send_photo(
        self,
        chat_id: int,
        photo: str,
        *,
        caption: str = '',
        parse_mode: str = 'HTML',
        reply_markup: Optional[dict] = None,
    ) -> Optional[dict]:
        """POST /sendPhoto. *photo* can be:
          - HTTPS URL string  → Telegram fetches it
          - Local file path   → uploaded as multipart (recommended)

        URL fetch often fails with non-ASCII filenames, HTTP/2-only
        servers, or >5MB images served with strict headers — Telegram
        returns `400 wrong type of the web page content`. Direct
        multipart upload bypasses the fetcher entirely.
        """
        is_url = photo.startswith(('http://', 'https://'))
        if not is_url and os.path.isfile(photo):
            return self._send_photo_multipart(
                chat_id, photo,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
        payload: dict = {
            'chat_id': chat_id,
            'photo': photo,
            'parse_mode': parse_mode,
        }
        if caption:
            payload['caption'] = caption
        if reply_markup:
            payload['reply_markup'] = reply_markup
        return self._post('sendPhoto', payload)

    def _send_photo_multipart(
        self,
        chat_id: int,
        photo_path: str,
        *,
        caption: str = '',
        parse_mode: str = 'HTML',
        reply_markup: Optional[dict] = None,
    ) -> Optional[dict]:
        """Multipart /sendPhoto upload — sidesteps URL-fetch brittleness.

        httpx's `files=` parameter builds the multipart body automatically;
        `data=` for text fields carries chat_id / caption / reply_markup.
        Complex fields (reply_markup dict) must be JSON-encoded — Telegram
        rejects raw Python repr.
        """
        if not self._token:
            logger.warning('TELEGRAM_BOT_TOKEN not configured — skipping sendPhoto')
            return None
        url = f'{self._base}/sendPhoto'
        data = {
            'chat_id': str(chat_id),
            'parse_mode': parse_mode,
        }
        if caption:
            data['caption'] = caption
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        try:
            with open(photo_path, 'rb') as fh:
                filename = os.path.basename(photo_path) or 'photo.png'
                # Force ASCII-safe filename; some Telegram MIME parsers choke
                # on non-ASCII in multipart Content-Disposition. The name
                # inside the upload doesn't matter for display anyway.
                safe_name = filename.encode('ascii', errors='replace').decode('ascii')
                files = {'photo': (safe_name, fh, 'application/octet-stream')}
                # 60s timeout — large photos over slow network need room.
                resp = self._client.post(url, data=data, files=files, timeout=60.0)
            result = resp.json()
            if not result.get('ok'):
                logger.warning(
                    'Telegram sendPhoto (multipart) error: %s',
                    result.get('description', result),
                )
            return result
        except FileNotFoundError:
            logger.error('sendPhoto multipart: file not found: %s', photo_path)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error('sendPhoto multipart failed: %s', exc)
            return None

    def answer_callback_query(
        self,
        callback_query_id: str,
        text: str = '',
    ) -> Optional[dict]:
        payload = {'callback_query_id': callback_query_id}
        if text:
            payload['text'] = text
        return self._post('answerCallbackQuery', payload)

    def edit_message_reply_markup(
        self,
        chat_id: int,
        message_id: int,
        reply_markup: dict,
    ) -> Optional[dict]:
        return self._post('editMessageReplyMarkup', {
            'chat_id': chat_id,
            'message_id': message_id,
            'reply_markup': reply_markup,
        })

    def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        *,
        parse_mode: str = 'HTML',
        reply_markup: Optional[dict] = None,
    ) -> Optional[dict]:
        payload: dict = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': parse_mode,
        }
        if reply_markup:
            payload['reply_markup'] = reply_markup
        return self._post('editMessageText', payload)

    def send_chat_action(self, chat_id: int, action: str = 'typing') -> Optional[dict]:
        """POST /sendChatAction. Shows typing/uploading indicator."""
        return self._post('sendChatAction', {
            'chat_id': chat_id,
            'action': action,
        })

    def set_webhook(self, url: str, *, secret_token: Optional[str] = None) -> Optional[dict]:
        payload: dict = {'url': url}
        if secret_token:
            payload['secret_token'] = secret_token
        return self._post('setWebhook', payload)

    def delete_webhook(self) -> Optional[dict]:
        return self._post('deleteWebhook', {})

    # ── Internal ─────────────────────────────────────────────────────────────

    def _post(self, method: str, data: dict) -> Optional[dict]:
        """POST to Bot API endpoint. Logs errors, never raises."""
        if not self._token:
            logger.warning('TELEGRAM_BOT_TOKEN not configured — skipping %s', method)
            return None
        try:
            resp = self._client.post(f'{self._base}/{method}', json=data)
            result = resp.json()
            if not result.get('ok'):
                logger.warning(
                    'Telegram API %s error: %s',
                    method, result.get('description', result),
                )
            return result
        except Exception as exc:
            logger.error('Telegram API %s failed: %s', method, exc)
            return None
