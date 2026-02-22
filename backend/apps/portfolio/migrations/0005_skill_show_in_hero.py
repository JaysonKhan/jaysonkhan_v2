from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0004_skill_category_choices_update'),
    ]

    operations = [
        migrations.AddField(
            model_name='skill',
            name='show_in_hero',
            field=models.BooleanField(
                default=False,
                help_text='Show this skill icon in the hero section orbit animation',
            ),
        ),
    ]
