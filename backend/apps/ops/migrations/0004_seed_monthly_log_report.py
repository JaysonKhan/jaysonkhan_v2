"""Seed the monthly log-report cron.

Adds (idempotently):
  - monthly_log_report  (1st of month, 00:05) — parses django_errors.log +
    security.log, sends an HTML summary + gzipped archives to the Telegram
    owner, then truncates the live logs ("tozalab borish").
"""
from django.db import migrations


CRONS = [
    {
        'command': 'monthly_log_report',
        'verbose_name': 'Monthly Log Report',
        'description': (
            'Har oy boshida (1-kun 00:05) o‘tgan oy loglarini tahlil qiladi: '
            '4xx/5xx, real server xatolari, bloklangan skanerlar — Telegram’ga '
            'xulosa + gzip arxiv yuboradi, so‘ng loglarni tozalaydi.'
        ),
        'schedule': '5 0 1 * *',
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
        ('ops', '0003_seed_more_crons'),
    ]
    operations = [migrations.RunPython(seed, unseed)]
