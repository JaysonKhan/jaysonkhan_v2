"""Create or refresh RBAC groups (admin, analyst) with proper permissions.

Safe to run multiple times — uses get_or_create and .set().
Called automatically after ``migrate`` via a post_migrate signal
(see ``users.apps``), or manually with::

    python manage.py setup_rbac
"""
from __future__ import annotations

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


def create_rbac_groups(**kwargs) -> dict[str, int]:
    """Create/update admin and analyst groups. Returns perm counts."""

    # ── Admin group — full access ────────────────────────────────────────
    admin_group, _ = Group.objects.get_or_create(name="admin")
    all_perms = Permission.objects.all()
    admin_group.permissions.set(all_perms)

    # ── Analyst group — read-only ────────────────────────────────────────
    analyst_group, _ = Group.objects.get_or_create(name="analyst")

    analyst_perms = set()

    # All view_* permissions (read-only access to Django admin models)
    view_perms = Permission.objects.filter(codename__startswith="view_")
    analyst_perms.update(view_perms)

    analyst_group.permissions.set(analyst_perms)

    return {
        "admin": admin_group.permissions.count(),
        "analyst": len(analyst_perms),
    }


class Command(BaseCommand):
    help = "Create/refresh RBAC permission groups (admin, analyst)"

    def handle(self, *args, **options):
        counts = create_rbac_groups()
        self.stdout.write(
            self.style.SUCCESS(
                f"RBAC groups created: "
                f"admin ({counts['admin']} perms), "
                f"analyst ({counts['analyst']} perms)"
            )
        )
