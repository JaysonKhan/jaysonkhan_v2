import json
import logging
import os
import re
from datetime import timedelta

import bleach
from PIL import Image

from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.views import View
from django.db.models import Count
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import redirect
from .models import TelegramProfile, Comment, Like
from .telegram_auth import verify_telegram_auth

logger = logging.getLogger(__name__)


# ── Session helpers ────────────────────────────────────────────────────────────

SESSION_KEY = 'tg_profile_id'


def get_tg_profile(request):
    """Return the TelegramProfile for the current session, or None."""
    profile_id = request.session.get(SESSION_KEY)
    if not profile_id:
        return None
    try:
        return TelegramProfile.objects.get(pk=profile_id)
    except TelegramProfile.DoesNotExist:
        del request.session[SESSION_KEY]
        return None


# ── Telegram Login Widget callback ─────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class TelegramAuthView(View):
    """
    GET /auth/telegram/?id=...&first_name=...&hash=...
    Called by the Telegram Login Widget after the user authorizes.
    Verifies data, upserts TelegramProfile, stores session, then redirects.
    """

    def get(self, request):
        data = dict(request.GET)
        # GET params come as lists; flatten them
        flat = {k: v[0] if isinstance(v, list) else v for k, v in data.items()}

        next_url = flat.pop('next', request.META.get('HTTP_REFERER', '/'))

        # ── Debug logging ──────────────────────────────────────────────────────
        safe_flat = {k: (v[:8] + '…' if k == 'hash' else v) for k, v in flat.items()}
        logger.info('[TelegramAuth] incoming params: %s | next_url: %s', safe_flat, next_url)

        if not verify_telegram_auth(flat):
            logger.warning('[TelegramAuth] FAILED verification. Params: %s', safe_flat)
            return JsonResponse({'error': 'Invalid Telegram authentication'}, status=400)

        logger.info('[TelegramAuth] verification OK for id=%s', flat.get('id'))

        profile, _ = TelegramProfile.objects.update_or_create(
            telegram_id=int(flat['id']),
            defaults={
                'first_name': flat.get('first_name', ''),
                'last_name':  flat.get('last_name', ''),
                'username':   flat.get('username', ''),
                'photo_url':  flat.get('photo_url', ''),
                'auth_date':  int(flat.get('auth_date', 0)),
            }
        )
        request.session[SESSION_KEY] = profile.pk
        request.session.modified = True
        return redirect(next_url)


class TelegramLogoutView(View):
    """POST /auth/telegram/logout/ — clears the Telegram session."""

    def post(self, request):
        request.session.pop(SESSION_KEY, None)
        next_url = request.POST.get('next', request.META.get('HTTP_REFERER', '/'))
        return redirect(next_url)


