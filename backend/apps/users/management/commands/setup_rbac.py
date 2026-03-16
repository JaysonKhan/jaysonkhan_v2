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

    # ── Analyst group — read-only + OSINT + export ───────────────────────
    analyst_group, _ = Group.objects.get_or_create(name="analyst")

    analyst_perms = set()

    # All view_* permissions (read-only access to Django admin models)
    view_perms = Permission.objects.filter(codename__startswith="view_")
    analyst_perms.update(view_perms)

    # Bot dashboard read-only access
    for codename in ("view_bot_dashboard", "export_data"):
        perm = Permission.objects.filter(
            codename=codename, content_type__app_label="botproxy",
        ).first()
        if perm:
            analyst_perms.add(perm)

    # Full OSINT access
    osint_perm = Permission.objects.filter(
        codename="use_osint", content_type__app_label="osint",
    ).first()
    if osint_perm:
        analyst_perms.add(osint_perm)

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
