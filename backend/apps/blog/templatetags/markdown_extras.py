"""
Custom template filter for safe Markdown rendering.

NOTE: This filter (render_markdown) is NOT currently used in any template.
blog_detail.html renders {{ post.content_rich|safe }} (TinyMCE HTML, bleach-sanitized on save).
This file is kept only because apps/core/tests.py imports and unit-tests it.
If Markdown authoring is added in future, wire it to a dedicated content_md field,
not the same field as TinyMCE (content_rich).

NOTE on ALLOWED_TAGS/ALLOWED_ATTRIBUTES vs core/utils.py:
The lists here are intentionally different from core/utils.py's bleach allowlist.
- This file's list is for Markdown output: adds del, ins, mark, abbr (valid Markdown
  output elements) and deliberately omits 'style' (safer for Markdown context).
- core/utils.py's list is for TinyMCE rich-text sanitization and allows 'style'.
Keep both lists in sync intentionally -- a security change to one does NOT auto-apply
to the other.
"""
import bleach
import markdown2
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Allowed HTML tags after Markdown conversion (safe subset).
# Intentionally differs from core/utils.py ALLOWED_TAGS -- see module docstring.
ALLOWED_TAGS = [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'br', 'hr',
    'strong', 'em', 'b', 'i', 'u', 's', 'del', 'ins', 'mark',
    'a', 'img',
    'ul', 'ol', 'li',
    'blockquote', 'pre', 'code',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'div', 'span',
    'sup', 'sub',
    'abbr',
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height', 'loading'],
    'abbr': ['title'],
    'td': ['align'],
    'th': ['align'],
    'code': ['class'],
    'pre': ['class'],
    'div': ['class'],
    'span': ['class'],
}

MARKDOWN_EXTRAS = [
    'fenced-code-blocks',
    'code-friendly',
    'tables',
    'footnotes',
    'header-ids',
    'strike',
    'task_list',
    'cuddled-lists',
    'target-blank-links',
]


@register.filter(name='render_markdown')
def render_markdown(value):
    """
    Convert Markdown text to sanitized HTML.

    1. Render Markdown → raw HTML via markdown2
    2. Sanitize via bleach (whitelist of tags + attributes)
    3. Mark as safe for Django templates
    """
    if not value:
        return ''

    # Step 1: Markdown → HTML
    raw_html = markdown2.markdown(value, extras=MARKDOWN_EXTRAS)

    # Step 2: Sanitize
    clean_html = bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )

    return mark_safe(clean_html)
