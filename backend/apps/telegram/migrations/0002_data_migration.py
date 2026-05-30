"""Stubbed: botproxy app removed. Original data migration no longer needed.

The forward/backward functions read botproxy models which no longer exist.
Operations cleared so fresh-DB migrate stays green. The interactions/0006
dependency on this migration remains valid (it depends on telegram/0002
existing, not on its operations).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("telegram", "0001_initial"),
        ("interactions", "0005_alter_adminlogmessage_message_id"),
    ]

    operations = []
