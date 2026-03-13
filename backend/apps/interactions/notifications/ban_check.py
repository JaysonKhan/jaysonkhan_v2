"""
Ban / mute verification utility.

Kept separate for reusability — can be imported by views, middleware, etc.
"""
from __future__ import annotations

from typing import Optional

from django.utils import timezone


class BanCheckResult:
    """Immutable result of checking a user's ban status."""

    __slots__ = ('is_banned', 'ban_type', 'reason', 'expires_at')

    def __init__(
        self,
        is_banned: bool = False,
        ban_type: Optional[str] = None,
        reason: str = '',
        expires_at=None,
    ):
        self.is_banned = is_banned
        self.ban_type = ban_type
        self.reason = reason
        self.expires_at = expires_at

    @property
    def message(self) -> str:
        if not self.is_banned:
            return ''
        if self.ban_type == 'ban':
            return 'You have been permanently banned from commenting.'
        if self.expires_at:
            return (
                f'You are muted until '
                f'{self.expires_at.strftime("%Y-%m-%d %H:%M UTC")}.'
            )
        return 'You are currently banned from commenting.'


def check_ban(profile) -> BanCheckResult:
    """
    Check whether *profile* is currently banned or muted.

    Expired mutes are auto-deactivated on every check so that
    subsequent requests don't need a cron job.
    """
    from interactions.models import UserBan  # avoid circular import

    now = timezone.now()

    # Auto-expire old mutes
    UserBan.objects.filter(
        profile=profile,
        is_active=True,
        ban_type='mute',
        expires_at__lt=now,
    ).update(is_active=False)

    # Fetch remaining active ban (if any)
    active = (
        UserBan.objects
        .filter(profile=profile, is_active=True)
        .order_by('-created_at')
        .first()
    )
    if not active:
        return BanCheckResult()

    return BanCheckResult(
        is_banned=True,
        ban_type=active.ban_type,
        reason=active.reason,
        expires_at=active.expires_at,
    )
