"""Seed managed crons for the expanded server-monitor pipeline.

Adds (idempotently):
  - service_health_check  (every 5 min)  — per-service state change alerts
  - cron_health_check     (hourly)        — failed + overdue jobs alert
  - server_health_report  (daily 09:00)   — full daily report

Existing CPU alert seeded in 0002 is left untouched.
"""
from django.db import migrations


CRONS = [
    {
        'command': 'service_health_check',
        'verbose_name': 'Service Health Check',
        'description': (
            'Monitored servislar holatini har 5 daqiqada tekshiradi. '
            'Holat o‘zgarganda Telegram’ga ogohlantirish yuboradi.'
        ),
        'schedule': '*/5 * * * *',
        'category': 'monitor',
        'enabled': True,
    },
    {
        'command': 'cron_health_check',
        'verbose_name': 'Cron Health Check',
        'description': (
            'Oxirgi 1 soat ichidagi muvaffaqiyatsiz CronRun yozuvlarini va '
            'overdue (kechikkan) managed cronlarni tekshiradi va Telegram’ga '
            'umumiy xulosa yuboradi.'
        ),
        'schedule': '0 * * * *',
        'category': 'monitor',
        'enabled': True,
    },
    {
        'command': 'server_health_report',
        'verbose_name': 'Daily Health Report',
        'description': (
            'Kunlik to‘liq server hisoboti: CPU, RAM, disk, '
            'guruhlangan servislar holati, 24-soatlik restart va cron xulosasi.'
        ),
        'schedule': '0 9 * * *',
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
        ('ops', '0002_seed_managed_crons'),
    ]
    operations = [migrations.RunPython(seed, unseed)]
