"""
Telegram Channel Share Service.

Publishes blog posts and projects to a configured Telegram channel
with rich inline keyboard buttons. Each content object may only be
shared once per channel; changing the channel ID in SiteSettings
allows re-sharing.
"""
from __future__ import annotations

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

        if not post.featured_image:
            return False, 'Postda rasm (featured_image) yo\'q.'

        # ── Optimistic lock: insert DB record FIRST to prevent duplicates ──
        ct = ContentType.objects.get_for_model(post)
        share_record = self._claim_share(ct, post.pk, channel_id, user)
        if share_record is None:
            return False, 'Bu post allaqachon ushbu kanalga yuborilgan.'

        caption = self._build_post_caption(post)
        keyboard = self._build_post_keyboard(post)
        reply_markup = {'inline_keyboard': keyboard}

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
            # Telegram failed — remove the optimistic DB record
            share_record.delete()
            error = result.get('description', 'Unknown error') if result else 'No response'
            return False, f'Telegram API xatosi: {error}'

        # Update record with Telegram message_id
        msg_id = result.get('result', {}).get('message_id')
        if msg_id:
            share_record.telegram_message_id = msg_id
            share_record.save(update_fields=['telegram_message_id'])

        return True, 'Post kanalga muvaffaqiyatli yuborildi!'

    def share_project(self, project, user=None) -> Tuple[bool, str]:
        """Share a Project to the Telegram channel."""
        channel_id = self._get_channel_id()
        if not channel_id:
            return False, 'Telegram kanal ID sozlanmagan.'

        # ── Optimistic lock: insert DB record FIRST to prevent duplicates ──
        ct = ContentType.objects.get_for_model(project)
        share_record = self._claim_share(ct, project.pk, channel_id, user)
        if share_record is None:
            return False, 'Bu project allaqachon ushbu kanalga yuborilgan.'

        caption = self._build_project_caption(project)
        keyboard = self._build_project_keyboard(project)
        reply_markup = {'inline_keyboard': keyboard}

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
            # Telegram failed — remove the optimistic DB record
            share_record.delete()
            error = result.get('description', 'Unknown error') if result else 'No response'
            return False, f'Telegram API xatosi: {error}'

        # Update record with Telegram message_id
        msg_id = result.get('result', {}).get('message_id')
        if msg_id:
            share_record.telegram_message_id = msg_id
            share_record.save(update_fields=['telegram_message_id'])

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
            # Calculate safe excerpt length
            title_line = f'📝 <b>{title}</b>'
            overhead = len(title_line) + 2  # +2 for two newlines
            if tags:
                overhead += len(tags) + 2  # +2 for two newlines before tags
            overhead += 3  # for "..."
            max_excerpt = max(1024 - overhead, 0)
            parts = [title_line, '', excerpt[:max_excerpt] + '...']
            if tags:
                parts.extend(['', tags])
            caption = '\n'.join(parts)

        return caption[:1024]

    def _build_project_caption(self, project) -> str:
        """Build HTML caption for a project (max 1024 chars)."""
        title = escape(project.title)
        raw_desc = project.short_description or project.get_card_description()[:200]
        desc = escape(raw_desc) if raw_desc else ''

        # Tech stack
        techs = ''
        try:
            tech_names = list(project.technologies.values_list('name', flat=True)[:8])
            if tech_names:
                techs = '🛠 ' + ' · '.join(escape(t) for t in tech_names)
        except Exception:
            pass

        lines = [f'📱 <b>{title}</b>']
        if desc:
            lines.extend(['', desc])
        if techs:
            lines.extend(['', techs])

        caption = '\n'.join(lines)

        # Truncation: trim desc to fit within 1024 chars
        if len(caption) > 1024 and desc:
            title_line = f'📱 <b>{title}</b>'
            overhead = len(title_line) + 2  # +2 for newlines before desc
            if techs:
                overhead += len(techs) + 2
            overhead += 3  # for "..."
            max_desc = max(1024 - overhead, 0)
            desc_truncated = escape(raw_desc[:max_desc]) + '...'
            parts = [title_line, '', desc_truncated]
            if techs:
                parts.extend(['', techs])
            caption = '\n'.join(parts)

        return caption[:1024]

    # ── Keyboard builders ─────────────────────────────────────────────────────

    def _build_post_keyboard(self, post) -> list:
        """Build inline keyboard for a blog post (Mini App deep link)."""
        detail_url = self._detail_deep_link(post)
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
            })
        if project.app_store_url:
            store_row.append({
                'text': '🍎 App Store',
                'url': project.app_store_url,
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
        # Bot projects: web_page_url is likely the bot link itself,
        # so only add a generic bot link if there is no web_page_url
        if project.is_bot and not project.web_page_url:
            bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', '')
            if bot_username:
                extra_row.append({
                    'text': '🤖 Telegram Bot',
                    'url': f'https://t.me/{bot_username}',
                })
        if extra_row:
            rows.append(extra_row)

        # Detail button (always present — Mini App deep link)
        detail_url = self._detail_deep_link(project)
        rows.append([{'text': '📖 Batafsil', 'url': detail_url}])

        return rows

    # ── Deep link helpers ─────────────────────────────────────────────────────

    def _detail_deep_link(self, obj) -> str:
        """Build Mini App deep link for a content object.

        Format: https://t.me/{bot}/{app}?startapp={post-slug|proj-slug}
        Falls back to regular website URL if bot/app settings are missing.
        """
        startapp = self._content_startapp(obj)
        deep_url = self._tg_deep_link(startapp) if startapp else ''
        if deep_url:
            return deep_url
        # Fallback to regular website URL
        return f'{self._domain}{obj.get_absolute_url()}'

    @staticmethod
    def _tg_deep_link(startapp: str) -> str:
        """Build t.me Mini App deep link URL."""
        bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', '')
        app_name = getattr(settings, 'TELEGRAM_WEBAPP_SHORT_NAME', '')
        if bot_username and app_name:
            return f'https://t.me/{bot_username}/{app_name}?startapp={startapp}'
        return ''

    @staticmethod
    def _content_startapp(obj) -> str:
        """Build startapp parameter for a content object (Post/Project)."""
        model = obj.__class__.__name__.lower()
        slug = getattr(obj, 'slug', '')
        if model == 'post' and slug:
            return f'post-{slug}'
        if model == 'project' and slug:
            return f'proj-{slug}'
        return ''

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _get_channel_id() -> Optional[int]:
        site = SiteSettingsService.get()
        return getattr(site, 'telegram_channel_id', None)

    @property
    def _domain(self) -> str:
        domain = getattr(settings, 'TELEGRAM_WEBHOOK_DOMAIN', DEFAULT_DOMAIN)
        return domain.rstrip('/')

    @staticmethod
    def _claim_share(ct, object_id: int, channel_id: int, user):
        """Attempt to claim a share slot (optimistic lock).

        Creates the ChannelShare record BEFORE calling the Telegram API.
        Returns the record on success, None if already shared (IntegrityError).
        The caller must delete the record if the Telegram call fails.
        """
        from interactions.models import ChannelShare
        try:
            return ChannelShare.objects.create(
                content_type=ct,
                object_id=object_id,
                channel_id=channel_id,
                shared_by=user,
            )
        except IntegrityError:
            logger.warning(
                'Duplicate share attempt: %s #%s → channel %s',
                ct, object_id, channel_id,
            )
            return None
