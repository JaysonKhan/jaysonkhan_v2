"""OSINT exception hierarchy."""
from __future__ import annotations


class OsintError(Exception):
    """Base exception for OSINT operations."""


class FunStatAPIError(OsintError):
    """FunStat API returned an error."""

    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(f"FunStat API error {status}: {detail}")


class FunStatConnectionError(OsintError):
    """Cannot reach FunStat API."""


class FunStatRateLimitError(OsintError):
    """FunStat API rate limited (429)."""

    def __init__(self, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__("FunStat rate limit")