# ── Comment view ───────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class AddCommentView(View):
    """
    POST /interactions/comment/<app_label>/<model_name>/<object_id>/
    e.g. /interactions/comment/blog/post/5/
         /interactions/comment/portfolio/project/3/
    """

    def post(self, request, app_label, model_name, object_id):
        profile = get_tg_profile(request)
        if not profile:
            return JsonResponse({'error': 'Login with Telegram first'}, status=401)

        # Handle FormData for images and text
        text = request.POST.get('text', '').strip()
        parent_id = request.POST.get('parent_id')
        image = request.FILES.get('image')

        # ── 1. Sanitize & normalize text ──
        if text:
            text = bleach.clean(text, tags=[], strip=True)
            # Har satrda ortiqcha bo'shliqlarni tozala, umumiy trim
            text = '\n'.join(
                re.sub(r'[ \t]+', ' ', line).strip()
                for line in text.splitlines()
            ).strip()

        if not text and not image:
            return JsonResponse({'error': 'Comment must have text or an image'}, status=400)
        
        # ── 2. Message Length Validation ──
        min_len = getattr(settings, 'COMMENT_MIN_LENGTH', 3)
        max_len = getattr(settings, 'COMMENT_MAX_LENGTH', 1000)
        if text:
            if len(text) < min_len and not image:
                return JsonResponse({'error': f'Comment must be at least {min_len} characters'}, status=400)
            if len(text) > max_len:
                return JsonResponse({'error': f'Comment too long (max {max_len} chars)'}, status=400)

        # ── 3. Image Validation (Size & MIME) ──
        if image:
            max_mb = getattr(settings, 'COMMENT_MAX_IMAGE_MB', 5)
            if image.size > max_mb * 1024 * 1024:
                return JsonResponse({'error': f'Image is too large (max {max_mb}MB)'}, status=400)
            
            allowed_mimes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image.content_type not in allowed_mimes:
                return JsonResponse({'error': 'Invalid image format (must be JPG, PNG, GIF, WEBP)'}, status=400)
                
            try:
                img = Image.open(image)
                img.verify()
                image.seek(0)
            except Exception as e:
                logger.warning(f'[Upload] Invalid image from {profile.telegram_id}: {e}')
                return JsonResponse({'error': 'Uploaded file is corrupted or not a valid image'}, status=400)

        # ── 4. Rate Limiting logic ──
        now = timezone.now()
        is_new_user = (now - profile.created_at) < timedelta(hours=getattr(settings, 'COMMENT_NEW_USER_HOURS', 24))

        if is_new_user:
            limit_mins = getattr(settings, 'COMMENT_NEW_USER_RATE_MINS', 10)
            limit_count = getattr(settings, 'COMMENT_NEW_USER_RATE_COUNT', 1)
        else:
            limit_mins = getattr(settings, 'COMMENT_RATE_LIMIT_MINUTES', 1)
            limit_count = getattr(settings, 'COMMENT_RATE_LIMIT_COUNT', 3)

        recent_comments = Comment.objects.filter(
            author=profile, 
            created_at__gte=now - timedelta(minutes=limit_mins)
        )
        if recent_comments.count() >= limit_count:
            logger.warning(f'[RateLimit] User {profile.telegram_id} blocked')
            return JsonResponse({'error': 'You are posting too fast. Please wait a moment.'}, status=429)

        # ── 5. Duplicate Detection ──
        dup_window = getattr(settings, 'COMMENT_DUP_WINDOW_MINUTES', 5)
        last_comment = Comment.objects.filter(
            author=profile, 
            created_at__gte=now - timedelta(minutes=dup_window)
        ).order_by('-created_at').first()
        
        if last_comment and text and last_comment.text == text:
            logger.warning(f'[Spam] Duplicate text from {profile.telegram_id}')
            return JsonResponse({'error': 'Duplicate comment detected.'}, status=400)

        # ── 6. Content Moderation (Keywords & Links) ──
        is_approved = True
        is_reviewed = False
        
        spam_keywords = getattr(settings, 'COMMENT_SPAM_KEYWORDS', [
            r'http[s]?://', r'www\.', r'\.com', r'\.ru', r'crypto', r'casino', r'viagra'
        ])
        if text:
            for kw in spam_keywords:
                if re.search(kw, text, re.IGNORECASE):
                    is_approved = False
                    logger.warning(f'[Moderation] Auto-quarantined comment from {profile.telegram_id}')
                    break

        if is_new_user and is_approved:
            # We want to flag new user comments as not reviewed
            is_reviewed = False

        # ── Setup target object ──
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist:
            return JsonResponse({'error': 'Invalid content type'}, status=404)

        parent = None
        if parent_id:
            try:
                parent = Comment.objects.get(id=int(parent_id), content_type=ct, object_id=object_id)
            except (ValueError, Comment.DoesNotExist):
                return JsonResponse({'error': 'Invalid parent comment'}, status=400)

        # ── Save comment ──
        Comment.objects.create(
            author=profile,
            content_type=ct,
            object_id=object_id,
            text=text,
            parent=parent,
            image=image,
            is_approved=is_approved,
            is_reviewed=is_reviewed,
        )
        
        return JsonResponse({
            'status': 'pending' if not is_approved else 'ok',
            'message': 'Your comment is pending admin review.' if not is_approved else 'Your comment has been posted successfully.',
        }, status=201)

@method_decorator(csrf_exempt, name='dispatch')
class ToggleCommentReactionView(View):
    """
    POST /interactions/comment/<int:comment_id>/react/
    Body JSON or POST Form with `emoji`.
    """
    def post(self, request, comment_id):
        profile = get_tg_profile(request)
        if not profile:
            return JsonResponse({'error': 'Login with Telegram first'}, status=401)

        try:
            body = json.loads(request.body)
            emoji = body.get('emoji', '').strip()
        except json.JSONDecodeError:
            emoji = request.POST.get('emoji', '').strip()
            
        if not emoji:
            return JsonResponse({'error': 'Emoji is required'}, status=400)

        # Basic emoji validation can be added here, we keep it simple for now
        
        try:
            comment = Comment.objects.get(id=comment_id)
        except Comment.DoesNotExist:
            return JsonResponse({'error': 'Comment not found'}, status=404)
        
        # Toggle: if the same reaction exists from this user, delete it.
        # If the user has another reaction, update it. If they have none, create it.
        from .models import CommentReaction
        
        reaction = CommentReaction.objects.filter(author=profile, comment=comment).first()
        if reaction:
            if reaction.emoji == emoji:
                reaction.delete()
                action = 'removed'
            else:
                reaction.emoji = emoji
                reaction.save()
                action = 'updated'
        else:
            CommentReaction.objects.create(author=profile, comment=comment, emoji=emoji)
            action = 'added'

        # Count reactions for this comment
        reactions = CommentReaction.objects.filter(comment=comment).values_list('emoji', flat=True)
        from collections import Counter
        counts = dict(Counter(reactions))

        return JsonResponse({'status': 'ok', 'action': action, 'reactions': counts}, status=200)


