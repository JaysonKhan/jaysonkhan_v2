from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        import sys as __sys
        __sys.stderr.write("[CoreConfig.ready] Patching get_language_info for 'xo'\n")
        # Patch django.utils.translation.get_language_info to recognise our
        # custom 'xo' language code. Done in ready() so the patch runs AFTER
        # Django has finished loading translation internals — patching from
        # settings.py was unreliable because something else reset the attribute
        # later in worker init.
        from django.utils import translation as _t

        _xo_info = {
            'bidi': False,
            'code': 'xo',
            'name': 'Khorezm Uzbek',
            'name_local': 'Xorazmcha',
            'name_translated': 'Khorezm Uzbek',
        }
        _orig = _t.get_language_info

        def _patched(lang_code):
            import sys as ___sys
            ___sys.stderr.write(f"[patched-call] lang_code={lang_code!r} module_attr_id={id(_t.get_language_info)}\n")
            if lang_code == 'xo':
                return dict(_xo_info)
            return _orig(lang_code)

        _t.get_language_info = _patched
        import sys as __sys2
        __sys2.stderr.write(f"[CoreConfig.ready] After patch, _t.get_language_info id={id(_t.get_language_info)} name={_t.get_language_info.__name__}\n")

        # Also patch django.conf.locale.LANG_INFO in case anything iterates it.
        import django.conf.locale as _locale
        _locale.LANG_INFO['xo'] = {
            'bidi': False,
            'code': 'xo',
            'name': 'Khorezm Uzbek',
            'name_local': 'Xorazmcha',
        }
