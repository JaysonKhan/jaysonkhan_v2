"""Shared public discussion queries for SSR and JSON endpoints."""
import html

from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils.translation import gettext as _

from .models import Comment


COMMENTABLE_CONTENT_TYPES = frozenset([('blog', 'post'), ('portfolio', 'project')])


def public_target(app_label, model_name, object_id):
    if (app_label, model_name) not in COMMENTABLE_CONTENT_TYPES:
        return None
    try:
        object_id = int(object_id)
        ct = ContentType.objects.get(app_label=app_label, model=model_name)
    except (ValueError, TypeError, ContentType.DoesNotExist):
        return None
    field = 'is_published' if app_label == 'blog' else 'is_visible'
    model = ct.model_class()
    return ct if model and model.objects.filter(pk=object_id, **{field: True}).exists() else None


def public_comment(comment_id, allow_deleted=False):
    comment = Comment.objects.select_related('content_type', 'parent', 'author').filter(
        pk=comment_id, is_approved=True,
    ).first()
    if not comment or (comment.deleted_at and not allow_deleted) or (comment.parent_id and not comment.parent.is_approved):
        return None
    return comment if public_target(comment.content_type.app_label, comment.content_type.model, comment.object_id) else None


def comment_queryset(ct, object_id):
    return Comment.objects.filter(content_type=ct, object_id=object_id, is_approved=True).filter(
        Q(parent__isnull=True) | Q(parent__is_approved=True)
    ).select_related('author', 'reply_to__author').prefetch_related('reactions').annotate(
        reply_count=Count('replies', filter=Q(replies__is_approved=True, replies__deleted_at__isnull=True), distinct=True)
    ).filter(Q(deleted_at__isnull=True) | Q(parent__isnull=True, reply_count__gt=0))


def discussion_page(ct, object_id, profile_id=None, page=1, sort='top'):
    qs = comment_queryset(ct, object_id)
    roots = qs.filter(parent__isnull=True)
    if sort == 'top':
        roots = roots.annotate(rcount=Count('reactions', distinct=True)).order_by('-rcount', '-reply_count', '-created_at', '-pk')
    else:
        roots = roots.order_by('-created_at', '-pk')
    result = Paginator(roots, 10).get_page(page)
    return {
        'comments': [serialize_comment(c, profile_id) for c in result.object_list],
        'has_next': result.has_next(),
        'page': result.number,
        'total_count': result.paginator.count,
        'discussion_count': qs.filter(deleted_at__isnull=True).count(),
    }


def serialize_comment(comment, tg_profile_id=None):
    # Cache reactions once (avoids duplicate iteration over prefetch cache)
    reactions = [] if comment.deleted_at else list(comment.reactions.all())

    # Determine the requester's reaction if logged in
    user_reaction = None
    if tg_profile_id:
        for r in reactions:
            if r.author_id == tg_profile_id:
                user_reaction = r.emoji
                break

    # Build group reactions
    reaction_counts = {}
    for r in reactions:
        reaction_counts[r.emoji] = reaction_counts.get(r.emoji, 0) + 1

    deleted = bool(comment.deleted_at)
    target = comment.reply_to
    reply_to = {"id": target.pk, "name": target.author.safe_display_name} if target and not target.deleted_at and target.is_approved else None
    return {
        "id": comment.id,
        "is_deleted": deleted,
        "reply_to": reply_to,
        "author": {
            "id": None if deleted else comment.author.id,
            # safe_display_name: tofu/format chars stripped, length-capped —
            # the client renders it via textContent, never innerHTML.
            "display_name": _('Deleted comment') if deleted else comment.author.safe_display_name,
            "photo_url": None if deleted else comment.author.photo_url,
            "initial": "" if deleted else comment.author.safe_initial,
        },
        # Legacy rows carry bleach entity-encoding (&lt; &amp;) — unescape to
        # plain text; the client textContent-renders it.
        "text": _('This comment was deleted.') if deleted else (html.unescape(comment.text) if comment.text else comment.text),
        "image_url": comment.image.url if comment.image and not deleted else None,
        "created_at": comment.created_at.isoformat(),
        "is_reviewed": comment.is_reviewed,
        "is_own": not deleted and tg_profile_id == comment.author.id,
        "reaction_counts": reaction_counts,
        "user_reaction": user_reaction,
        "reply_count": comment.reply_count if hasattr(comment, "reply_count") else comment.replies.filter(is_approved=True, deleted_at__isnull=True).count(),
        "parent_id": comment.parent_id
    }

