from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('portfolio', '0005_skill_show_in_hero'),
    ]

    operations = [
        # Add is_bot field
        migrations.AddField(
            model_name='project',
            name='is_bot',
            field=models.BooleanField(
                default=False,
                help_text='Show in the Telegram Bot section (overrides platform for section display)',
            ),
        ),
        # Add web_page_url field
        migrations.AddField(
            model_name='project',
            name='web_page_url',
            field=models.URLField(
                blank=True,
                help_text='Web page / live URL — shown only for Web platform projects',
            ),
        ),
        # Add 'bot' to PLATFORM_CHOICES (Django tracks this via AlterField)
        migrations.AlterField(
            model_name='project',
            name='platform',
            field=models.CharField(
                choices=[
                    ('android', 'Android'),
                    ('ios', 'iOS'),
                    ('cross', 'Cross-platform (Android & iOS)'),
                    ('web', 'Web'),
                    ('bot', 'Telegram Bot'),
                ],
                default='cross',
                help_text='Target platform',
                max_length=10,
            ),
        ),
        # Remove live_url field
        migrations.RemoveField(
            model_name='project',
            name='live_url',
        ),
    ]
