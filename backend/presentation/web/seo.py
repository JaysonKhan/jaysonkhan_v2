"""Meta descriptions that do not come out too short.

Bing Webmaster flagged pages whose description was a 57–63 character
one-liner (prod sweep 2026-11-13: a blog teaser, the ru/en team intro). A
page's own teaser is kept as written when it is long enough; a short one is
extended with more of the same page, then with the site-wide description —
always text that already exists in the page's language, never new copy.
"""
import html
import re

from django.conf import settings
from django.utils.html import strip_tags
from django.utils.translation import get_language

META_DESC_MIN = 100  # shorter than this → extend (the flagged pages were under ~70; this leaves a margin)
META_DESC_MAX = 160  # an extended description never exceeds this

_BLOCK_END = re.compile(r'</(?:p|h[1-6]|li|blockquote|div|tr|figcaption|pre)>|<[bh]r\s*/?>', re.I)
_SENTENCE_END = re.compile(r'[.!?…](?=\s|$)')


def plain_text(rich):
    """Rich-text HTML → one line of text; block boundaries become spaces."""
    return ' '.join(html.unescape(strip_tags(_BLOCK_END.sub(' ', rich or ''))).split())


def translated(obj, field):
    """`field` in the active language, or '' when that column is empty or only
    repeats the xo text.

    The page itself then shows the xo fallback, but a description must not
    glue an English teaser to an Uzbek body.
    """
    lang = get_language()
    default = settings.MODELTRANSLATION_DEFAULT_LANGUAGE
    value = getattr(obj, f'{field}_{lang}', None) or ''
    if lang != default and value == (getattr(obj, f'{field}_{default}', None) or ''):
        return ''
    return value


def meta_description(*parts):
    """The first non-empty part, extended by the next ones while it is short."""
    parts = [' '.join(part.split()) for part in parts if part and part.strip()]
    if not parts:
        return ''
    text = parts[0]
    for extra in parts[1:]:
        if len(text) >= META_DESC_MIN:
            break
        if extra.startswith(text.rstrip(' .…')):  # the teaser is the opening of the body
            text = extra
        else:
            text = f'{text if text[-1] in ".!?…" else text + "."} {extra}'
    if len(text) <= META_DESC_MAX or text == parts[0]:
        return text
    # End on the last whole sentence that fits, else on a word.
    ends = [m.end() for m in _SENTENCE_END.finditer(text) if META_DESC_MIN <= m.end() <= META_DESC_MAX]
    if ends:
        return text[:ends[-1]]
    return text[:META_DESC_MAX - 1].rsplit(' ', 1)[0].rstrip(' ,;:—–-/·') + '…'
