"""Seed the IndexNow cron.

Adds (idempotently):
  - indexnow  (daily 05:47) — submits the sitemap URLs whose content changed
    since the last accepted submission to IndexNow (Bing/Yandex).

The schedule string is deliberately not one `cron_health_check` knows an
interval for: a daily job that has not had its first run yet must not be
paged as "overdue" every hour. A failed run is still alerted.
"""
from django.db import migrations


CRONS = [
    {
        'command': 'indexnow',
        'verbose_name': 'IndexNow',
        'description': (
            'Har kuni 05:47 da sitemap’dagi (statik sahifalar, loyihalar, blog — 4 til) '
            'kontenti o‘zgargan URL’larni IndexNow orqali Bing/Yandex’ga yuboradi. '
            'O‘zgarish bo‘lmasa so‘rov yuborilmaydi.'
        ),
        'schedule': '47 5 * * *',
        'category': 'seo',
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
        ('ops', '0005_indexnowurl'),
    ]
    operations = [migrations.RunPython(seed, unseed)]