# ── Like / Unlike (toggle) ─────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class ToggleLikeView(View):
    """
    POST /interactions/like/<app_label>/<model_name>/<object_id>/
    Returns { liked: true/false, count: N }
    """

    def post(self, request, app_label, model_name, object_id):
        profile = get_tg_profile(request)
        if not profile:
            return JsonResponse({'error': 'Login with Telegram first'}, status=401)

        try:
            ct = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist:
            return JsonResponse({'error': 'Invalid content type'}, status=404)

        like, created = Like.objects.get_or_create(
            author=profile,
            content_type=ct,
            object_id=object_id,
        )
        if not created:
            like.delete()
            liked = False
        else:
            liked = True

        count = Like.objects.filter(content_type=ct, object_id=object_id).count()
        return JsonResponse({'liked': liked, 'count': count})


def serialize_comment(comment, tg_profile_id=None):
    # Determine the requester's reaction if logged in
    user_reaction = None
    if tg_profile_id:
        for r in comment.reactions.all():
            if r.author_id == tg_profile_id:
                user_reaction = r.emoji
                break

    # Build group reactions
    reaction_counts = {}
    for r in comment.reactions.all():
        reaction_counts[r.emoji] = reaction_counts.get(r.emoji, 0) + 1

    return {
        "id": comment.id,
        "author": {
            "id": comment.author.id,
            "display_name": comment.author.display_name,
            "photo_url": comment.author.photo_url,
            "initial": comment.author.first_name[0].upper() if comment.author.first_name else 'U',
        },
        "text": comment.text,
        "image_url": comment.image.url if getattr(comment, 'image', None) and hasattr(comment.image, 'url') else None,
        "created_at": comment.created_at.strftime('%H:%M'),
        "is_reviewed": comment.is_reviewed,
        "is_own": tg_profile_id == comment.author.id,
        "reaction_counts": reaction_counts,
        "user_reaction": user_reaction,
        "reply_count": getattr(comment, 'reply_count', comment.replies.filter(is_approved=True).count()),
        "parent_id": comment.parent_id
    }


class ListCommentsView(View):
    """
    GET /interactions/comments/?app_label=...&model=...&object_id=...&page=1&sort=top
    """
    def get(self, request):
        app_label = request.GET.get('app_label')
        model = request.GET.get('model')
        object_id = request.GET.get('object_id')
        sort = request.GET.get('sort', 'top')
        page = int(request.GET.get('page', 1))

        try:
            ct = ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist:
            return JsonResponse({'error': 'Invalid content type'}, status=404)

        # Get parent comments only
        qs = Comment.objects.filter(
            content_type=ct, 
            object_id=object_id, 
            is_approved=True, 
            parent__isnull=True
        ).select_related('author').prefetch_related('reactions', 'reactions__author')

        if sort == 'top':
            # Sorting formula: Score interactions dynamically
            qs = qs.annotate(
                rcount=Count('reactions', distinct=True),
                pcount=Count('replies', distinct=True)
            ).order_by('-rcount', '-pcount', '-created_at')
        else:
            qs = qs.order_by('-created_at')

        paginator = Paginator(qs, 10)
        page_obj = paginator.get_page(page)

        tg_profile_id = request.session.get('tg_profile_id')
        data = [serialize_comment(c, tg_profile_id) for c in page_obj.object_list]

        return JsonResponse({
            'comments': data,
            'has_next': page_obj.has_next(),
            'total_count': paginator.count
        })

class ListRepliesView(View):
    """
    GET /interactions/comments/<parent_id>/replies/?page=1
    """
    def get(self, request, parent_id):
        page = int(request.GET.get('page', 1))
        qs = Comment.objects.filter(
            parent_id=parent_id, 
            is_approved=True
        ).select_related('author').prefetch_related('reactions', 'reactions__author').order_by('created_at')
        
        paginator = Paginator(qs, 10)
        page_obj = paginator.get_page(page)

        tg_profile_id = request.session.get('tg_profile_id')
        data = [serialize_comment(c, tg_profile_id) for c in page_obj.object_list]

        return JsonResponse({
            'replies': data,
            'has_next': page_obj.has_next()
        })
