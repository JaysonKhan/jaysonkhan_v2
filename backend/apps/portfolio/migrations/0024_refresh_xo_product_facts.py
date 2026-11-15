"""Product counts re-checked 2026-11-15 (docs/archive/project-facts-2026-11.md).

apply_edtech_founder_copy never overwrites existing xo text (owner's Khorezm voice),
so the dated figures inside it are corrected here: numbers only, wording untouched.
"""
import json

from django.db import migrations

FACTS = (
    ("85k+", "167k+"),
    ("21k+", "39k+"),
    ("53k+", "54k+"),
    ("193 faol OTM", "208 faol OTM"),
    ("121 OTM", "126 OTM"),
)


def refresh_facts(apps, schema_editor):
    for app_label, model_name in (("core", "SiteSettings"), ("portfolio", "Experience")):
        model = apps.get_model(app_label, model_name)
        fields = [f.name for f in model._meta.concrete_fields
                  if f.get_internal_type() in ("CharField", "TextField", "JSONField")]
        for obj in model.objects.using(schema_editor.connection.alias).all():
            changed = []
            for name in fields:
                value = getattr(obj, name)
                if not value:
                    continue
                # JSON copy (FAQ, lists) is patched through its serialized form.
                text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
                new = text
                for old, fresh in FACTS:
                    new = new.replace(old, fresh)
                if new != text:
                    setattr(obj, name, new if isinstance(value, str) else json.loads(new))
                    changed.append(name)
            if changed:
                obj.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("portfolio", "0023_refresh_confirmed_career"), ("core", "0042_sitesettings_about_image_anime_and_more")]
    operations = [migrations.RunPython(refresh_facts, migrations.RunPython.noop)]
