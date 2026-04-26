"""Idempotent seed translations for Skill, Project, Experience, TeamMember.

Initial pass — mirrors existing xo content into uz/ru/en where empty,
plus hand-translated copy for non-test rows. User will edit later via admin.
Skips any row whose target column is already non-empty (preserves admin edits).
"""
from django.db import migrations


# Most skill names are proper nouns / brand names — same across all 4 langs.
# Only "Architecture" gets a translated form per language.
SKILL_TRANSLATIONS = {
    "Architecture": {
        "xo": "Arxitektura",
        "uz": "Arxitektura",
        "ru": "Архитектура",
        "en": "Architecture",
    },
    "Clean Architecture": {
        "xo": "Clean Architecture",
        "uz": "Clean Architecture",
        "ru": "Clean Architecture",
        "en": "Clean Architecture",
    },
    "Pentesting": {
        "xo": "Pentesting",
        "uz": "Pentesting",
        "ru": "Пентестинг",
        "en": "Pentesting",
    },
}


PROJECT_TRANSLATIONS = {
    # key = title_xo (existing canonical), values = per-lang dict of fields
    "My Portfolio": {
        "title": {
            "xo": "Shaxsiy portfolio",
            "uz": "Shaxsiy portfolio",
            "ru": "Личное портфолио",
            "en": "Personal Portfolio",
        },
        "short_description": {
            "xo": "Shaxsiy portfolio web sayti",
            "uz": "Shaxsiy portfolio web sayti",
            "ru": "Личный портфолио-сайт",
            "en": "Personal portfolio website",
        },
    },
    "Smart Home App": {
        "title": {
            "xo": "Smart Home App",
            "uz": "Smart Home App",
            "ru": "Smart Home App",
            "en": "Smart Home App",
        },
    },
    "E-commerce Platform": {
        "title": {
            "xo": "E-commerce Platform",
            "uz": "E-commerce Platform",
            "ru": "E-commerce Platform",
            "en": "E-commerce Platform",
        },
    },
}


def _set_if_empty(obj, attr, value):
    """Only assign when the target column is empty/None — preserve admin edits."""
    if not getattr(obj, attr, None):
        setattr(obj, attr, value)
        return True
    return False


def seed_translations(apps, schema_editor):
    Skill = apps.get_model("portfolio", "Skill")
    Project = apps.get_model("portfolio", "Project")

    # ── Skills: hand-translated where needed; otherwise mirror xo across langs ─
    for s in Skill.objects.all():
        canonical = s.name_xo or s.name or ""
        if not canonical:
            continue
        translations = SKILL_TRANSLATIONS.get(canonical)
        if translations is None:
            # Proper noun / brand — same in all langs.
            translations = {lang: canonical for lang in ("xo", "uz", "ru", "en")}
        changed = False
        for lang, value in translations.items():
            changed |= _set_if_empty(s, f"name_{lang}", value)
        if changed:
            s.save(update_fields=[f"name_{lang}" for lang in ("xo", "uz", "ru", "en")])

    # ── Projects: hand-translated for visible non-test projects ───────────────
    for p in Project.objects.all():
        canonical = p.title_xo or p.title or ""
        cfg = PROJECT_TRANSLATIONS.get(canonical)
        if cfg is None:
            # No hand translation — at minimum, mirror xo title across other langs
            # so language switcher doesn't show empty titles.
            for lang in ("uz", "ru", "en"):
                _set_if_empty(p, f"title_{lang}", canonical)
        else:
            for field, by_lang in cfg.items():
                for lang, value in by_lang.items():
                    _set_if_empty(p, f"{field}_{lang}", value)
        # Mirror short_description for projects without a hand translation
        if p.short_description_xo:
            for lang in ("uz", "ru", "en"):
                _set_if_empty(p, f"short_description_{lang}", p.short_description_xo)
        # Mirror description_rich + case_study_* into other langs (initial pass —
        # user will edit later). For richer fields we copy xo verbatim so the page
        # never renders empty when switching language.
        for src in ("description_rich", "case_study_challenge",
                    "case_study_solution", "case_study_results"):
            xo_val = getattr(p, f"{src}_xo", None) or getattr(p, src, None) or ""
            if not xo_val:
                continue
            for lang in ("uz", "ru", "en"):
                _set_if_empty(p, f"{src}_{lang}", xo_val)
        p.save()


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0016_experience_company_en_experience_company_ru_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_translations, reverse_noop),
    ]
