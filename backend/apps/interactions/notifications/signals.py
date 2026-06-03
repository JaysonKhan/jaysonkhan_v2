"""
Django signal handlers that bridge model lifecycle events to notifications.

Imported in ``InteractionsConfig.ready()`` so that ``@receiver`` decorators
are registered at startup.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from interactions.models import Comment, CommentReaction, Like
from telegram.models import EntitySource

from .service import NotificationService, fire_and_forget

logger = logging.getLogger('interactions.notifications')

# Lazy singleton — avoids creating an httpx client at import time.
_service: Optional[NotificationService] = None
_service_lock = threading.Lock()


def _get_service() -> NotificationService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:  # double-checked locking
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
    if not created:
        return  # emoji update -- suppress spurious DM
    svc = _get_service()
    fire_and_forget(svc.notify_reaction, instance, 'added')
    fire_and_forget(svc.log_reaction, instance, 'added')


@receiver(post_delete, sender=CommentReaction)
def on_reaction_deleted(sender, instance, **kwargs):
    # Guard: comment or author may have been cascade-deleted already
    try:
        _ = instance.comment.author
    except Exception:
        return
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
    # Guard: content_object may have been cascade-deleted already
    try:
        if not instance.content_object:
            return
    except Exception:
        return
    svc = _get_service()
    fire_and_forget(svc.log_like, instance, 'unliked')


# ── New user / new service signal ─────────────────────────────────────────────
# Fires on EntitySource creation, not TelegramEntity.
# This covers BOTH:
#   - Completely new user (first EntitySource created after TelegramEntity)
#   - Existing user discovered via new service (e.g., OSINT user logs into website)

@receiver(post_save, sender=EntitySource)
def on_source_created(sender, instance, created, **kwargs):
    if not created:
        return
    svc = _get_service()
    fire_and_forget(svc.log_new_user, instance.entity)


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
