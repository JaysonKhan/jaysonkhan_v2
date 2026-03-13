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

from django.conf import settings

from core.services import SiteSettingsService
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
        parent = comment.parent
        if not parent or not parent.author:
            return
        if comment.author_id == parent.author_id:
            return
        recipient = parent.author
        if not self._should_notify(recipient, 'replies_enabled'):
            return

        replier = escape(comment.author.display_name)
        snippet = escape(comment.text[:200]) if comment.text else ''
        content_url = self._content_url(comment)

        text = (
            f'↩️ <b>{replier}</b> sizning kommentingizga javob yozdi:\n\n'
            f'"{snippet}"'
        )
        reply_markup = {
            'inline_keyboard': [[{
                'text': '💬 Javob berish',
                'web_app': {'url': f'{self._domain}{content_url}#comment-{comment.id}'},
            }]],
        }
        self.api.send_message(
            recipient.telegram_id, text, reply_markup=reply_markup,
        )

    def notify_reaction(self, reaction, action: str) -> None:
        """
        Notify comment author about a reaction change.
        *action*: ``'added'`` or ``'removed'``.
        """
        comment = reaction.comment
        if reaction.author_id == comment.author_id:
            return
        recipient = comment.author
        if not self._should_notify(recipient, 'reactions_enabled'):
            return

        reactor = escape(reaction.author.display_name)
        sign = '+1' if action == 'added' else '-1'
        text = f'{sign} {reaction.emoji} — <b>{reactor}</b>'
        self.api.send_message(recipient.telegram_id, text)

    # ── Admin group logging ──────────────────────────────────────────────────

    def log_new_comment(self, comment) -> None:
        if not self._admin_enabled('admin_notify_comments'):
            return
        author = escape(comment.author.display_name)
        url = self._full_url(comment)
        snippet = escape(comment.text[:200]) if comment.text else ''
        text = f'💬 <b>{author}</b> komment yozdi:\n{snippet}' if snippet else f'💬 <b>{author}</b> komment yozdi:'
        button = self._url_button('💬 Kommentni ko\'rish', f'{url}#comment-{comment.id}')
        photo_url = self._comment_image_url(comment)
        self._send_to_admin_group(
            text, comment.author, 'comment',
            reply_markup=button, photo_url=photo_url,
        )

    def log_reply(self, comment) -> None:
        if not self._admin_enabled('admin_notify_replies'):
            return
        parent = comment.parent
        if not parent or not parent.author:
            return
        author = escape(comment.author.display_name)
        parent_author = escape(parent.author.display_name)
        url = self._full_url(comment)
        snippet = escape(comment.text[:200]) if comment.text else ''
        text = f'↩️ <b>{author}</b> → <b>{parent_author}</b>:\n{snippet}' if snippet else f'↩️ <b>{author}</b> → <b>{parent_author}</b>'
        button = self._url_button('💬 Javobni ko\'rish', f'{url}#comment-{comment.id}')
        photo_url = self._comment_image_url(comment)
        self._send_to_admin_group(
            text, comment.author, 'reply',
            reply_markup=button, photo_url=photo_url,
        )

    def log_reaction(self, reaction, action: str) -> None:
        if not self._admin_enabled('admin_notify_reactions'):
            return
        actor = escape(reaction.author.display_name)
        comment_author = escape(reaction.comment.author.display_name)
        verb = 'reacted' if action == 'added' else 'removed'
        text = (
            f'{reaction.emoji} <b>{actor}</b> {verb} '
            f'{reaction.emoji} on <b>{comment_author}</b>\'s comment'
        )
        url = self._comment_anchor_url(reaction.comment)
        button = self._url_button(f'{reaction.emoji} Kommentni ko\'rish', url)
        self._send_to_admin_group(text, reaction.author, 'reaction', reply_markup=button)

    def log_like(self, like, action: str) -> None:
        if not self._admin_enabled('admin_notify_likes'):
            return
        obj = like.content_object
        if not obj:
            return
        actor = escape(like.author.display_name)
        title = self._content_title(obj)
        obj_url = ''
        if hasattr(obj, 'get_absolute_url'):
            obj_url = f'{self._domain}{obj.get_absolute_url()}'
        emoji = '👍' if action == 'liked' else '👎'
        text = f'{emoji} <b>{actor}</b> {action} <b>{escape(title)}</b>'
        button = self._url_button(f'{emoji} Ko\'rish', obj_url) if obj_url else None
        self._send_to_admin_group(text, like.author, 'like', reply_markup=button)

    def log_new_user(self, profile) -> None:
        if not self._admin_enabled('admin_notify_new_users'):
            return
        name = escape(profile.display_name)
        username = f' (@{escape(profile.username)})' if profile.username else ''
        text = f'👤 Yangi user: <b>{name}</b>{username}'
        button = self._url_button('🌐 Saytga o\'tish', self._domain)
        self._send_to_admin_group(text, profile, 'new_user', reply_markup=button)

    def log_contact_message(self, contact) -> None:
        if not self._admin_enabled('admin_notify_contacts'):
            return
        name = escape(contact.name)
        email = escape(contact.email)
        subject = escape(contact.subject)
        body = escape(contact.message[:300])
        text = (
            f'📩 Yangi xabar:\n'
            f'<b>From:</b> {name} ({email})\n'
            f'<b>Subject:</b> {subject}\n'
            f'<b>Message:</b> {body}'
        )
        admin_prefix = getattr(settings, 'ADMIN_URL_PREFIX', 'admin/')
        admin_url = f'{self._domain}/{admin_prefix}contact/contactmessage/'
        button = self._url_button('📩 Admin panelda ko\'rish', admin_url)
        self._send_to_admin_group(text, profile=None, event_type='contact', reply_markup=button)

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _admin_enabled(field_name: str) -> bool:
        """Check whether the admin-group toggle *field_name* is on."""
        site = SiteSettingsService.get()
        return getattr(site, field_name, True)

    @property
    def _domain(self) -> str:
        return getattr(settings, 'TELEGRAM_WEBHOOK_DOMAIN', DEFAULT_DOMAIN)

    def _send_to_admin_group(
        self,
        text: str,
        profile=None,
        event_type: str = '',
        reply_markup: Optional[dict] = None,
        photo_url: Optional[str] = None,
    ) -> Optional[int]:
        """Send message to admin group.  Saves AdminLogMessage for /ban lookup."""
        from interactions.models import AdminLogMessage

        site = SiteSettingsService.get()
        group_id = site.telegram_admin_group_id
        if not group_id:
            return None

        if photo_url:
            result = self.api.send_photo(
                group_id, photo_url,
                caption=text, reply_markup=reply_markup,
            )
        else:
            result = self.api.send_message(group_id, text, reply_markup=reply_markup)

        if result and result.get('ok'):
            msg_id = result['result']['message_id']
            AdminLogMessage.objects.create(
                message_id=msg_id,
                profile=profile,
                event_type=event_type,
            )
            return msg_id
        return None

    def _should_notify(self, profile, pref_field: str) -> bool:
        """
        Check if *profile* should receive the given notification type.
        Site owner always receives, regardless of preferences.
        """
        from interactions.models import NotificationPreference

        if self._is_site_owner(profile):
            return True
        pref, _ = NotificationPreference.objects.get_or_create(profile=profile)
        return getattr(pref, pref_field, True)

    def _is_site_owner(self, profile) -> bool:
        site = SiteSettingsService.get()
        owner_id = site.telegram_owner_id
        return bool(owner_id and profile.telegram_id == owner_id)

    def _comment_image_url(self, comment) -> Optional[str]:
        """Return absolute URL for the comment image, or None."""
        if not comment.image:
            return None
        return f'{self._domain}{comment.image.url}'

    @staticmethod
    def _url_button(label: str, url: str) -> dict:
        """Build a single inline-keyboard row with one URL button.

        Note: ``web_app`` type only works in private chats, not groups.
        ``url`` type opens in Telegram's in-app browser on mobile,
        and in the system browser on desktop — this is a Telegram limitation.
        """
        return {
            'inline_keyboard': [[{'text': label, 'url': url}]],
        }

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
