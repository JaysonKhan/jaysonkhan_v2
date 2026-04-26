"""Aggressive Flutter→VibeCoder rebrand for fields whose admin-edited value
still contains 'Flutter' or 'Mobile Engineer'. Overwrites with the new VibeCoder
copy. The user has explicitly stopped Flutter work and wants the entire site
repositioned, so substring-match is intentional.

Idempotent: skips fields that don't contain Flutter (already migrated or were
never Flutter-related).
"""
from django.db import migrations


# field → new value (overwrites if old contains 'Flutter' or 'Mobile Engineer')
NEW_VALUES = {
    'site_title': "Jaysonkhan | VibeCoder · Build Studio",
    'site_tagline': "VibeCoder — shipping production web apps & Telegram bots via AI-augmented development.",
    'meta_description': (
        "Jaysonkhan — VibeCoder shipping production web apps & "
        "Telegram bots via AI-augmented development. Build Studio · Tashkent."
    ),
    'meta_keywords': "VibeCoder, Django, Python, Telegram bots, AI development, Claude Code, full stack, build studio, Tashkent",
    'hero_title': "I ship production web apps and Telegram bots.",
    'hero_subtitle': (
        "VibeCoder specializing in shipping production-grade web applications, "
        "Telegram bots, and AI-augmented systems. Built fast with Claude Code, "
        "built to last with Django."
    ),
    'about_description': (
        "Full-stack VibeCoder with 3+ years shipping production systems. "
        "I build web apps with Django, Telegram bots with Aiogram, and "
        "design systems with Tailwind — all augmented by Claude Code and a "
        "sane workflow. Background in mobile (Flutter, Android, iOS), but the "
        "studio's center of gravity has moved to web + bots + AI."
    ),
    'blog_page_subtitle': (
        "Notes on AI-augmented development, full-stack delivery, and "
        "shipping production systems that actually run."
    ),
    'contact_page_subtitle': (
        "Building a web app, Telegram bot, or AI-augmented system? "
        "Let's ship it together."
    ),
    'hero_eyebrow': "Personal · Build Studio · VibeCoder",
    'team_intro': (
        "A small studio of full-stack builders, designers, and operators. "
        "We ship production web apps, Telegram bots, and AI-augmented systems — "
        "using whatever tool fits the problem."
    ),
    'cta_description': (
        "Two slots opening for Q2 2026. Best fit: ambitious web apps, "
        "Telegram bot products, or AI-augmented systems with a 12+ week "
        "runway and a real user base in mind."
    ),
}

# Trigger rebrand if old value contains any of these substrings
TRIGGERS = ['Flutter', 'Mobile Engineer', 'mobile engineer', 'Mobile Developer',
            'mobile development', 'Android & iOS', 'Android and iOS',
            'BLoC', 'Dart Developer', 'flutter']


def fuzzy_rebrand(apps, schema_editor):
    SiteSettings = apps.get_model('core', 'SiteSettings')
    for row in SiteSettings.objects.all():
        changed = []
        for field, new in NEW_VALUES.items():
            old = getattr(row, field, '') or ''
            if any(t in old for t in TRIGGERS):
                setattr(row, field, new)
                changed.append(field)
        if changed:
            row.save(update_fields=changed)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0032_rebrand_flutter_to_vibecoder'),
    ]
    operations = [
        migrations.RunPython(fuzzy_rebrand, noop),
    ]
