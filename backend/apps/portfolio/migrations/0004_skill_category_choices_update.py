# Migration: Update Skill.category choices
# Added: security, performance, media & streaming
# Removed: other
# This is a metadata-only change (choices are not enforced at DB level),
# so existing rows remain intact with no data loss.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0003_remove_project_tech_stack'),
    ]

    operations = [
        migrations.AlterField(
            model_name='skill',
            name='category',
            field=models.CharField(
                choices=[
                    ('mobile', 'Mobile'),
                    ('architecture', 'Architecture'),
                    ('backend', 'Backend & Networking'),
                    ('database', 'Databases'),
                    ('security', 'Security'),
                    ('performance', 'Performance'),
                    ('media', 'Media & Streaming'),
                    ('devops', 'DevOps & Tools'),
                    ('uiux', 'UI/UX'),
                ],
                default='other',
                help_text='Skill category for grouped display',
                max_length=20,
            ),
        ),
    ]
