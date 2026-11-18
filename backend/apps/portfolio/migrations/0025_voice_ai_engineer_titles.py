"""Voice AI Engineer repositioning (owner's request, 2026-11-18).

apply_edtech_founder_copy never overwrites existing xo text (owner's Khorezm voice),
so the old role titles inside it are swapped here: role phrases and Experience
titles only, the surrounding dialect wording stays untouched.
"""
import json

from django.db import migrations

# Substrings inside SiteSettings copy (site title, meta, hero, about, FAQ).
PHRASES = (
    ("AI dasturchi, mobil dasturchi, full stack dasturchi, Flutter dasturchi",
     "Voice AI Engineer, ovozli AI, AI dasturchi, LLM integratsiya, Python dasturchi"),
    ("AI, mobil va full-stack dasturchi", "Voice AI Engineer"),
    ("AI · Mobil · Full-stack dasturchi", "Voice AI Engineer"),
    ("AI va mobil dasturchi", "Voice AI Engineer"),
)

# Whole Experience titles (exact match only, so free-form titles are never cut up).
TITLES = {
    "Mobile Developer": "Voice AI Engineer",
    "Founder & AI EdTech Specialist": "Founder & AI Engineer",
    "Software Engineer — Flutter / Fintech": "Software Engineer — Fintech",
    "Flutter Mobile Engineer": "Software Engineer",
}


def _text_fields(model):
    return [f.name for f in model._meta.concrete_fields
            if f.get_internal_type() in ("CharField", "TextField", "JSONField")]


def refresh_titles(apps, schema_editor):
    alias = schema_editor.connection.alias

    settings_model = apps.get_model("core", "SiteSettings")
    fields = _text_fields(settings_model)
    for obj in settings_model.objects.using(alias).all():
        changed = []
        for name in fields:
            value = getattr(obj, name)
            if not value:
                continue
            # JSON copy (FAQ, lists) is patched through its serialized form.
            text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            new = text
            for old, fresh in PHRASES:
                new = new.replace(old, fresh)
            if new != text:
                setattr(obj, name, new if isinstance(value, str) else json.loads(new))
                changed.append(name)
        if changed:
            obj.save(update_fields=changed)

    experience_model = apps.get_model("portfolio", "Experience")
    positions = [name for name in _text_fields(experience_model) if name.startswith("position")]
    for obj in experience_model.objects.using(alias).all():
        # Read every column first: with translated fields, writing one column can
        # change what the base `position` attribute returns.
        fresh = {name: TITLES[getattr(obj, name)] for name in positions if getattr(obj, name) in TITLES}
        for name, value in fresh.items():
            setattr(obj, name, value)
        if fresh:
            obj.save(update_fields=list(fresh))


class Migration(migrations.Migration):
    dependencies = [("portfolio", "0024_refresh_xo_product_facts")]
    operations = [migrations.RunPython(refresh_titles, migrations.RunPython.noop)]
