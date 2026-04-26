from django.apps import AppConfig


class _LangInfoDict(dict):
    """Dict subclass that auto-resolves 'xo' to our Khorezm metadata.

    Works regardless of which module holds a reference to the original dict —
    every lookup goes through __missing__ when the key is absent, including
    the module-level `from django.conf.locale import LANG_INFO` import in
    trans_real.py and the function-local import in translation/__init__.py.
    """

    _XO = {
        'bidi': False,
        'code': 'xo',
        'name': 'Khorezm Uzbek',
        'name_local': 'Xorazmcha',
    }

    def __missing__(self, key):
        if key == 'xo':
            return dict(self._XO)
        raise KeyError(key)


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        # 'xo' isn't in Django's built-in LANG_INFO. Replace the dict with
        # one that auto-resolves 'xo' on missing-key access. Done via __missing__
        # rather than mutation because some module-level references in Django
        # internals hold a copy of the original dict.
        import django.conf.locale as _locale
        from django.utils.translation import trans_real as _trans_real

        if not isinstance(_locale.LANG_INFO, _LangInfoDict):
            new = _LangInfoDict(_locale.LANG_INFO)
            _locale.LANG_INFO = new
            _trans_real.LANG_INFO = new
            import sys as __sys
            __sys.stderr.write(f"[ready] After replace: locale.LANG_INFO id={id(_locale.LANG_INFO)} type={type(_locale.LANG_INFO).__name__}\n")

        # Wrap get_language_info to log at request time which dict is seen.
        from django.utils import translation as _t
        _orig_gli = _t.get_language_info
        def _logging_gli(lang_code):
            import sys as ___s
            import django.conf.locale as ___L
            ___s.stderr.write(f"[gli-call] {lang_code!r} locale.LANG_INFO id={id(___L.LANG_INFO)} type={type(___L.LANG_INFO).__name__} has_xo={('xo' in ___L.LANG_INFO)}\n")
            return _orig_gli(lang_code)
        _t.get_language_info = _logging_gli
