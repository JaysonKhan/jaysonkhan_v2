"""Rename 'rektor' and 'ovoz' service values to 'talabaovozi' in EntitySource."""

from django.db import migrations, models


def rename_services(apps, schema_editor):
    EntitySource = apps.get_model('telegram', 'EntitySource')
    # Merge both rektor and ovoz into talabaovozi
    EntitySource.objects.filter(service='rektor').update(service='talabaovozi')
    EntitySource.objects.filter(service='ovoz').update(service='talabaovozi')


def reverse_rename(apps, schema_editor):
    EntitySource = apps.get_model('telegram', 'EntitySource')
    EntitySource.objects.filter(service='talabaovozi').update(service='rektor')


class Migration(migrations.Migration):

    dependencies = [
        ('telegram', '0004_telegramsession_api_hash_telegramsession_api_id_and_more'),
    ]

    operations = [
        migrations.RunPython(rename_services, reverse_rename),
        migrations.AlterField(
            model_name='entitysource',
            name='service',
            field=models.CharField(
                choices=[
                    ('site', 'Website (jaysonkhan.com)'),
                    ('osint', 'OSINT'),
                    ('talabaovozi', 'TalabaOvozi'),
                ],
                max_length=20,
            ),
        ),
    ]
