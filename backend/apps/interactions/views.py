import json
import logging

from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.views import View
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

        if not text and not image:
            return JsonResponse({'error': 'Comment must have text or an image'}, status=400)
        
        if text and len(text) > 1000:
            return JsonResponse({'error': 'Comment too long (max 1000 chars)'}, status=400)

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

        Comment.objects.create(
            author=profile,
            content_type=ct,
            object_id=object_id,
            text=text,
            parent=parent,
            image=image,
            is_approved=False, # Could auto-approve for testing, but keeping False for now (user usually needs manual app or auto-app logic)
        )
        return JsonResponse({
            'status': 'pending',
            'message': 'Your comment has been submitted and is awaiting moderation.',
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
