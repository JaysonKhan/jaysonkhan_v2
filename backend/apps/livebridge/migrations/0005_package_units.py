"""Fewer minutes in the smaller packages: Starter 45 min, Medium 190 min; Large stays 600 min (6000 units = 1 minute)."""
from django.db import migrations

UNITS = {'starter': (360_000, 270_000), 'medium': (1_200_000, 1_140_000)}


def set_units(apps, schema_editor):
    Package = apps.get_model('livebridge', 'Package')
    for code, (_, new) in UNITS.items():
        Package.objects.filter(code=code).update(units=new)


def restore_units(apps, schema_editor):
    Package = apps.get_model('livebridge', 'Package')
    for code, (old, _) in UNITS.items():
        Package.objects.filter(code=code).update(units=old)


class Migration(migrations.Migration):
    dependencies = [('livebridge', '0004_package_prices')]

    operations = [migrations.RunPython(set_units, restore_units)]
