"""Rebrand SiteSettings from Flutter Mobile Engineer → VibeCoder.

Idempotent: only updates rows where the value still matches the OLD plain-text
default. Custom admin edits are preserved.
"""
from django.db import migrations


# Old default → new VibeCoder default (only updates exact matches)
OLD_TO_NEW = {
    'site_title': (
        "Jahongir Kuziboev | Flutter Mobile Engineer",
        "Jaysonkhan | VibeCoder · Build Studio",
    ),
    'site_tagline': (
        "Flutter Mobile Engineer — building high-quality Android & iOS apps.",
        "VibeCoder — shipping production web apps & Telegram bots via AI-augmented development.",
    ),
    'meta_description': (
        "Flutter Mobile Engineer with 2+ years of experience developing "
        "high-quality Android & iOS apps. Clean Architecture, BLoC, Dart.",
        "Jaysonkhan — VibeCoder shipping production web apps & "
        "Telegram bots via AI-augmented development. Build Studio · Tashkent.",
    ),
    'meta_keywords': (
        "Flutter, Dart, Mobile Developer, Android, iOS, BLoC, Clean Architecture, Portfolio",
        "VibeCoder, Django, Python, Telegram bots, AI development, Claude Code, full stack, build studio, Tashkent",
    ),
    'hero_title': (
        "I craft pixel-perfect mobile experiences.",
        "I ship production web apps and Telegram bots.",
    ),
    'hero_subtitle': (
        "Flutter Mobile Engineer specializing in building scalable, "
        "performance-oriented Android & iOS applications with Clean Architecture.",
        "VibeCoder specializing in shipping production-grade web applications, Telegram bots, "
        "and AI-augmented systems. Built fast with Claude Code, built to last with Django.",
    ),
    'about_description': (
        "Flutter Mobile Engineer with 2+ years of experience developing "
        "high-quality Android and iOS applications. Specialized in building "
        "scalable, maintainable, and performance-oriented mobile solutions "
        "using Clean Architecture and BLoC. Developed 15+ corporate mobile "
        "apps with complex animations, REST API integrations, and cross-platform "
        "adaptive user interfaces.",
        "Full-stack VibeCoder with 3+ years shipping production systems. "
        "I build web apps with Django, Telegram bots with Aiogram, and "
        "design systems with Tailwind — all augmented by Claude Code and a "
        "sane workflow. Background in mobile (Flutter, Android, iOS), but the "
        "studio's center of gravity has moved to web + bots + AI.",
    ),
    'blog_page_subtitle': (
        "Insights on mobile development, Flutter, and building production-ready apps.",
        "Notes on AI-augmented development, full-stack delivery, and shipping production systems that actually run.",
    ),
    'contact_page_subtitle': (
        "Have a mobile app idea or need a Flutter engineer? Drop me a message.",
        "Building a web app, Telegram bot, or AI-augmented system? Let's ship it together.",
    ),
    'hero_eyebrow': (
        "Personal · Build Studio · Mobile Engineering",
        "Personal · Build Studio · VibeCoder",
    ),
    'team_intro': (
        "A small studio of mobile engineers, designers, and operators. We combine technical execution, product thinking, and production experience to ship real apps for real users.",
        "A small studio of full-stack builders, designers, and operators. We ship production web apps, Telegram bots, and AI-augmented systems — using whatever tool fits the problem.",
    ),
    'cta_description': (
        "Two slots opening for Q2 2026. Best fit: ambitious mobile-first products with a 12+ week runway and a real user base in mind.",
        "Two slots opening for Q2 2026. Best fit: ambitious web apps, Telegram bot products, or AI-augmented systems with a 12+ week runway and a real user base in mind.",
    ),
}

# JSON list field rebrand: old ticker → new ticker (only if matches old)
OLD_TICKER = [
    "Flutter mobile engineering",
    "Production apps",
    "Fintech · Logistics · Consumer",
    "Tashkent — worldwide remote",
    "Built for scale, not for demos",
]
NEW_TICKER = [
    "VibeCoder",
    "AI-augmented development",
    "Web apps · Telegram bots · Full-stack",
    "Tashkent — worldwide remote",
    "Built for scale, not for demos",
]

OLD_PROCESS_STEP_3 = "End-to-end working features each week. You can run it on your phone from day 7."
NEW_PROCESS_STEP_3 = "End-to-end working features each week. Staging deploy from day 7, AI-augmented iteration."

OLD_PROCESS_STEP_4 = "Beta with real users, telemetry wired, rollout plan agreed. Then App Store + Play Store on the same day."
NEW_PROCESS_STEP_4 = "Beta with real users, telemetry wired, rollback plan agreed. Then production deploy with one command."


def rebrand(apps, schema_editor):
    SiteSettings = apps.get_model('core', 'SiteSettings')
    for row in SiteSettings.objects.all():
        changed_fields = []
        # Plain-string fields
        for field, (old, new) in OLD_TO_NEW.items():
            if getattr(row, field, '') == old:
                setattr(row, field, new)
                changed_fields.append(field)

        # Ticker JSON
        if row.ticker_items == OLD_TICKER:
            row.ticker_items = NEW_TICKER
            changed_fields.append('ticker_items')

        # Process steps JSON — update step 3 + 4 if descriptions match
        if row.process_steps:
            updated_steps = []
            steps_changed = False
            for s in row.process_steps:
                if isinstance(s, dict):
                    if s.get('description') == OLD_PROCESS_STEP_3:
                        s = {**s, 'description': NEW_PROCESS_STEP_3}
                        steps_changed = True
                    elif s.get('description') == OLD_PROCESS_STEP_4:
                        s = {**s, 'description': NEW_PROCESS_STEP_4}
                        steps_changed = True
                updated_steps.append(s)
            if steps_changed:
                row.process_steps = updated_steps
                changed_fields.append('process_steps')

        if changed_fields:
            row.save(update_fields=changed_fields)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0031_sitesettings_about_section_eyebrow_and_more'),
    ]
    operations = [
        migrations.RunPython(rebrand, noop),
    ]
