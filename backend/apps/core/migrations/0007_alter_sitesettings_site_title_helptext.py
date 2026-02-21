from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_header_footer_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitesettings',
            name='site_title',
            field=models.CharField(
                default='Jahongir Kuziboev | Flutter Mobile Engineer',
                help_text='Full site name — used in the page title tag and nav logo',
                max_length=255,
            ),
        ),
    ]
