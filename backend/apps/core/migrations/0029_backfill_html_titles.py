"""Backfill HTML titles for SiteSettings rows that still have the old plain-text defaults.

Only updates rows where the value matches the previous plain-text default exactly,
so any admin-edited custom values are preserved.
"""
from django.db import migrations


OLD_TO_NEW = {
    'metrics_title': (
        'A track record, measured.',
        'A track record,<br><em style="font-weight: 300;">measured.</em>',
    ),
    'process_title': (
        'Five steps, no surprises.',
        'Five steps,<br><em style="font-weight: 300;">no surprises.</em>',
    ),
    'team_values_title': (
        'How we think.',
        'How we<br>think.',
    ),
    'cta_title_pre': (
        'Bring the brief.',
        'Bring the<br>brief.',
    ),
}


def backfill(apps, schema_editor):
    SiteSettings = apps.get_model('core', 'SiteSettings')
    for row in SiteSettings.objects.all():
        changed = False
        for field, (old, new) in OLD_TO_NEW.items():
            if getattr(row, field, '') == old:
                setattr(row, field, new)
                changed = True
        if changed:
            row.save(update_fields=list(OLD_TO_NEW.keys()))


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0028_alter_sitesettings_cta_title_pre_and_more'),
    ]
    operations = [
        migrations.RunPython(backfill, noop),
    ]
