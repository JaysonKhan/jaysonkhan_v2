# Safe non-destructive migration: only AddField operations.
# Existing SiteSettings row values remain untouched — new fields get defaults.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_alter_sitesettings_about_description_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='experience_section_title',
            field=models.CharField(
                default='Experience',
                help_text='Experience section heading on homepage',
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='phone',
            field=models.CharField(
                blank=True, default='',
                help_text='Phone number (optional)',
                max_length=20,
            ),
        ),
    ]
