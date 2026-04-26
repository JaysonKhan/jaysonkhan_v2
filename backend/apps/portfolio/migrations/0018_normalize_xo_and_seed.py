"""Prod-aware fix: normalize xo + seed mirroring for portfolio models.

Same recovery logic as blog/0008 — see that migration's docstring.
"""
from django.db import migrations


SKILL_TRANSLATIONS = {
    "Architecture": {
        "xo": "Arxitektura", "uz": "Arxitektura",
        "ru": "Архитектура", "en": "Architecture",
    },
    "Pentesting": {
        "xo": "Pentesting", "uz": "Pentesting",
        "ru": "Пентестинг", "en": "Pentesting",
    },
}


# Hand translations keyed by canonical xo title (proper-noun project names
# pass through as-is via the fallback mirroring in `fix_translations`).
PROJECT_TRANSLATIONS_BY_TITLE = {
    "My Portfolio": {
        "title": {
            "xo": "Shaxsiy portfolio", "uz": "Shaxsiy portfolio",
            "ru": "Личное портфолио", "en": "Personal Portfolio",
        },
        "short_description": {
            "xo": "Shaxsiy portfolio web sayti",
            "uz": "Shaxsiy portfolio web sayti",
            "ru": "Личный портфолио-сайт",
            "en": "Personal portfolio website",
        },
    },
}


LANGS = ("xo", "uz", "ru", "en")
ALT_LANGS = ("uz", "ru", "en")


def _normalize_xo(obj, fields):
    for f in fields:
        if getattr(obj, f"{f}_xo", None):
            continue
        candidate = None
        for alt in ALT_LANGS:
            v = getattr(obj, f"{f}_{alt}", None)
            if v:
                candidate = v
                break
        if not candidate:
            candidate = getattr(obj, f, None)
        if candidate:
            setattr(obj, f"{f}_xo", candidate)


def _apply_translations(obj, by_field_lang):
    for field, by_lang in by_field_lang.items():
        xo_val = getattr(obj, f"{field}_xo", None) or ""
        for lang, value in by_lang.items():
            attr = f"{field}_{lang}"
            cur = getattr(obj, attr, None) or ""
            if not cur or cur == xo_val:
                setattr(obj, attr, value)


def _mirror_xo_to_empty(obj, fields):
    for f in fields:
        xo_val = getattr(obj, f"{f}_xo", None) or ""
        if not xo_val:
            continue
        for lang in ALT_LANGS:
            attr = f"{f}_{lang}"
            if not getattr(obj, attr, None):
                setattr(obj, attr, xo_val)


def fix_translations(apps, schema_editor):
    Skill = apps.get_model("portfolio", "Skill")
    Project = apps.get_model("portfolio", "Project")
    Experience = apps.get_model("portfolio", "Experience")
    TeamMember = apps.get_model("portfolio", "TeamMember")

    # ── Skills ────────────────────────────────────────────────────────────────
    for s in Skill.objects.all():
        _normalize_xo(s, ["name"])
        canonical = s.name_xo or s.name or ""
        translations = SKILL_TRANSLATIONS.get(canonical) or {
            lang: canonical for lang in LANGS
        }
        _apply_translations(s, {"name": translations})
        _mirror_xo_to_empty(s, ["name"])
        s.save()

    # ── Projects ──────────────────────────────────────────────────────────────
    project_fields = (
        "title", "short_description", "description_rich",
        "case_study_challenge", "case_study_solution", "case_study_results",
    )
    for p in Project.objects.all():
        _normalize_xo(p, list(project_fields))
        canonical = p.title_xo or p.title or ""
        cfg = PROJECT_TRANSLATIONS_BY_TITLE.get(canonical)
        if cfg:
            _apply_translations(p, cfg)
        _mirror_xo_to_empty(p, list(project_fields))
        p.save()

    # ── Experience / TeamMember (rare on prod, just normalize+mirror) ─────────
    for e in Experience.objects.all():
        _normalize_xo(e, ["company", "position", "description", "location"])
        _mirror_xo_to_empty(e, ["company", "position", "description", "location"])
        e.save()

    for t in TeamMember.objects.all():
        _normalize_xo(t, ["name", "role", "bio", "quote", "skills"])
        _mirror_xo_to_empty(t, ["name", "role", "bio", "quote", "skills"])
        t.save()


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0017_seed_translations"),
    ]

    operations = [
        migrations.RunPython(fix_translations, reverse_noop),
    ]
