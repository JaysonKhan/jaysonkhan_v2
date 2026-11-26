"""Package prices cover Polar's fee (tax is added on top at checkout): $6 / $17 / $45. Units are unchanged."""
from django.db import migrations

PRICES = {'starter': (500, 600), 'medium': (1500, 1700), 'large': (4000, 4500)}


def raise_prices(apps, schema_editor):
    Package = apps.get_model('livebridge', 'Package')
    for code, (_, new) in PRICES.items():
        Package.objects.filter(code=code).update(price_cents=new)


def restore_prices(apps, schema_editor):
    Package = apps.get_model('livebridge', 'Package')
    for code, (old, _) in PRICES.items():
        Package.objects.filter(code=code).update(price_cents=old)


class Migration(migrations.Migration):
    dependencies = [('livebridge', '0003_retired_refresh_tokens')]

    operations = [migrations.RunPython(raise_prices, restore_prices)]
