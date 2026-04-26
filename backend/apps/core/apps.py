from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        import sys
        sys.stderr.write("[CoreConfig.ready V2] Installing xo language patch\n")
        sys.stderr.flush()

        from django.templatetags import i18n as _i18n

        _xo_info = {
            'bidi': False,
            'code': 'xo',
            'name': 'Khorezm Uzbek',
            'name_local': 'Xorazmcha',
            'name_translated': 'Khorezm Uzbek',
        }

        # Wholesale replace render() on the node — match Django's exact signature.
        original_render = _i18n.GetLanguageInfoListNode.render

        def patched_render(self, context):
            sys.stderr.write("[V2 patched_render] called\n")
            sys.stderr.flush()
            langs = self.languages.resolve(context)
            results = []
            for lang in langs:
                code = lang[0] if (lang and len(lang[0]) > 1) else str(lang)
                if code == 'xo':
                    results.append(dict(_xo_info))
                else:
                    from django.utils import translation
                    results.append(translation.get_language_info(code))
            context[self.variable] = results
            return ""

        _i18n.GetLanguageInfoListNode.render = patched_render
        sys.stderr.write(f"[V2 ready] Patched render: {_i18n.GetLanguageInfoListNode.render.__name__}\n")
        sys.stderr.flush()
