from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("telegram", "0005_rename_rektor_to_talabaovozi"),
    ]

    operations = [
        migrations.DeleteModel(name="TelegramSession"),
    ]
