import logging
import os
import re
import uuid
import io

from django.http import JsonResponse, HttpResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.urls import reverse
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

# ── SVG sanitization ────────────────────────────────────────────────────────
# Tags and attributes that can execute JavaScript or load external resources.
_SVG_DANGEROUS_TAG_GROUP = r'(?:script|foreignObject|set|animate(?:Transform)?)'
_SVG_DANGEROUS_TAGS = re.compile(
    rf'<\s*{_SVG_DANGEROUS_TAG_GROUP}[^>]*>.*?</\s*{_SVG_DANGEROUS_TAG_GROUP}\s*>',
    re.IGNORECASE | re.DOTALL,
)
_SVG_DANGEROUS_TAG_SELF = re.compile(
    rf'<\s*{_SVG_DANGEROUS_TAG_GROUP}[^>]*/\s*>',
    re.IGNORECASE,
)
_SVG_EVENT_ATTRS = re.compile(
    r'\s+on\w+\s*=\s*["\'][^"\']*["\']',
    re.IGNORECASE,
)
_SVG_XLINK_HREF_JS = re.compile(
    r'(xlink:href|href)\s*=\s*["\'](?:\s*javascript\s*:)[^"\']*["\']',
    re.IGNORECASE,
)


def _sanitize_svg(raw_bytes: bytes) -> bytes:
    """Strip dangerous elements/attributes from SVG content.

    This is a defence-in-depth measure: the upload is staff-only, but
    SVGs are served to all visitors and can execute JS in the browser.
    """
    try:
        text = raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        raise ValueError('SVG file contains invalid UTF-8')

    text = _SVG_DANGEROUS_TAGS.sub('', text)
    text = _SVG_DANGEROUS_TAG_SELF.sub('', text)
    text = _SVG_EVENT_ATTRS.sub('', text)
    text = _SVG_XLINK_HREF_JS.sub('', text)
    return text.encode('utf-8')


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
    elif ext == '.svg':
        # SVG: sanitize to remove XSS vectors before saving
        raw = file.read()
        try:
            clean = _sanitize_svg(raw)
        except ValueError as e:
            logger.warning('[Upload] Invalid SVG from %s: %s', request.user, e)
            return JsonResponse({'error': str(e)}, status=400)
        file_path = default_storage.save(
            f"uploads/rich_content/{new_filename}", ContentFile(clean),
        )
    else:
        # Video: save directly
        file_path = default_storage.save(f"uploads/rich_content/{new_filename}", file)

    url = default_storage.url(file_path)
    return JsonResponse({'location': url})


# ── WakaTime Coding Activity ──────────────────────────────────────────────────

