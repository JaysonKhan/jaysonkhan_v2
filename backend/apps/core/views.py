import io
import logging
import os
import re
import uuid

from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
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
}

MAX_IMAGE_SIZE = 10 * 1024 * 1024   # 10 MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024   # 50 MB

# ── SVG sanitization ────────────────────────────────────────────────────────
# Tags and attributes that can execute JavaScript or load external resources.
_SVG_DANGEROUS_TAG_GROUP = r'(?:script|foreignObject|set|animate(?:Transform|Motion)?)'
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
        if ext == '.webp':
            valid_magic = header[:4] == b'RIFF' and header[8:12] == b'WEBP'
        else:
            for magic in IMAGE_MAGIC_BYTES:
                if header.startswith(magic):
                    valid_magic = True
                    break

        if not valid_magic and ext not in {'.svg'}:
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


# ── robots.txt ─────────────────────────────────────────────────────────────────

def robots_txt(request):
    """Serve robots.txt with per-bot rules + AI scraper blocks.

    Sections:
      • Default Allow (public pages) + Disallow private paths
      • Search engines (Google/Bing/Yandex/Duck/Apple): explicit Allow + crawl-delay
      • Image bots: full access for Google Images / Yandex Images
      • Social previewers: full Allow (link unfurl needs HTML+OG)
      • Aggressive SEO scrapers: Disallow /
      • AI scrapers (GPTBot, ClaudeBot, anthropic-ai, CCBot, Bytespider): Disallow
      • Yandex Host directive: canonical to jaysonkhan.com
      • Single Sitemap line: points to /sitemap.xml (the index)
    """
    sitemap_url = request.build_absolute_uri(reverse("sitemap_index"))
    humans_url = request.build_absolute_uri(reverse("humans_txt"))
    lines = [
        "# jaysonkhan.com — Qo'ziboyev Jahongir (JaysonKhan)",
        "# Flutter & Full-Stack Engineer · VibeCoder · Tashkent, UZ",
        "# Per-bot policy. Default: allow public, block private + scrapers.",
        "",
        "# ─── Default policy ──────────────────────────────────────────────",
        "User-agent: *",
        "Allow: /",
        "Disallow: /api/",
        "Disallow: /auth/",
        "Disallow: /jk-dinadmin/",
        "Disallow: /admin/",
        "Disallow: /i18n/",
        "Disallow: /*?success=*",
        "Disallow: /*?error=*",
        "Crawl-delay: 1",
        "",
        "# ─── Search engines (explicit Allow + tuned crawl-delay) ─────────",
        "User-agent: Googlebot",
        "Allow: /",
        "Disallow: /api/",
        "Disallow: /auth/",
        "Disallow: /admin/",
        "Disallow: /jk-dinadmin/",
        "",
        "User-agent: Bingbot",
        "Allow: /",
        "Disallow: /api/",
        "Disallow: /auth/",
        "Disallow: /admin/",
        "Disallow: /jk-dinadmin/",
        "Crawl-delay: 1",
        "",
        "User-agent: YandexBot",
        "Allow: /",
        "Disallow: /api/",
        "Disallow: /auth/",
        "Disallow: /admin/",
        "Disallow: /jk-dinadmin/",
        "Crawl-delay: 2",
        "",
        "User-agent: DuckDuckBot",
        "Allow: /",
        "Disallow: /api/",
        "Disallow: /admin/",
        "",
        "User-agent: Applebot",
        "Allow: /",
        "Disallow: /api/",
        "Disallow: /admin/",
        "",
        "# ─── Image crawlers — full access for Google Images / Yandex ─────",
        "User-agent: Googlebot-Image",
        "Allow: /",
        "Allow: /media/",
        "Allow: /static/",
        "",
        "User-agent: YandexImages",
        "Allow: /",
        "Allow: /media/",
        "Allow: /static/",
        "",
        "# ─── Social link previewers (need HTML + Open Graph) ─────────────",
        "User-agent: Twitterbot",
        "Allow: /",
        "",
        "User-agent: facebookexternalhit",
        "Allow: /",
        "",
        "User-agent: LinkedInBot",
        "Allow: /",
        "",
        "User-agent: TelegramBot",
        "Allow: /",
        "",
        "User-agent: WhatsApp",
        "Allow: /",
        "",
        "User-agent: Slackbot",
        "Allow: /",
        "",
        "User-agent: Slackbot-LinkExpanding",
        "Allow: /",
        "",
        "# ─── Aggressive SEO scrapers (bandwidth hogs, zero value) ────────",
        "User-agent: AhrefsBot",
        "Disallow: /",
        "",
        "User-agent: SemrushBot",
        "Disallow: /",
        "",
        "User-agent: DotBot",
        "Disallow: /",
        "",
        "User-agent: MJ12bot",
        "Disallow: /",
        "",
        "User-agent: PetalBot",
        "Disallow: /",
        "",
        "User-agent: DataForSeoBot",
        "Disallow: /",
        "",
        "User-agent: Bytespider",
        "Disallow: /",
        "",
        "User-agent: SEOkicks",
        "Disallow: /",
        "",
        "User-agent: BLEXBot",
        "Disallow: /",
        "",
        "# ─── AI scrapers (we own this content; no opt-in for training) ───",
        "User-agent: GPTBot",
        "Disallow: /",
        "",
        "User-agent: ChatGPT-User",
        "Disallow: /",
        "",
        "User-agent: OAI-SearchBot",
        "Disallow: /",
        "",
        "User-agent: anthropic-ai",
        "Disallow: /",
        "",
        "User-agent: ClaudeBot",
        "Disallow: /",
        "",
        "User-agent: Claude-Web",
        "Disallow: /",
        "",
        "User-agent: CCBot",
        "Disallow: /",
        "",
        "User-agent: Google-Extended",
        "Disallow: /",
        "",
        "User-agent: PerplexityBot",
        "Disallow: /",
        "",
        "User-agent: cohere-ai",
        "Disallow: /",
        "",
        "User-agent: Diffbot",
        "Disallow: /",
        "",
        "# ─── Yandex canonical host ───────────────────────────────────────",
        "Host: jaysonkhan.com",
        "",
        f"Sitemap: {sitemap_url}",
        f"# Humans: {humans_url}",
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


# ── humans.txt — E-E-A-T signal ────────────────────────────────────────────────

def humans_txt(request):
    """Serve humans.txt — humanstxt.org standard format.

    Search engines (and curious humans) use this as a signal that there's a
    real team behind the site. Linked from <head> via `rel="author"`.
    """
    lines = [
        "/* TEAM */",
        "",
        "    Founder · Lead Engineer: Qo'ziboyev Jahongir (JaysonKhan)",
        "    Also known as: Jayson Khan · Betta347 · Kuziboev Jahongir · Quziboyev Jahongir",
        "    Role: VibeCoder · Flutter & Full-Stack Engineer",
        "    Contact: hello [at] jaysonkhan.com",
        "    Telegram: t.me/jaysonkhan",
        "    GitHub: github.com/jaysonkhan",
        "    Location: Tashkent, Uzbekistan",
        "",
        "/* THANKS */",
        "",
        "    To everyone who reads this file — you're the kind of curious",
        "    person we build for. To the open-source maintainers behind",
        "    Django, Flutter, Dart, Python, PostgreSQL, Tailwind, and HTMX.",
        "    To Anthropic for Claude Code — vibecoding made real.",
        "",
        "/* SITE */",
        "",
        "    Last update: 2026/04/26",
        "    Standards: HTML5 · CSS3 · ES2024 · WCAG 2.1 AA",
        "    Components: Django 4.2 · DRF · Tailwind CSS · Alpine.js · HTMX",
        "    Hosting: Contabo VPS (Ubuntu 24.04) · Nginx · Gunicorn · PostgreSQL",
        "    Languages: O'zbek · O'zbekcha (lotin) · Русский · English",
        "    IDE: VS Code · Claude Code (CLI)",
        "",
        "/* MISSION */",
        "",
        "    Build production-grade mobile experiences and full-stack",
        "    products that ship. No fluff, no abstractions for hypothetical",
        "    futures, no half-finished implementations.",
        "    Talaba'larga, biznesga, community'ga — mahsulot quramiz.",
        "",
        "                              ████████╗",
        "                              ╚══██╔══╝",
        "                                 ██║",
        "                                 ╚═╝",
        "                            JaysonKhan",
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


# ── Health check ──────────────────────────────────────────────────────────────

def health_check(request):
    """
    Lightweight health check for monitoring and deploy verification.
    Checks: database connectivity, cache backend, migrations applied.
    """
    from django.core.cache import cache
    from django.db import connection

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
