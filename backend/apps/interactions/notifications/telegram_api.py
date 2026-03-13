"""
Low-level Telegram Bot API client.

Synchronous (httpx), designed to be called from daemon threads.
All exceptions are caught and logged — notification failure never crashes a request.
"""
from __future__ import annotations

import logging
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
        """POST /sendPhoto.  *photo* is a URL string."""
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
