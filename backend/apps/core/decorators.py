"""Custom decorators for role-based access control (RBAC).

Integrates with Django's built-in permission system and is compatible
with the existing ``@staff_member_required`` workflow.
Supports both sync and async views.
"""
from __future__ import annotations

import asyncio
from functools import wraps

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied


def _check_perms(user, perms, any_perm: bool) -> None:
    """Raise PermissionDenied if user lacks required permissions."""
    if user.is_superuser:
        return
    if any_perm:
        if not any(user.has_perm(p) for p in perms):
            raise PermissionDenied
    else:
        if not all(user.has_perm(p) for p in perms):
            raise PermissionDenied


def admin_permission_required(*perms, any_perm: bool = False):
    """Require staff status AND specific Django permissions.

    Superusers always pass (Django's ``has_perm`` returns True for them).
    For non-superusers, checks the given permission strings.
    Supports both sync and async views.

    Args:
        *perms: Permission strings, e.g. ``'botproxy.manage_polls'``.
        any_perm: If ``True``, passes when the user has **any** of the
            given permissions.  Default (``False``) requires **all**.
    """

    def decorator(view_func):
        if asyncio.iscoroutinefunction(view_func):
            @wraps(view_func)
            @staff_member_required
            async def _wrapped(request, *args, **kwargs):
                _check_perms(request.user, perms, any_perm)
                return await view_func(request, *args, **kwargs)
        else:
            @wraps(view_func)
            @staff_member_required
            def _wrapped(request, *args, **kwargs):
                _check_perms(request.user, perms, any_perm)
                return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
