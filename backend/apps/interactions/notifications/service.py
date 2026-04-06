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

from core.emoji import ce
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
        if not comment.author:
            return
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

        text = (
            f'{ce("reply", "↩️")} <b>{replier}</b> sizning kommentingizga javob yozdi:\n\n'
            f'"{snippet}"'
        )
        fallback_url = f'{self._domain}{self._content_url(comment)}#comment-{comment.id}'
        reply_markup = self._deep_link_button(
            '💬 Javob berish', f'c-{comment.id}', fallback_url,
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
        if not comment.author:
            return
        author = escape(comment.author.display_name)
        snippet = escape(comment.text[:200]) if comment.text else ''
        text = f'{ce("comment", "💬")} <b>{author}</b> komment yozdi:\n{snippet}' if snippet else f'{ce("comment", "💬")} <b>{author}</b> komment yozdi:'
        fallback_url = f'{self._full_url(comment)}#comment-{comment.id}'
        button = self._deep_link_button(
            '💬 Kommentni ko\'rish', f'c-{comment.id}', fallback_url,
        )
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
        snippet = escape(comment.text[:200]) if comment.text else ''
        text = f'↩️ <b>{author}</b> → <b>{parent_author}</b>:\n{snippet}' if snippet else f'↩️ <b>{author}</b> → <b>{parent_author}</b>'
        fallback_url = f'{self._full_url(comment)}#comment-{comment.id}'
        button = self._deep_link_button(
            '💬 Javobni ko\'rish', f'c-{comment.id}', fallback_url,
        )
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
        comment = reaction.comment
        fallback_url = self._comment_anchor_url(comment)
        button = self._deep_link_button(
            f'{reaction.emoji} Kommentni ko\'rish', f'c-{comment.id}', fallback_url,
        )
        self._send_to_admin_group(text, reaction.author, 'reaction', reply_markup=button)

    def log_like(self, like, action: str) -> None:
        if not self._admin_enabled('admin_notify_likes'):
            return
        obj = like.content_object
        if not obj:
            return
        actor = escape(like.author.display_name)
        title = self._content_title(obj)
        emoji = '👍' if action == 'liked' else '👎'
        text = f'{emoji} <b>{actor}</b> {action} <b>{escape(title)}</b>'
        startapp = self._content_startapp(obj)
        fallback_url = ''
        if hasattr(obj, 'get_absolute_url'):
            fallback_url = f'{self._domain}{obj.get_absolute_url()}'
        button = self._deep_link_button(
            f'{emoji} Ko\'rish', startapp, fallback_url,
        ) if (startapp or fallback_url) else None
        self._send_to_admin_group(text, like.author, 'like', reply_markup=button)

    def log_new_user(self, profile) -> None:
        if not self._admin_enabled('admin_notify_new_users'):
            return

        # ── FunStat stats_min (bepul) ─────────────────────────────────────
        funstat = {}
        if profile.entity_type in ('user', 'bot'):
            try:
                from osint.services.osint_service import fetch_or_cache
                result = fetch_or_cache('stats_min', profile.telegram_id)
                if result and result.data:
                    funstat = result.data
            except Exception:
                logger.debug('FunStat stats_min failed for %s', profile.telegram_id)

        # ── Entity type ───────────────────────────────────────────────────
        type_map = {
            'user': (ce('user', '👤'), 'Foydalanuvchi'),
            'bot': (ce('bot', '🤖'), 'Bot'),
            'group': ('👥', 'Guruh'),
            'supergroup': ('👥', 'Superguruh'),
            'channel': ('📢', 'Kanal'),
        }
        emoji, type_label = type_map.get(profile.entity_type, (ce('user', '👤'), 'Noma\'lum'))

        # ── Servis manbalarini erta so'rash (yangi vs qaytgan user uchun) ──
        svc_labels = {
            'site': f'{ce("web", "🌐")} Sayt (Login)',
            'osint': f'{ce("osint", "🔍")} OSINT',
            'talabaovozi': f'{ce("education", "🎓")} TalabaOvozi',
        }
        svc_action_labels = {
            'site': f'{ce("web", "🌐")} Saytga kirdi',
            'osint': f'{ce("osint", "🔍")} OSINT qidirildi',
            'talabaovozi': f'{ce("education", "🎓")} TalabaOvozi botga qo\'shildi',
        }
        try:
            from telegram.models import EntitySource
            sources = list(
                EntitySource.objects.filter(entity=profile)
                .values_list('service', flat=True)
            )
        except Exception:
            sources = []
        is_returning = len(sources) > 1

        # Ism — FunStat dan yangilangan bo'lishi mumkin
        fs_name = ''
        if funstat:
            parts = [funstat.get('first_name', ''), funstat.get('last_name', '')]
            fs_name = ' '.join(p for p in parts if p).strip()
        name = escape(fs_name or profile.display_name)

        if is_returning:
            # Qaytgan user — yangi servisdan kirdi
            new_service = sources[0] if sources else ''  # ordering = ["-updated_at"]
            action = svc_action_labels.get(new_service, f'{new_service} dan topildi')
            lines = [f'{ce("returning", "🔄")} <b>{name}</b> — {action}']
        else:
            lines = [f'{emoji} <b>Yangi {type_label.lower()}: {name}</b>']

        # ── Asosiy ma'lumotlar ────────────────────────────────────────────
        username = funstat.get('username') or profile.username
        info_parts = [f'🆔 <code>{profile.telegram_id}</code>']
        if username:
            info_parts.append(f'@{escape(username)}')
        lines.append(' · '.join(info_parts))

        phone = funstat.get('phone') or profile.phone
        if phone:
            lines.append(f'📱 <code>{escape(phone)}</code>')

        # ── Qaysi servislar orqali topilgan ──────────────────────────────
        if sources:
            src_str = ', '.join(svc_labels.get(s, s) for s in sources)
            lines.append(f'📡 {src_str}')

        # ── Badgelar ──────────────────────────────────────────────────────
        badges = []
        if funstat.get('is_premium') or getattr(profile, 'is_premium', False):
            badges.append(f'{ce("premium", "⭐️")} Premium')
        if funstat.get('is_verified') or getattr(profile, 'is_verified', False):
            badges.append('✅ Tasdiqlangan')
        if funstat.get('is_scam') or getattr(profile, 'is_scam', False):
            badges.append('⚠️ SCAM')
        if funstat.get('is_fake') or getattr(profile, 'is_fake', False):
            badges.append('🚫 FAKE')
        if funstat.get('is_bot'):
            badges.append('🤖 Bot')
        is_active = funstat.get('is_active')
        if is_active is True:
            badges.append('🟢 Faol')
        elif is_active is False:
            badges.append('🔴 Nofaol')
        if badges:
            lines.append(' · '.join(badges))

        # ── FunStat statistika ────────────────────────────────────────────
        if funstat:
            stats_parts = []
            total_msg = funstat.get('total_msg_count')
            if total_msg:
                stats_parts.append(f'💬 {total_msg:,} xabar')
            total_grp = funstat.get('total_groups')
            if total_grp:
                stats_parts.append(f'👥 {total_grp} guruh')
            adm = funstat.get('adm_in_groups')
            if adm:
                stats_parts.append(f'👑 {adm} admin')
            if stats_parts:
                lines.append(' · '.join(stats_parts))

            history_parts = []
            unames = funstat.get('usernames_count')
            if unames:
                history_parts.append(f'📝 {unames} username')
            names = funstat.get('names_count')
            if names:
                history_parts.append(f'✏️ {names} ism')
            if history_parts:
                lines.append(' · '.join(history_parts))

            # Faollik davri
            first_d = funstat.get('first_msg_date', '')
            last_d = funstat.get('last_msg_date', '')
            if first_d and last_d:
                lines.append(f'📅 {str(first_d)[:10]} — {str(last_d)[:10]}')
            elif first_d:
                lines.append(f'📅 {str(first_d)[:10]} dan beri')

        # ── Bio ───────────────────────────────────────────────────────────
        bio = funstat.get('about') or funstat.get('bio') or getattr(profile, 'bio', '')
        if bio:
            lines.append(f'💬 <i>{escape(str(bio)[:120])}</i>')

        text = '\n'.join(lines)

        # ── Tugmalar ──────────────────────────────────────────────────────
        buttons = []
        # OSINT — Mini App deep link (Telegram ichida ochiladi)
        if profile.entity_type in ('channel', 'supergroup', 'group'):
            startapp = f'osint-e-{profile.telegram_id}'
        else:
            startapp = f'osint-p-{profile.telegram_id}'
        deep_url = self._tg_deep_link(startapp)
        if deep_url:
            buttons.append([{'text': f'{ce("osint", "🔍")} OSINT', 'url': deep_url}])
        else:
            # Fallback — oddiy URL
            try:
                from django.urls import reverse
                if profile.entity_type in ('channel', 'supergroup', 'group'):
                    osint_url = reverse(
                        'osint_entity_profile',
                        kwargs={'entity_id': profile.telegram_id},
                    )
                else:
                    osint_url = reverse(
                        'osint_profile',
                        kwargs={'user_id': profile.telegram_id},
                    )
                buttons.append([{
                    'text': f'{ce("osint", "🔍")} OSINT',
                    'url': f'{self._domain}{osint_url}',
                }])
            except Exception:
                pass
        buttons.append([
            {'text': '⚙️ Admin', 'url': self._admin_entity_url(profile)},
            {'text': '🌐 Sayt', 'url': self._domain},
        ])

        reply_markup = {'inline_keyboard': buttons}
        photo_url = profile.get_photo_url() or None
        self._send_to_admin_group(
            text, profile, 'new_user',
            reply_markup=reply_markup, photo_url=photo_url,
        )

    def log_contact_message(self, contact) -> None:
        if not self._admin_enabled('admin_notify_contacts'):
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
        admin_prefix = getattr(settings, 'ADMIN_URL_PREFIX', 'admin/')
        admin_url = f'{self._domain}/{admin_prefix}contact/contactmessage/'
        button = {'inline_keyboard': [[{'text': f'{ce("contact_msg", "📩")} Admin panelda ko\'rish', 'url': admin_url}]]}
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
    ) -> Optional[int]:
        """Send message to admin group.  Saves AdminLogMessage for /ban lookup."""
        from interactions.models import AdminLogMessage

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

    def _deep_link_button(self, label: str, startapp: str, fallback_url: str = '') -> dict:
        """Build inline keyboard with Mini App deep link button.

        If deep link settings (bot username / app name) are configured,
        the button opens the page inside Telegram's Mini App browser.
        Otherwise falls back to a regular URL button.

        Supports Bot API 9.4 icon_custom_emoji_id for animated emoji.
        """
        deep_url = self._tg_deep_link(startapp) if startapp else ''
        url = deep_url or fallback_url or self._domain
        btn = {'text': label, 'url': url}
        # Add custom emoji for comment buttons (💬)
        site = SiteSettingsService.get()
        emoji_id = getattr(site, 'tg_emoji_comment', '') or ''
        if emoji_id and label.startswith('💬'):
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
