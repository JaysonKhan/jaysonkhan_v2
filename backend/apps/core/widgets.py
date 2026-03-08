from django import forms


class RichTextWidget(forms.Textarea):
    """
    Textarea that activates TinyMCE 6 (self-hosted via cdnjs — no API key required).
    Dark oxide skin matches the Unfold admin theme.
    """

    def __init__(self, *args, **kwargs):
        attrs = kwargs.setdefault('attrs', {})
        attrs['class'] = attrs.get('class', '') + ' rich-text-editor'
        attrs['rows'] = 20  # Fallback height before JS loads
        super().__init__(*args, **kwargs)

    class Media:
        js = (
            # Self-hosted TinyMCE 6 — no API key, no domain restrictions.
            # Full bundle including all plugins and skins.
            'https://cdnjs.cloudflare.com/ajax/libs/tinymce/6.8.5/tinymce.min.js',
            'core/js/rich_text_init.js',
        )
