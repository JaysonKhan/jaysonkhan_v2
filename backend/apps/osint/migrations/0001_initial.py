"""Claim OsintCache and OsintSearchLog tables from botproxy.

State operations create the models in osint app's state.
Database operations rename the tables from botproxy_* to osint_*.

This migration depends on botproxy.0007 which removes the models
from botproxy's state (without touching the DB).
"""
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("botproxy", "0007_remove_osint_models_state_only"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="OsintCache",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("endpoint_type", models.CharField(
                            choices=[
                                ("stats_min", "Basic Stats (free)"),
                                ("groups_count", "Groups Count (free)"),
                                ("messages_count", "Messages Count (free)"),
                                ("reputation", "Reputation (free)"),
                                ("stats_full", "Full Stats (1)"),
                                ("groups", "Groups (5)"),
                                ("names", "Name History (3)"),
                                ("usernames", "Username History (3)"),
                                ("stickers", "Stickers (1)"),
                                ("gifts", "Gift Relations (5)"),
                                ("common_groups_stat", "Common Groups Stat (5)"),
                                ("messages", "Messages (10)"),
                                ("basic_info", "Basic Info (0.10)"),
                                ("resolve_username", "Resolve Username (0.10)"),
                                ("username_usage", "Username Usage (0.1)"),
                                ("group_info", "Group Info (0.01)"),
                                ("group_members", "Group Members (15)"),
                                ("common_groups", "Common Groups (0.5)"),
                                ("text_search", "Text Search (0.1)"),
                                ("channel_profile", "Channel Profile (Telethon)"),
                                ("channel_messages", "Channel Messages (Telethon)"),
                                ("channel_search", "Channel Search (Telethon)"),
                            ],
                            db_index=True,
                            max_length=30,
                        )),
                        ("target_id", models.CharField(db_index=True, help_text="Telegram user/group ID, username, or search query", max_length=255)),
                        ("page", models.PositiveIntegerField(default=1, help_text="Page for paginated endpoints")),
                        ("data", models.JSONField(help_text="The 'data' payload from FunStat response")),
                        ("tech", models.JSONField(blank=True, default=dict, help_text="The 'tech' metadata (request_cost, current_ballance, duration)")),
                        ("fetched_at", models.DateTimeField(default=django.utils.timezone.now)),
                        ("fetched_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        "verbose_name": "OSINT Cache Entry",
                        "verbose_name_plural": "OSINT Cache Entries",
                        "ordering": ["-fetched_at"],
                        "unique_together": {("endpoint_type", "target_id", "page")},
                    },
                ),
                migrations.CreateModel(
                    name="OsintSearchLog",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("query", models.CharField(max_length=255)),
                        ("query_type", models.CharField(choices=[("id", "User ID"), ("username", "Username"), ("text", "Text Search"), ("channel", "Channel/Group")], max_length=20)),
                        ("resolved_id", models.BigIntegerField(blank=True, null=True)),
                        ("searched_at", models.DateTimeField(default=django.utils.timezone.now)),
                        ("api_cost", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                        ("balance_after", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                        ("searched_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        "ordering": ["-searched_at"],
                    },
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE botproxy_osintcache RENAME TO osint_osintcache;",
                    reverse_sql="ALTER TABLE osint_osintcache RENAME TO botproxy_osintcache;",
                ),
                migrations.RunSQL(
                    sql="ALTER TABLE botproxy_osintsearchlog RENAME TO osint_osintsearchlog;",
                    reverse_sql="ALTER TABLE osint_osintsearchlog RENAME TO botproxy_osintsearchlog;",
                ),
            ],
        ),
    ]
