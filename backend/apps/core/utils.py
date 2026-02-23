import bleach

ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol',
    'strong', 'ul', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img', 'br',
    'hr', 'pre', 'div', 'span', 'iframe', 'table', 'thead', 'tbody', 'tr',
    'th', 'td', 'figure', 'figcaption', 'u', 's', 'sub', 'sup'
]

ALLOWED_ATTRIBUTES = {
    '*': ['class', 'style', 'title', 'dir'],
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'width', 'height', 'loading'],
    'iframe': ['src', 'width', 'height', 'frameborder', 'allow', 'allowfullscreen', 'title'],
    'table': ['border', 'cellpadding', 'cellspacing'],
}

ALLOWED_STYLES = [
    'color', 'font-family', 'font-size', 'font-weight', 'text-align',
    'text-decoration', 'background-color', 'margin', 'padding', 'width', 'height',
    'max-width', 'max-height', 'border', 'border-radius', 'display'
]

def sanitize_rich_text(text):
    if not text:
        return text
    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        styles=ALLOWED_STYLES,
        strip=True
    )
