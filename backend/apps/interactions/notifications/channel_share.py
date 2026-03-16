"""
Telegram Channel Share Service.

Publishes blog posts and projects to a configured Telegram channel
with rich inline keyboard buttons. Each content object may only be
shared once per channel; changing the channel ID in SiteSettings
allows re-sharing.
"""
from __future__ import annotations

import json
import logging
from html import escape
from typing import Optional, Tuple

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError

from core.services import SiteSettingsService
from .telegram_api import TelegramBotAPI

logger = logging.getLogger('interactions.notifications')

DEFAULT_DOMAIN = 'https://jaysonkhan.com'


class ChannelShareService:
    """Publishes Post / Project to the configured Telegram channel."""

    def __init__(self):
        self.api = TelegramBotAPI()

    # ── Public API ────────────────────────────────────────────────────────────

    def get_share_info(self, obj) -> Optional[dict]:
        """
        Return share state for *obj* relative to the currently configured
        channel.  Returns ``None`` if no channel is configured.
        """
        channel_id = self._get_channel_id()
        if not channel_id:
            return None

        from interactions.models import ChannelShare
        ct = ContentType.objects.get_for_model(obj)
        share = (
            ChannelShare.objects
            .filter(content_type=ct, object_id=obj.pk, channel_id=channel_id)
            .first()
        )
        return {
            'shared': share is not None,
            'shared_at': share.shared_at if share else None,
            'channel_id': channel_id,
        }

    def share_post(self, post, user=None) -> Tuple[bool, str]:
        """Share a blog Post to the Telegram channel."""
        channel_id = self._get_channel_id()
        if not channel_id:
            return False, 'Telegram kanal ID sozlanmagan.'

        if self._is_shared(post, channel_id):
            return False, 'Bu post allaqachon ushbu kanalga yuborilgan.'

        if not post.featured_image:
            return False, 'Postda rasm (featured_image) yo\'q.'

        caption = self._build_post_caption(post)
        keyboard = self._build_post_keyboard(post)
        reply_markup = json.dumps({'inline_keyboard': keyboard})

        photo_url = f'{self._domain}{post.featured_image.url}'
        result = self.api.send_photo(
            channel_id, photo_url,
            caption=caption,
            reply_markup=reply_markup,
        )

        # Fallback to message if photo fails
        if not result or not result.get('ok'):
            logger.info('send_photo to channel failed, trying send_message')
            result = self.api.send_message(
                channel_id, caption,
                reply_markup=reply_markup,
                disable_web_page_preview=False,
            )

        if not result or not result.get('ok'):
            error = result.get('description', 'Unknown error') if result else 'No response'
            return False, f'Telegram API xatosi: {error}'

        msg_id = result.get('result', {}).get('message_id')
        self._record_share(post, channel_id, msg_id, user)
        return True, 'Post kanalga muvaffaqiyatli yuborildi!'

    def share_project(self, project, user=None) -> Tuple[bool, str]:
        """Share a Project to the Telegram channel."""
        channel_id = self._get_channel_id()
        if not channel_id:
            return False, 'Telegram kanal ID sozlanmagan.'

        if self._is_shared(project, channel_id):
            return False, 'Bu project allaqachon ushbu kanalga yuborilgan.'

        caption = self._build_project_caption(project)
        keyboard = self._build_project_keyboard(project)
        reply_markup = json.dumps({'inline_keyboard': keyboard})

        # Try photo first
        result = None
        if project.image:
            photo_url = f'{self._domain}{project.image.url}'
            result = self.api.send_photo(
                channel_id, photo_url,
                caption=caption,
                reply_markup=reply_markup,
            )

        if not result or not result.get('ok'):
            if project.image:
                logger.info('send_photo to channel failed, trying send_message')
            result = self.api.send_message(
                channel_id, caption,
                reply_markup=reply_markup,
                disable_web_page_preview=False,
            )

        if not result or not result.get('ok'):
            error = result.get('description', 'Unknown error') if result else 'No response'
            return False, f'Telegram API xatosi: {error}'

        msg_id = result.get('result', {}).get('message_id')
        self._record_share(project, channel_id, msg_id, user)
        return True, 'Project kanalga muvaffaqiyatli yuborildi!'

    # ── Caption builders ──────────────────────────────────────────────────────

    def _build_post_caption(self, post) -> str:
        """Build HTML caption for a blog post (max 1024 chars)."""
        title = escape(post.title)
        excerpt = escape(post.excerpt or '')

        # Hashtags from tags
        tags = ''
        try:
            tag_names = list(post.tags.values_list('name', flat=True))
            if tag_names:
                tags = ' '.join(f'#{escape(t.replace(" ", "_"))}' for t in tag_names)
        except Exception:
            pass

        lines = [
            f'📝 <b>{title}</b>',
            '',
            excerpt,
        ]
        if tags:
            lines.extend(['', tags])

        caption = '\n'.join(lines)

        # Telegram caption limit = 1024 chars
        if len(caption) > 1024:
            # Truncate excerpt to fit
            overhead = len(caption) - len(excerpt)
            max_excerpt = 1024 - overhead - 3  # for "..."
            caption = '\n'.join([
                f'📝 <b>{title}</b>',
                '',
                excerpt[:max_excerpt] + '...',
                *([f'\n{tags}'] if tags else []),
            ])

        return caption[:1024]

    def _build_project_caption(self, project) -> str:
        """Build HTML caption for a project (max 1024 chars)."""
        title = escape(project.title)
        desc = escape(project.short_description or project.get_card_description()[:200])

        # Tech stack
        techs = ''
        try:
            tech_names = list(project.technologies.values_list('name', flat=True)[:8])
            if tech_names:
                techs = '🛠 ' + ' · '.join(escape(t) for t in tech_names)
        except Exception:
            pass

        lines = [
            f'📱 <b>{title}</b>',
            '',
            desc,
        ]
        if techs:
            lines.extend(['', techs])

        caption = '\n'.join(lines)
        return caption[:1024]

    # ── Keyboard builders ─────────────────────────────────────────────────────

    def _build_post_keyboard(self, post) -> list:
        """Build inline keyboard for a blog post."""
        detail_url = f'{self._domain}{post.get_absolute_url()}'
        return [
            [{'text': '📖 Batafsil', 'url': detail_url}],
        ]

    def _build_project_keyboard(self, project) -> list:
        """Build inline keyboard for a project with store links."""
        rows = []

        # Store buttons (same row if both exist)
        store_row = []
        if project.play_store_url:
            store_row.append({
                'text': '▶️ Google Play',
                'url': project.play_store_url,
                'style': 'success',
            })
        if project.app_store_url:
            store_row.append({
                'text': '🍎 App Store',
                'url': project.app_store_url,
                'style': 'primary',
            })
        if store_row:
            rows.append(store_row)

        # Additional links row
        extra_row = []
        if project.web_page_url:
            extra_row.append({
                'text': '🌐 Web',
                'url': project.web_page_url,
            })
        if project.is_bot and project.web_page_url:
            # If is_bot, web_page_url is likely the bot link
            pass
        elif project.is_bot:
            bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', '')
            if bot_username:
                extra_row.append({
                    'text': '🤖 Telegram Bot',
                    'url': f'https://t.me/{bot_username}',
                })
        if extra_row:
            rows.append(extra_row)

        # Detail button (always present)
        detail_url = f'{self._domain}{project.get_absolute_url()}'
        rows.append([{'text': '📖 Batafsil', 'url': detail_url}])

        return rows

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _get_channel_id() -> Optional[int]:
        site = SiteSettingsService.get()
        return getattr(site, 'telegram_channel_id', None)

    @staticmethod
    def _is_shared(obj, channel_id: int) -> bool:
        from interactions.models import ChannelShare
        ct = ContentType.objects.get_for_model(obj)
        return ChannelShare.objects.filter(
            content_type=ct, object_id=obj.pk, channel_id=channel_id,
        ).exists()

    @property
    def _domain(self) -> str:
        return getattr(settings, 'TELEGRAM_WEBHOOK_DOMAIN', DEFAULT_DOMAIN)

    @staticmethod
    def _record_share(obj, channel_id: int, message_id, user):
        from interactions.models import ChannelShare
        ct = ContentType.objects.get_for_model(obj)
        try:
            ChannelShare.objects.create(
                content_type=ct,
                object_id=obj.pk,
                channel_id=channel_id,
                telegram_message_id=message_id,
                shared_by=user,
            )
        except IntegrityError:
            logger.warning(
                'Duplicate share attempt: %s #%s → channel %s',
                ct, obj.pk, channel_id,
            )
