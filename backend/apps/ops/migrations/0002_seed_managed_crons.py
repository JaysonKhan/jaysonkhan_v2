"""Seed initial ManagedCron entries for jaysonkhan server crons."""
from django.db import migrations


CRONS = [
    {
        'command': 'check_cpu_alert',
        'verbose_name': 'CPU Alert Monitor',
        'description': 'Server CPU yuk darajasini tekshiradi va Telegram\'ga ogohlantirish yuboradi.',
        'schedule': '*/10 * * * *',
        'category': 'monitor',
        'enabled': True,
    },
]


def seed(apps, schema_editor):
    ManagedCron = apps.get_model('ops', 'ManagedCron')
    for data in CRONS:
        ManagedCron.objects.update_or_create(
            command=data['command'],
            defaults={k: v for k, v in data.items() if k != 'command'},
        )


def unseed(apps, schema_editor):
    ManagedCron = apps.get_model('ops', 'ManagedCron')
    ManagedCron.objects.filter(command__in=[c['command'] for c in CRONS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('ops', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]
