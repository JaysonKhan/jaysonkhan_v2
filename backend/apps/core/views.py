import logging
import os
import uuid
import io

from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from PIL import Image

logger = logging.getLogger(__name__)

# ── Allowed file types (whitelist approach) ──────────────────────────────────
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS

# Magic byte signatures for image validation
IMAGE_MAGIC_BYTES = {
    b'\xff\xd8\xff': 'jpeg',
    b'\x89PNG': 'png',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'RIFF': 'webp',
}

MAX_IMAGE_SIZE = 10 * 1024 * 1024   # 10 MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024   # 50 MB


@staff_member_required
@require_POST
def upload_media_view(request):
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': 'No file provided'}, status=400)

    # ── 1. Extension whitelist ────────────────────────────────────────────
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning('[Upload] Blocked extension: %s from user %s', ext, request.user)
        return JsonResponse({
            'error': f'File type "{ext}" is not allowed. Allowed: {", ".join(sorted(ALLOWED_EXTENSIONS))}'
        }, status=400)

    # ── 2. Size validation ────────────────────────────────────────────────
    is_image = ext in ALLOWED_IMAGE_EXTENSIONS
    max_size = MAX_IMAGE_SIZE if is_image else MAX_VIDEO_SIZE
    if file.size > max_size:
        max_mb = max_size // (1024 * 1024)
        return JsonResponse({'error': f'File too large. Max {max_mb} MB.'}, status=400)

    # ── 3. MIME type validation ───────────────────────────────────────────
    if is_image and not file.content_type.startswith('image/'):
        return JsonResponse({'error': 'MIME type does not match file extension.'}, status=400)
    if not is_image and not file.content_type.startswith('video/'):
        return JsonResponse({'error': 'MIME type does not match file extension.'}, status=400)

    # ── 4. Filename sanitization (UUID only, no user-supplied name) ───────
    new_filename = f"{uuid.uuid4().hex}{ext}"

    # ── 5. Image processing with magic byte validation ───────────────────
    if is_image and ext != '.svg':
        # Read first bytes for magic byte check
        header = file.read(8)
        file.seek(0)

        valid_magic = False
        for magic, _ in IMAGE_MAGIC_BYTES.items():
            if header.startswith(magic):
                valid_magic = True
                break

        if not valid_magic and ext not in {'.webp', '.svg'}:
            logger.warning('[Upload] Magic byte mismatch for %s from user %s', ext, request.user)
            return JsonResponse({'error': 'File content does not match expected image format.'}, status=400)

        try:
            img = Image.open(file)
            img.verify()
            file.seek(0)
            img = Image.open(file)
            img.thumbnail((1920, 1920))
            img_format = img.format if img.format else "JPEG"
            temp = io.BytesIO()
            img.save(temp, format=img_format, optimize=True)
            temp.seek(0)
            file_path = default_storage.save(f"uploads/rich_content/{new_filename}", ContentFile(temp.read()))
        except Exception as e:
            logger.warning('[Upload] Invalid image file from %s: %s', request.user, e)
            return JsonResponse({'error': 'Uploaded file is corrupted or not a valid image.'}, status=400)
    else:
        # SVG or video: save directly
        file_path = default_storage.save(f"uploads/rich_content/{new_filename}", file)

    url = default_storage.url(file_path)
    return JsonResponse({'location': url})
