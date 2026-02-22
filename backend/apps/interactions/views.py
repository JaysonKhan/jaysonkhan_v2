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

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        text = body.get('text', '').strip()
        if not text:
            return JsonResponse({'error': 'Comment text is required'}, status=400)
        if len(text) > 1000:
            return JsonResponse({'error': 'Comment too long (max 1000 chars)'}, status=400)

        try:
            ct = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist:
            return JsonResponse({'error': 'Invalid content type'}, status=404)

        Comment.objects.create(
            author=profile,
            content_type=ct,
            object_id=object_id,
            text=text,
            is_approved=False,
        )
        return JsonResponse({
            'status': 'pending',
            'message': 'Your comment has been submitted and is awaiting moderation.',
        }, status=201)


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
