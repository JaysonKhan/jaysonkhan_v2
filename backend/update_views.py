import re

with open('/Users/mac/GravityProjects/jaysonkhan_v2/backend/apps/interactions/views.py', 'r') as f:
    text = f.read()

imports = """import json
import logging
import os
import re
from datetime import timedelta

import bleach
from PIL import Image

from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType"""

text = re.sub(r'import json\nimport logging\n\nfrom django\.contrib\.contenttypes\.models import ContentType', imports, text)


post_method_start = text.find('    def post(self, request, app_label, model_name, object_id):')
post_method_end = text.find('            \'message\': \'Your comment has been posted successfully.\',\n        }, status=201)') + 87

new_post_method = """    def post(self, request, app_label, model_name, object_id):
        profile = get_tg_profile(request)
        if not profile:
            return JsonResponse({'error': 'Login with Telegram first'}, status=401)

        # Handle FormData for images and text
        text = request.POST.get('text', '').strip()
        parent_id = request.POST.get('parent_id')
        image = request.FILES.get('image')

        # ── 1. Sanitize text (Prevent XSS) ──
        if text:
            # Strip all HTML tags
            text = bleach.clean(text, tags=[], strip=True)
            
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
        }, status=201)"""

text = text[:post_method_start] + new_post_method + text[post_method_end:]

with open('/Users/mac/GravityProjects/jaysonkhan_v2/backend/apps/interactions/views.py', 'w') as f:
    f.write(text)

