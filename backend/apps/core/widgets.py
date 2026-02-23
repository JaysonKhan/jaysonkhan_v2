from django import forms

class RichTextWidget(forms.Textarea):
    def __init__(self, *args, **kwargs):
        attrs = kwargs.setdefault('attrs', {})
        attrs['class'] = attrs.get('class', '') + ' rich-text-editor'
        # Set large rows so the basic textarea is large until JS loads
        attrs['rows'] = 20
        super().__init__(*args, **kwargs)

    class Media:
        js = (
            'https://cdn.tiny.cloud/1/t6ix19p2zofps0gngjoxg1sznntgmy2eb7ebw03ed5d1b7a2/tinymce/6/tinymce.min.js',
            'core/js/rich_text_init.js',
        )
