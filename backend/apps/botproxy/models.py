"""Botproxy models.

OSINT models (OsintCache, OsintSearchLog) have been moved to the ``osint`` app.
TelegramSession and OsintPhotoCache have been moved to the ``telegram`` app.
"""
from django.db import models


class BotProxyPermissions(models.Model):
    """Proxy model solely for defining custom RBAC permissions.

    No database table is created — permissions are registered
    via Django's ``auth_permission`` table after ``makemigrations``.
    """

    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ("view_bot_dashboard", "Can view bot dashboard and read-only data"),
            ("manage_polls", "Can create, close, delete, publish polls"),
            ("manage_bot_admins", "Can add/remove bot admins"),
            ("manage_universities", "Can CRUD universities"),
            ("manage_telegram_session", "Can manage Telegram MTProto session"),
            ("export_data", "Can download CSV/PDF/JSON exports"),
        ]
