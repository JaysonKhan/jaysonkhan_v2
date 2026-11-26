"""Seeds the three one-time packages (accounts design, "Packages"). Polar product ids are set in the admin."""
from django.db import migrations

PACKAGES = [
    ('starter', 500, 360_000, 1),
    ('medium', 1500, 1_200_000, 2),
    ('large', 4000, 3_600_000, 3),
]


def seed(apps, schema_editor):
    Package = apps.get_model('livebridge', 'Package')
    for code, price_cents, units, sort_order in PACKAGES:
        Package.objects.update_or_create(
            code=code, defaults={'price_cents': price_cents, 'units': units, 'sort_order': sort_order},
        )


def unseed(apps, schema_editor):
    apps.get_model('livebridge', 'Package').objects.filter(code__in=[p[0] for p in PACKAGES]).delete()


class Migration(migrations.Migration):
    dependencies = [('livebridge', '0001_initial')]

    operations = [migrations.RunPython(seed, unseed)]
