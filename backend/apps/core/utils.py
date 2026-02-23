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

try:
    from bleach.css_sanitizer import CSSSanitizer
    css_sanitizer = CSSSanitizer(allowed_css_properties=ALLOWED_STYLES)
except ImportError:
    css_sanitizer = None

def sanitize_rich_text(text):
    if not text:
        return text
        
    kwargs = {
        'tags': ALLOWED_TAGS,
        'attributes': ALLOWED_ATTRIBUTES,
        'strip': True
    }
    
    if css_sanitizer:
        kwargs['css_sanitizer'] = css_sanitizer
    else:
        # Older bleach uses 'styles'
        # To avoid error in older versions or new version without css_sanitizer,
        # we try using 'styles' if it doesn't raise TypeError, 
        # but to be safe we just pass 'styles' only if bleach version < 6
        if int(bleach.__version__.split('.')[0]) < 6:
            kwargs['styles'] = ALLOWED_STYLES

    return bleach.clean(text, **kwargs)