def wakatime_stats(request):
    """
    Proxy WakaTime stats API — returns last 7 days coding activity.
    API key stays server-side; frontend gets safe JSON.
    Cached for 2 hours.
    """
    from django.core.cache import cache
    from core.models import SiteSettings
    import urllib.request
    import json
    import base64

    cache_key = 'wakatime_stats_data'
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    try:
        settings_obj = SiteSettings.objects.first()
        api_key = getattr(settings_obj, 'wakatime_api_key', '') or ''
    except Exception:
        api_key = ''

    if not api_key:
        return JsonResponse({'error': 'No WakaTime API key configured'}, status=404)

    # WakaTime uses Basic auth with api_key as username, no password
    auth_header = 'Basic ' + base64.b64encode(api_key.encode()).decode()
    api_url = 'https://api.wakatime.com/api/v1/users/current/stats/last_7_days'

    try:
        req = urllib.request.Request(
            api_url,
            headers={
                'Authorization': auth_header,
                'User-Agent': 'Mozilla/5.0 (compatible; PortfolioBot/1.0)',
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        logger.warning('Failed to fetch WakaTime stats: %s', e)
        return JsonResponse({'error': 'Failed to fetch WakaTime data'}, status=502)

    data = raw.get('data', {})

    # Extract only the fields we need (no sensitive info)
    result = {
        'daily_average': data.get('human_readable_daily_average_including_other_language', ''),
        'total': data.get('human_readable_total_including_other_language', ''),
        'best_day': {
            'date': data.get('best_day', {}).get('date', ''),
            'text': data.get('best_day', {}).get('text', ''),
        } if data.get('best_day') else None,
        'languages': [
            {
                'name': lang.get('name', ''),
                'percent': round(lang.get('percent', 0), 1),
                'text': lang.get('text', ''),
            }
            for lang in (data.get('languages') or [])[:8]
        ],
        'editors': [
            {
                'name': ed.get('name', ''),
                'percent': round(ed.get('percent', 0), 1),
                'text': ed.get('text', ''),
            }
            for ed in (data.get('editors') or [])[:5]
        ],
        'operating_systems': [
            {
                'name': os_item.get('name', ''),
                'percent': round(os_item.get('percent', 0), 1),
            }
            for os_item in (data.get('operating_systems') or [])[:3]
        ],
        'categories': [
            {
                'name': cat.get('name', ''),
                'percent': round(cat.get('percent', 0), 1),
                'text': cat.get('text', ''),
            }
            for cat in (data.get('categories') or [])[:5]
        ],
    }

    # Cache for 2 hours
    cache.set(cache_key, result, 7200)

    return JsonResponse(result)


# ── GitHub Contribution Graph ──────────────────────────────────────────────────

def github_contributions(request):
    """
    Return the last ~1 year of GitHub contribution data as JSON.
    Scrapes the public contributions page (no API token required).
    Cached for 1 hour.
    """
    from django.core.cache import cache
    from core.models import SiteSettings
    import urllib.request

    cache_key = 'github_contributions_data'
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached, safe=False)

    try:
        settings_obj = SiteSettings.objects.first()
        github_url = getattr(settings_obj, 'github_url', '') or ''
    except Exception:
        github_url = ''

    if not github_url:
        return JsonResponse({'error': 'No GitHub URL configured'}, status=404)

    # Extract username from URL like https://github.com/username
    username = github_url.rstrip('/').split('/')[-1]
    if not username:
        return JsonResponse({'error': 'Could not extract GitHub username'}, status=400)

    contributions_url = f'https://github.com/users/{username}/contributions'
    try:
        req = urllib.request.Request(
            contributions_url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; PortfolioBot/1.0)'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8')
    except Exception as e:
        logger.warning('Failed to fetch GitHub contributions for %s: %s', username, e)
        return JsonResponse({'error': 'Failed to fetch contributions'}, status=502)

    # Parse contribution data from the SVG/HTML
    # Each cell: <td ... data-date="2025-03-01" data-level="2" ...>
    pattern = re.compile(
        r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="(\d)"'
    )
    contributions = []
    for match in pattern.finditer(html):
        contributions.append({
            'date': match.group(1),
            'level': int(match.group(2)),
        })

    if not contributions:
        return JsonResponse({'error': 'No contribution data found'}, status=404)

    # Sort by date
    contributions.sort(key=lambda x: x['date'])

    # Cache for 1 hour
    cache.set(cache_key, contributions, 3600)

    return JsonResponse(contributions, safe=False)


# ── robots.txt ─────────────────────────────────────────────────────────────────

def robots_txt(request):
    """Serve robots.txt with dynamic Sitemap URL."""
    sitemap_url = request.build_absolute_uri(
        reverse('django.contrib.sitemaps.views.sitemap')
    )
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        "Disallow: /api/\n"
        "Disallow: /auth/\n"
        "\n"
        f"Sitemap: {sitemap_url}\n"
    )
    return HttpResponse(content, content_type='text/plain')


# ── Health check ──────────────────────────────────────────────────────────────

def health_check(request):
    """
    Lightweight health check for monitoring and deploy verification.
    Checks: database connectivity, cache backend, migrations applied.
    """
    from django.db import connection
    from django.core.cache import cache

    health = {'status': 'ok'}

    # Database check
    try:
        connection.ensure_connection()
        health['database'] = 'ok'
    except Exception as e:
        health['database'] = f'error: {e}'
        health['status'] = 'degraded'

    # Cache check
    try:
        cache.set('_health_check', '1', 10)
        if cache.get('_health_check') == '1':
            health['cache'] = 'ok'
        else:
            health['cache'] = 'error: read-back mismatch'
            health['status'] = 'degraded'
    except Exception as e:
        health['cache'] = f'error: {e}'
        health['status'] = 'degraded'

    status_code = 200 if health['status'] == 'ok' else 503
    return JsonResponse(health, status=status_code)
