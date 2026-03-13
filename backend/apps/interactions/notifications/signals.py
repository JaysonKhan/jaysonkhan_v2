"""
Django signal handlers that bridge model lifecycle events to notifications.

Imported in ``InteractionsConfig.ready()`` so that ``@receiver`` decorators
are registered at startup.
"""
from __future__ import annotations

import logging
from typing import Optional

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from interactions.models import Comment, CommentReaction, Like, TelegramProfile
from .service import NotificationService, fire_and_forget

logger = logging.getLogger('interactions.notifications')

# Lazy singleton — avoids creating an httpx client at import time.
_service: Optional[NotificationService] = None


def _get_service() -> NotificationService:
    global _service
    if _service is None:
        _service = NotificationService()
    return _service


# ── Comment signals ──────────────────────────────────────────────────────────

@receiver(post_save, sender=Comment)
def on_comment_created(sender, instance, created, **kwargs):
    if not created:
        return
    svc = _get_service()
    if instance.parent_id:
        # Reply → notify parent author + log
        fire_and_forget(svc.notify_reply, instance)
        fire_and_forget(svc.log_reply, instance)
    else:
        # Top-level comment → log only
        fire_and_forget(svc.log_new_comment, instance)


# ── Reaction signals ─────────────────────────────────────────────────────────

@receiver(post_save, sender=CommentReaction)
def on_reaction_saved(sender, instance, created, **kwargs):
    """Fires on both create and update (emoji change)."""
    svc = _get_service()
    fire_and_forget(svc.notify_reaction, instance, 'added')
    fire_and_forget(svc.log_reaction, instance, 'added')


@receiver(post_delete, sender=CommentReaction)
def on_reaction_deleted(sender, instance, **kwargs):
    svc = _get_service()
    fire_and_forget(svc.notify_reaction, instance, 'removed')
    fire_and_forget(svc.log_reaction, instance, 'removed')


# ── Like signals ─────────────────────────────────────────────────────────────

@receiver(post_save, sender=Like)
def on_like_created(sender, instance, created, **kwargs):
    if not created:
        return
    svc = _get_service()
    fire_and_forget(svc.log_like, instance, 'liked')


@receiver(post_delete, sender=Like)
def on_like_deleted(sender, instance, **kwargs):
    svc = _get_service()
    fire_and_forget(svc.log_like, instance, 'unliked')


# ── New user signal ──────────────────────────────────────────────────────────

@receiver(post_save, sender=TelegramProfile)
def on_profile_created(sender, instance, created, **kwargs):
    if not created:
        return
    svc = _get_service()
    fire_and_forget(svc.log_new_user, instance)


# ── Contact message signal ───────────────────────────────────────────────────
# Imported here so that the signal is registered even though the model
# lives in a different app.

try:
    from contact.models import ContactMessage

    @receiver(post_save, sender=ContactMessage)
    def on_contact_created(sender, instance, created, **kwargs):
        if not created:
            return
        svc = _get_service()
        fire_and_forget(svc.log_contact_message, instance)
except ImportError:
    pass  # contact app not installed — skip gracefully
