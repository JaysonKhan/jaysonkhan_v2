from django.apps import AppConfig


_XO_LANG_INFO = {
    'bidi': False,
    'code': 'xo',
    'name': 'Khorezm Uzbek',
    'name_local': 'Xorazmcha',
    'name_translated': 'Khorezm Uzbek',
}


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        # Override Django's i18n template-tag node so that 'xo' resolves to
        # our Khorezm metadata instead of raising KeyError. We patch the
        # static method on the Node class because patching either the
        # `LANG_INFO` dict or `translation.get_language_info` from settings
        # or ready() didn't survive worker init for reasons that aren't
        # worth chasing further — this is the path the actual call takes
        # at template-render time, so a class-level override is bulletproof.
        from django.templatetags import i18n as _i18n
        from django.utils import translation as _t

        _orig_static = _i18n.GetLanguageInfoListNode.get_language_info

        @staticmethod
        def _xo_aware_get_language_info(language):
            code = language[0] if (language and len(language[0]) > 1) else str(language)
            if code == 'xo':
                return dict(_XO_LANG_INFO)
            return _orig_static(language)

        _i18n.GetLanguageInfoListNode.get_language_info = _xo_aware_get_language_info

        # Same fix for the single-language template filter helpers.
        _orig_lookup = _t.get_language_info

        def _xo_aware_translation_get_language_info(lang_code):
            if lang_code == 'xo':
                return dict(_XO_LANG_INFO)
            return _orig_lookup(lang_code)

        _t.get_language_info = _xo_aware_translation_get_language_info
