"""Custom decorators for role-based access control (RBAC).

Integrates with Django's built-in permission system and is compatible
with the existing ``@staff_member_required`` workflow.
"""
from __future__ import annotations

from functools import wraps

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied


def admin_permission_required(*perms, any_perm: bool = False):
    """Require staff status AND specific Django permissions.

    Superusers always pass (Django's ``has_perm`` returns True for them).
    For non-superusers, checks the given permission strings.

    Args:
        *perms: Permission strings, e.g. ``'botproxy.manage_polls'``.
        any_perm: If ``True``, passes when the user has **any** of the
            given permissions.  Default (``False``) requires **all**.
    """

    def decorator(view_func):
        @wraps(view_func)
        @staff_member_required
        def _wrapped(request, *args, **kwargs):
            user = request.user
            # Superusers bypass all permission checks
            if user.is_superuser:
                return view_func(request, *args, **kwargs)
            # Check permissions
            if any_perm:
                if not any(user.has_perm(p) for p in perms):
                    raise PermissionDenied
            else:
                if not all(user.has_perm(p) for p in perms):
                    raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
