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


# ── Thread helper ────────────────────────────────────────────────────────────

def _fire_and_forget(fn, *args, **kwargs):
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
        if not parent:
            return
        # Don't notify self-replies
        if comment.author_id == parent.author_id:
            return
        recipient = parent.author
        if not self._should_notify(recipient, 'replies_enabled'):
            return

        replier = escape(comment.author.display_name)
        snippet = escape(comment.text[:200])
        content_url = self._get_content_url(comment)
        domain = getattr(settings, 'TELEGRAM_WEBHOOK_DOMAIN', 'https://jaysonkhan.com')

        text = (
            f'↩️ <b>{replier}</b> sizning kommentingizga javob yozdi:\n\n'
            f'"{snippet}"'
        )
        reply_markup = {
            'inline_keyboard': [[{
                'text': '💬 Javob berish',
                'web_app': {'url': f'{domain}{content_url}#comment-{comment.id}'},
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
        # Don't notify self-reactions
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
        site = SiteSettingsService.get()
        if not site.admin_notify_comments:
            return
        author = escape(comment.author.display_name)
        title = self._get_content_title(comment.content_object)
        url = self._get_full_url(comment)
        snippet = escape(comment.text[:200])
        text = (
            f'💬 <a href="{url}">{escape(title)}</a> ga komment:\n'
            f'<b>{author}</b>: {snippet}'
        )
        self._send_to_admin_group(text, comment.author, 'comment')

    def log_reply(self, comment) -> None:
        site = SiteSettingsService.get()
        if not site.admin_notify_replies:
            return
        author = escape(comment.author.display_name)
        parent_author = escape(comment.parent.author.display_name)
        title = self._get_content_title(comment.content_object)
        url = self._get_full_url(comment)
        snippet = escape(comment.text[:200])
        text = (
            f'↩️ <a href="{url}">{escape(title)}</a>:\n'
            f'<b>{author}</b> → <b>{parent_author}</b>: {snippet}'
        )
        self._send_to_admin_group(text, comment.author, 'reply')

    def log_reaction(self, reaction, action: str) -> None:
        site = SiteSettingsService.get()
        if not site.admin_notify_reactions:
            return
        actor = escape(reaction.author.display_name)
        comment_author = escape(reaction.comment.author.display_name)
        verb = 'reacted' if action == 'added' else 'removed'
        text = (
            f'{reaction.emoji} <b>{actor}</b> {verb} '
            f'{reaction.emoji} on <b>{comment_author}</b>\'s comment'
        )
        self._send_to_admin_group(text, reaction.author, 'reaction')

    def log_like(self, like, action: str) -> None:
        site = SiteSettingsService.get()
        if not site.admin_notify_likes:
            return
        actor = escape(like.author.display_name)
        obj = like.content_object
        title = self._get_content_title(obj)
        domain = getattr(settings, 'TELEGRAM_WEBHOOK_DOMAIN', 'https://jaysonkhan.com')
        obj_url = ''
        if hasattr(obj, 'get_absolute_url'):
            obj_url = f'{domain}{obj.get_absolute_url()}'
        emoji = '👍' if action == 'liked' else '👎'
        if obj_url:
            text = f'{emoji} <b>{actor}</b> {action} <a href="{obj_url}">{escape(title)}</a>'
        else:
            text = f'{emoji} <b>{actor}</b> {action} {escape(title)}'
        self._send_to_admin_group(text, like.author, 'like')

    def log_new_user(self, profile) -> None:
        site = SiteSettingsService.get()
        if not site.admin_notify_new_users:
            return
        name = escape(profile.display_name)
        username = f' (@{escape(profile.username)})' if profile.username else ''
        text = f'👤 Yangi user: <b>{name}</b>{username}'
        self._send_to_admin_group(text, profile, 'new_user')

    def log_contact_message(self, contact) -> None:
        site = SiteSettingsService.get()
        if not site.admin_notify_contacts:
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
        self._send_to_admin_group(text, profile=None, event_type='contact')

    # ── Private helpers ──────────────────────────────────────────────────────

    def _send_to_admin_group(
        self,
        text: str,
        profile=None,
        event_type: str = '',
    ) -> Optional[int]:
        """Send message to admin group.  Saves AdminLogMessage for /ban lookup."""
        from interactions.models import AdminLogMessage

        site = SiteSettingsService.get()
        group_id = site.telegram_admin_group_id
        if not group_id:
            return None

        result = self.api.send_message(group_id, text)
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

    @staticmethod
    def _get_content_url(comment) -> str:
        """Resolve relative URL for the content object a comment is attached to."""
        obj = comment.content_object
        if hasattr(obj, 'get_absolute_url'):
            return obj.get_absolute_url()
        return '/'

    def _get_full_url(self, comment) -> str:
        domain = getattr(settings, 'TELEGRAM_WEBHOOK_DOMAIN', 'https://jaysonkhan.com')
        return f'{domain}{self._get_content_url(comment)}'

    @staticmethod
    def _get_content_title(content_object) -> str:
        return getattr(content_object, 'title', str(content_object))
