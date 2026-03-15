"""Remove OsintCache and OsintSearchLog from botproxy state.

The actual database tables are NOT touched — they will be claimed
by the new ``osint`` app via its own SeparateDatabaseAndState migration.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("botproxy", "0006_add_channel_osint_choices"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="OsintCache"),
                migrations.DeleteModel(name="OsintSearchLog"),
            ],
            database_operations=[],  # DB tables untouched
        ),
    ]
