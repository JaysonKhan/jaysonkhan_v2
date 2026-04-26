from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        # Add 'xo' to Django's LANG_INFO so get_language_info('xo') and the
        # i18n template tags don't raise KeyError. Mutate the dict in place
        # rather than replacing it, so that module-level imports of
        # `LANG_INFO` (e.g. in trans_real.py) see the change.
        import django.conf.locale as _locale
        _locale.LANG_INFO['xo'] = {
            'bidi': False,
            'code': 'xo',
            'name': 'Khorezm Uzbek',
            'name_local': 'Xorazmcha',
        }
