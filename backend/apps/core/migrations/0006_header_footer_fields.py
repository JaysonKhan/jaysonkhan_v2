# Generated manually — non-destructive AddField migration for header/footer fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_alter_sitesettings_about_description_and_more'),
    ]

    operations = [
        # ── Header / Navigation fields ───────────────────────────────────────
        migrations.AddField(
            model_name='sitesettings',
            name='logo_text',
            field=models.CharField(
                blank=True, default='', max_length=100,
                help_text='Text next to logo (leave blank to use site_author)',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='nav_links_json',
            field=models.JSONField(
                blank=True, default=list,
                help_text='Extra nav links as JSON list, e.g. [{"label":"Resume","url":"/resume/"}]. Leave empty for default nav.',
            ),
        ),

        # ── Footer fields ────────────────────────────────────────────────────
        migrations.AddField(
            model_name='sitesettings',
            name='footer_description',
            field=models.TextField(
                blank=True, default='', max_length=500,
                help_text='Footer description text (leave blank to use site_tagline)',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='footer_email',
            field=models.EmailField(
                blank=True, default='', max_length=254,
                help_text='Footer contact email (leave blank to use main email)',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='footer_social_github',
            field=models.URLField(
                blank=True, default='',
                help_text='Footer GitHub URL (leave blank to inherit from main socials)',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='footer_social_linkedin',
            field=models.URLField(
                blank=True, default='',
                help_text='Footer LinkedIn URL (leave blank to inherit from main socials)',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='footer_social_twitter',
            field=models.URLField(
                blank=True, default='',
                help_text='Footer Twitter/X URL (leave blank to inherit from main socials)',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='footer_social_telegram',
            field=models.URLField(
                blank=True, default='',
                help_text='Footer Telegram URL (leave blank to inherit from main socials)',
            ),
        ),
    ]
