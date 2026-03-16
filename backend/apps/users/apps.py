import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


def _setup_rbac_after_migrate(sender, **kwargs):
    """Auto-create RBAC groups after migrations complete."""
    try:
        from users.management.commands.setup_rbac import create_rbac_groups
        create_rbac_groups()
    except Exception as exc:
        logger.debug("RBAC setup skipped: %s", exc)


class UsersConfig(AppConfig):
    name = 'users'

    def ready(self):
        from django.db.models.signals import post_migrate

        post_migrate.connect(_setup_rbac_after_migrate, sender=self)
