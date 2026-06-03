"""
High-level notification dispatcher.

Every public method accepts Django model instances, builds formatted
Telegram messages, checks user preferences, and delegates to
TelegramBotAPI.  All outbound calls run in daemon threads so the
caller (Django view / signal handler) is never blocked.
"""
from __future__ import annotations

import logging
import threading
from html import escape
from typing import Optional

from core.emoji import ce
from core.services import SiteSettingsService
from django.conf import settings

from .telegram_api import TelegramBotAPI

logger = logging.getLogger('interactions.notifications')

DEFAULT_DOMAIN = 'https://jaysonkhan.com'


# ── Thread helper ────────────────────────────────────────────────────────────

def fire_and_forget(fn, *args, **kwargs):
    """Run *fn* in a daemon thread.  Exceptions are logged, never raised."""
    def _wrapper():
        try:
            fn(*args, **kwargs)
        except Exception as exc:
            logger.error('Notification thread error: %s', exc, exc_info=True)
    threading.Thread(target=_wrapper, daemon=True).start()


# ── Service ──────────────────────────────────────────────────────────────────

class NotificationService:
    """Orchestrates user DMs and admin-group logging."""

    def __init__(self):
        self.api = TelegramBotAPI()

    # ── User notifications ───────────────────────────────────────────────────

    def notify_reply(self, comment) -> None:
        """Notify the parent-comment author that someone replied."""
        if not comment.author:
            return
        parent = comment.parent
        if not parent or not parent.author:
            return
        if comment.author_id == parent.author_id:
            return
        recipient = parent.author
        site = SiteSettingsService.get()
        if not self._should_notify(recipient, 'replies_enabled', site=site):
            return

        replier = escape(comment.author.display_name)
        snippet = escape(comment.text[:200]) if comment.text else ''

        text = (
            f'{ce("reply", "↩️")} <b>{replier}</b> sizning kommentingizga javob yozdi:\n\n'
            f'"{snippet}"'
        )
        fallback_url = f'{self._domain}{self._content_url(comment)}#comment-{comment.id}'
        reply_markup = self._deep_link_button(
            'Javob berish', f'c-{comment.id}', fallback_url, site=site,
        )
        self.api.send_message(
            recipient.telegram_id, text, reply_markup=reply_markup,
        )

    def notify_reaction(self, reaction, action: str) -> None:
        """
        Notify comment author about a reaction change.
        *action*: ``'added'`` or ``'removed'``.
        """
        comment = reaction.comment
        if not comment or not comment.author or not reaction.author:
            return
        if reaction.author_id == comment.author_id:
            return
        recipient = comment.author
        site = SiteSettingsService.get()
        if not self._should_notify(recipient, 'reactions_enabled', site=site):
            return

        reactor = escape(reaction.author.display_name)
        sign = '+1' if action == 'added' else '-1'
        text = f'{sign} {reaction.emoji} — <b>{reactor}</b>'
        self.api.send_message(recipient.telegram_id, text)

    # ── Admin group logging ──────────────────────────────────────────────────

    def log_new_comment(self, comment) -> None:
        site = SiteSettingsService.get()
        if not getattr(site, 'admin_notify_comments', True):
            return
        if not comment.author:
            return
        author = escape(comment.author.display_name)
        snippet = escape(comment.text[:200]) if comment.text else ''
        text = f'{ce("comment", "💬")} <b>{author}</b> komment yozdi:\n{snippet}' if snippet else f'{ce("comment", "💬")} <b>{author}</b> komment yozdi:'
        fallback_url = f'{self._full_url(comment)}#comment-{comment.id}'
        button = self._deep_link_button(
            'Kommentni ko\'rish', f'c-{comment.id}', fallback_url, site=site,
        )
        photo_url = self._comment_image_url(comment)
        self._send_to_admin_group(
            text, comment.author, 'comment',
            reply_markup=button, photo_url=photo_url, site=site,
        )

    def log_reply(self, comment) -> None:
        site = SiteSettingsService.get()
        if not getattr(site, 'admin_notify_replies', True):
            return
        parent = comment.parent
        if not parent or not parent.author:
            return
        author = escape(comment.author.display_name)
        parent_author = escape(parent.author.display_name)
        snippet = escape(comment.text[:200]) if comment.text else ''
        text = f'{ce("reply", "↩️")} <b>{author}</b> → <b>{parent_author}</b>:\n{snippet}' if snippet else f'{ce("reply", "↩️")} <b>{author}</b> → <b>{parent_author}</b>'
        fallback_url = f'{self._full_url(comment)}#comment-{comment.id}'
        button = self._deep_link_button(
            'Javobni ko\'rish', f'c-{comment.id}', fallback_url, site=site,
        )
        photo_url = self._comment_image_url(comment)
        self._send_to_admin_group(
            text, comment.author, 'reply',
            reply_markup=button, photo_url=photo_url, site=site,
        )

    def log_reaction(self, reaction, action: str) -> None:
        site = SiteSettingsService.get()
        if not getattr(site, 'admin_notify_reactions', True):
            return
        actor = escape(reaction.author.display_name)
        comment_author = escape(reaction.comment.author.display_name)
        verb = 'reacted' if action == 'added' else 'removed'
        text = f'{reaction.emoji} <b>{actor}</b> {verb} on <b>{comment_author}</b>\'s comment'
        comment = reaction.comment
        fallback_url = self._comment_anchor_url(comment)
        button = self._deep_link_button(
            'Kommentni ko\'rish', f'c-{comment.id}', fallback_url, site=site,
        )
        self._send_to_admin_group(text, reaction.author, 'reaction', reply_markup=button, site=site)

    def log_like(self, like, action: str) -> None:
        site = SiteSettingsService.get()
        if not getattr(site, 'admin_notify_likes', True):
            return
        obj = like.content_object
        if not obj:
            return
        actor = escape(like.author.display_name)
        title = self._content_title(obj)
        emoji = ce('like', '👍') if action == 'liked' else ce('unlike', '👎')
        text = f'{emoji} <b>{actor}</b> {action} <b>{escape(title)}</b>'
        startapp = self._content_startapp(obj)
        fallback_url = ''
        if hasattr(obj, 'get_absolute_url'):
            fallback_url = f'{self._domain}{obj.get_absolute_url()}'
        button = self._deep_link_button(
            'Ko\'rish', startapp, fallback_url, site=site,
        ) if (startapp or fallback_url) else None
        self._send_to_admin_group(text, like.author, 'like', reply_markup=button, site=site)

    def log_new_user(self, profile) -> None:
        site = SiteSettingsService.get()
        if not getattr(site, 'admin_notify_new_users', True):
            return

        # ── Entity type ───────────────────────────────────────────────────
        type_map = {
            'user': (ce('user', '👤'), 'Foydalanuvchi'),
            'bot': (ce('bot', '🤖'), 'Bot'),
            'group': (ce('group', '👥'), 'Guruh'),
            'supergroup': (ce('group', '👥'), 'Superguruh'),
            'channel': (ce('channel_icon', '📢'), 'Kanal'),
        }
        emoji, type_label = type_map.get(profile.entity_type, (ce('user', '👤'), 'Noma\'lum'))

        # ── Servis manbalarini erta so'rash (yangi vs qaytgan user uchun) ──
        svc_labels = {
            'site': f'{ce("web", "🌐")} Sayt (Login)',
        }
        svc_action_labels = {
            'site': f'{ce("web", "🌐")} Saytga kirdi',
        }
        try:
            from telegram.models import EntitySource
            sources = list(
                EntitySource.objects.filter(entity=profile)
                .order_by('-updated_at')
                .values_list('service', flat=True)
            )
        except Exception:
            sources = []
        is_returning = len(sources) > 1

        name = escape(profile.display_name)

        if is_returning:
            # Qaytgan user — yangi servisdan kirdi (sources ordered by -updated_at)
            new_service = sources[0] if sources else ''
            action = svc_action_labels.get(new_service, f'{new_service} dan topildi')
            lines = [f'{ce("returning", "🔄")} <b>{name}</b> — {action}']
        else:
            lines = [f'{emoji} <b>Yangi {type_label.lower()}: {name}</b>']

        # ── Asosiy ma'lumotlar ────────────────────────────────────────────
        username = profile.username
        info_parts = [f'{ce("id_badge", "🆔")} <code>{profile.telegram_id}</code>']
        if username:
            info_parts.append(f'@{escape(username)}')
        lines.append(' · '.join(info_parts))

        phone = profile.phone
        if phone:
            lines.append(f'{ce("phone", "📱")} <code>{escape(phone)}</code>')

        # ── Qaysi servislar orqali topilgan ──────────────────────────────
        if sources:
            src_str = ', '.join(svc_labels.get(s, s) for s in sources)
            lines.append(f'{ce("sources", "📡")} {src_str}')

        # ── Badgelar ──────────────────────────────────────────────────────
        badges = []
        if getattr(profile, 'is_premium', False):
            badges.append(f'{ce("premium", "⭐️")} Premium')
        if getattr(profile, 'is_verified', False):
            badges.append(f'{ce("verified", "✅")} Tasdiqlangan')
        if getattr(profile, 'is_scam', False):
            badges.append(f'{ce("scam_warn", "⚠️")} SCAM')
        if getattr(profile, 'is_fake', False):
            badges.append(f'{ce("ban", "🚫")} FAKE')
        if badges:
            lines.append(' · '.join(badges))

        # ── Bio ───────────────────────────────────────────────────────────
        bio = getattr(profile, 'bio', '')
        if bio:
            lines.append(f'💬 <i>{escape(str(bio)[:120])}</i>')

        text = '\n'.join(lines)

        # ── Tugmalar ──────────────────────────────────────────────────────
        buttons = [
            [
                {'text': '⚙️ Admin', 'url': self._admin_entity_url(profile)},
                {'text': '🌐 Sayt', 'url': self._domain},
            ]
        ]

        reply_markup = {'inline_keyboard': buttons}
        photo_url = profile.get_photo_url() or None
        self._send_to_admin_group(
            text, profile, 'new_user',
            reply_markup=reply_markup, photo_url=photo_url, site=site,
        )

    def log_contact_message(self, contact) -> None:
        site = SiteSettingsService.get()
        if not getattr(site, 'admin_notify_contacts', True):
            return
        name = escape(contact.name or '')
        email = escape(contact.email or '')
        subject = escape(contact.subject or '')
        body = escape((contact.message or '')[:300])
        text = (
            f'{ce("contact_msg", "📩")} Yangi xabar:\n'
            f'<b>From:</b> {name} ({email})\n'
            f'<b>Subject:</b> {subject}\n'
            f'<b>Message:</b> {body}'
        )
        try:
            from django.urls import reverse
            path = reverse('admin:contact_contactmessage_changelist')
            admin_url = f'{self._domain}{path}'
        except Exception:
            admin_prefix = getattr(settings, 'ADMIN_URL_PREFIX', 'admin/').rstrip('/') + '/'
            admin_url = f'{self._domain}/{admin_prefix}contact/contactmessage/'
        button = {'inline_keyboard': [[{'text': 'Admin panelda ko\'rish', 'url': admin_url}]]}
        self._send_to_admin_group(text, profile=None, event_type='contact', reply_markup=button, site=site)

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _admin_enabled(field_name: str) -> bool:
        """Check whether the admin-group toggle *field_name* is on."""
        site = SiteSettingsService.get()
        return getattr(site, field_name, True)

    @property
    def _domain(self) -> str:
        return getattr(settings, 'TELEGRAM_WEBHOOK_DOMAIN', DEFAULT_DOMAIN)

    def _admin_entity_url(self, profile) -> str:
        """Admin change page URL for a TelegramEntity."""
        try:
            from django.urls import reverse
            path = reverse(
                'admin:telegram_telegramentity_change',
                args=[profile.pk],
            )
            return f'{self._domain}{path}'
        except Exception:
            return self._domain

    def _tg_deep_link(self, startapp: str) -> str:
        """Build t.me Mini App deep link.

        Format: https://t.me/{bot_username}/{app_name}?startapp={param}
        Telegram bu linkni Mini App sifatida ochadi (in-app browser).
        """
        bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', '')
        app_name = getattr(settings, 'TELEGRAM_WEBAPP_SHORT_NAME', '')
        if bot_username and app_name:
            return f'https://t.me/{bot_username}/{app_name}?startapp={startapp}'
        return ''

    def _send_to_admin_group(
        self,
        text: str,
        profile=None,
        event_type: str = '',
        reply_markup: Optional[dict] = None,
        photo_url: Optional[str] = None,
        site=None,
    ) -> Optional[int]:
        """Send message to admin group.  Saves AdminLogMessage for /ban lookup."""
        from interactions.models import AdminLogMessage

        if site is None:
            site = SiteSettingsService.get()
        group_id = site.telegram_admin_group_id
        if not group_id:
            return None

        result = None
        if photo_url:
            result = self.api.send_photo(
                group_id, photo_url,
                caption=text, reply_markup=reply_markup,
            )
        if not result or not result.get('ok'):
            # Fallback to plain text (handles expired photo URLs, caption > 1024 chars, etc.)
            if photo_url:
                logger.info('send_photo failed, falling back to send_message')
            result = self.api.send_message(group_id, text, reply_markup=reply_markup)

        msg_data = result.get('result') if result else None
        if result and result.get('ok') and msg_data:
            msg_id = msg_data.get('message_id')
            if not msg_id:
                return None
            AdminLogMessage.objects.create(
                message_id=msg_id,
                profile=profile,
                event_type=event_type,
            )
            return msg_id
        return None

    def _should_notify(self, profile, pref_field: str, site=None) -> bool:
        """
        Check if *profile* should receive the given notification type.
        Site owner always receives, regardless of preferences.
        """
        from interactions.models import NotificationPreference

        if self._is_site_owner(profile, site=site):
            return True
        pref, _ = NotificationPreference.objects.get_or_create(profile=profile)
        return getattr(pref, pref_field, True)

    def _is_site_owner(self, profile, site=None) -> bool:
        if site is None:
            site = SiteSettingsService.get()
        owner_id = site.telegram_owner_id
        return bool(owner_id and profile.telegram_id == owner_id)

    def _comment_image_url(self, comment) -> Optional[str]:
        """Return absolute URL for the comment image, or None."""
        if not comment.image:
            return None
        return f'{self._domain}{comment.image.url}'

    def _deep_link_button(self, label: str, startapp: str, fallback_url: str = '', site=None) -> dict:
        """Build inline keyboard with Mini App deep link button.

        Button text should NOT contain emoji — icon_custom_emoji_id handles that.
        """
        deep_url = self._tg_deep_link(startapp) if startapp else ''
        url = deep_url or fallback_url or self._domain
        btn = {'text': label, 'url': url}
        # Add custom emoji icon for the button
        if site is None:
            site = SiteSettingsService.get()
        emoji_id = getattr(site, 'tg_emoji_comment', '') or ''
        if emoji_id:
            btn['icon_custom_emoji_id'] = emoji_id
        return {'inline_keyboard': [[btn]]}

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

    @staticmethod
    def _content_url(comment) -> str:
        """Resolve relative URL for the content object a comment is attached to."""
        obj = comment.content_object
        if hasattr(obj, 'get_absolute_url'):
            return obj.get_absolute_url()
        return '/'

    def _full_url(self, comment) -> str:
        """Full absolute URL for the content a comment belongs to."""
        return f'{self._domain}{self._content_url(comment)}'

    def _comment_anchor_url(self, comment) -> str:
        """Full URL pointing directly to a specific comment."""
        return f'{self._full_url(comment)}#comment-{comment.id}'

    @staticmethod
    def _content_title(content_object) -> str:
        return getattr(content_object, 'title', str(content_object))
