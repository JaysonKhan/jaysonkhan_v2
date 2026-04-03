"""HTTP client for the FunStat OSINT API with Bearer JWT authentication.

Connection pooling: thread-safe singleton httpx.Client — TCP handshake overhead yo'q.
Retry logic: 2 marta urinish, 429/502/503/504 uchun exponential backoff.
"""
from __future__ import annotations

import atexit
import logging
import threading
import time
from typing import Any

import httpx
from django.conf import settings

from osint.exceptions import FunStatAPIError

logger = logging.getLogger(__name__)

# ── Connection pool (thread-safe singleton) ──────────────────────────────────

_shared_client: httpx.Client | None = None
_client_lock = threading.Lock()

MAX_RETRIES = 2
RETRY_BASE_DELAY = 0.5  # sekund (gunicorn worker ni bloklash kamaytirildi)
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}


def _get_shared_client() -> httpx.Client:
    """Thread-safe singleton httpx.Client with connection pooling."""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        with _client_lock:
            if _shared_client is None or _shared_client.is_closed:
                _shared_client = httpx.Client(
                    timeout=getattr(settings, "FUNSTAT_API_TIMEOUT", 30),
                    limits=httpx.Limits(
                        max_connections=10,
                        max_keepalive_connections=5,
                        keepalive_expiry=300,
                    ),
                    headers={
                        "Authorization": f"Bearer {settings.FUNSTAT_API_TOKEN}",
                        "Accept": "application/json",
                    },
                )
    return _shared_client


def _cleanup_client():
    global _shared_client
    if _shared_client and not _shared_client.is_closed:
        _shared_client.close()


atexit.register(_cleanup_client)


class FunStatClient:
    """Synchronous HTTP client for FunStat Telegram OSINT API."""

    def __init__(self):
        self._base_url = settings.FUNSTAT_API_BASE_URL.rstrip("/")

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self._base_url}{path}"
        client = _get_shared_client()
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                resp = client.request(method, url, **kwargs)
            except httpx.ConnectError as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "FunStat %s %s ulanish xatosi, retry %d/%d (%.1fs)",
                        method, path, attempt + 1, MAX_RETRIES, delay,
                    )
                    time.sleep(delay)
                    continue
                raise FunStatAPIError(0, "FunStat serveriga ulanib bo'lmadi")
            except httpx.TimeoutException as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "FunStat %s %s timeout, retry %d/%d (%.1fs)",
                        method, path, attempt + 1, MAX_RETRIES, delay,
                    )
                    time.sleep(delay)
                    continue
                raise FunStatAPIError(0, "FunStat API so'rovi vaqti o'tdi")
            except httpx.HTTPError as e:
                raise FunStatAPIError(0, f"HTTP xatoligi: {e}")

            # Retryable status codes
            if resp.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after:
                        try:
                            delay = max(delay, float(retry_after))
                        except ValueError:
                            pass
                logger.warning(
                    "FunStat %s %s → %d, retry %d/%d (%.1fs)",
                    method, path, resp.status_code, attempt + 1, MAX_RETRIES, delay,
                )
                time.sleep(delay)
                continue

            # Non-retryable error
            if resp.status_code >= 400:
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:
                    detail = resp.text
                raise FunStatAPIError(resp.status_code, detail)

            # Success
            try:
                data = resp.json()
            except Exception:
                logger.warning(
                    "FunStat %s %s → %d non-JSON response",
                    method, path, resp.status_code,
                )
                raise FunStatAPIError(
                    resp.status_code,
                    "API javobini o'qib bo'lmadi (non-JSON)",
                )
            if isinstance(data, dict) and data.get("success") is False:
                raise FunStatAPIError(
                    resp.status_code,
                    data.get("detail", "API xatosi"),
                )
            return data

        # All retries exhausted
        raise FunStatAPIError(0, f"Barcha urinishlar tugadi: {last_error}")

    # ─── Free endpoints ───────────────────────────────────────────────────────

    def get_user_stats_min(self, user_id: int) -> dict:
        """Basic user stats (FREE)."""
        return self._request("GET", f"/api/v1/users/{user_id}/stats_min")

    def get_user_reputation(self, user_id: int) -> dict:
        """User reputation (FREE)."""
        return self._request("GET", "/api/v1/users/reputation", params={"id": user_id})

    def get_user_groups_count(self, user_id: int, only_msg: bool = True) -> dict:
        """Total groups count (FREE)."""
        return self._request(
            "GET", f"/api/v1/users/{user_id}/groups_count",
            params={"onlyMsg": str(only_msg).lower()},
        )

    def get_user_messages_count(self, user_id: int) -> dict:
        """Total messages count (FREE)."""
        return self._request("GET", f"/api/v1/users/{user_id}/messages_count")

    # ─── Paid user endpoints ──────────────────────────────────────────────────

    def get_user_stats_full(self, user_id: int) -> dict:
        """Full user stats (cost: 1)."""
        return self._request("GET", f"/api/v1/users/{user_id}/stats")

    def get_user_groups(self, user_id: int) -> dict:
        """Known user groups (cost: 5)."""
        return self._request("GET", f"/api/v1/users/{user_id}/groups")

    def get_user_names(self, user_id: int) -> dict:
        """Name (first+last) history (cost: 3)."""
        return self._request("GET", f"/api/v1/users/{user_id}/names")

    def get_user_usernames(self, user_id: int) -> dict:
        """@username history (cost: 3)."""
        return self._request("GET", f"/api/v1/users/{user_id}/usernames")

    def get_user_stickers(self, user_id: int) -> dict:
        """Sticker packs created by user (cost: 1)."""
        return self._request("GET", f"/api/v1/users/{user_id}/stickers")

    def get_user_gifts(self, user_id: int, page: int = 1, page_size: int = 25) -> dict:
        """Gift relations — from whom / to whom (cost: 5, paginated)."""
        return self._request(
            "GET", f"/api/v1/users/{user_id}/gifts_relation",
            params={"page": page, "pageSize": page_size},
        )

    def get_user_common_groups(self, user_id: int) -> dict:
        """Users who share groups with this user (cost: 5)."""
        return self._request("GET", f"/api/v1/users/{user_id}/common_groups_stat")

    def get_user_messages(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 25,
        group_id: int | None = None,
        text_contains: str | None = None,
    ) -> dict:
        """User messages (cost: 10, paginated)."""
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if group_id:
            params["group_id"] = group_id
        if text_contains:
            params["text_contains"] = text_contains
        return self._request("GET", f"/api/v1/users/{user_id}/messages", params=params)

    # ─── Search / resolve ─────────────────────────────────────────────────────

    def resolve_username(self, username: str) -> dict:
        """Resolve @username to user info (cost: 0.10)."""
        name = username.lstrip("@")
        return self._request("GET", "/api/v1/users/resolve_username", params={"name": name})

    def get_username_usage(self, username: str) -> dict:
        """Username usage — who used, where mentioned (cost: 0.1)."""
        name = username.lstrip("@")
        return self._request("GET", "/api/v1/users/username_usage", params={"username": name})

    def get_basic_info(self, ids: list[int]) -> dict:
        """Basic info by multiple Telegram IDs (cost: 0.10 per found)."""
        return self._request("GET", "/api/v1/users/basic_info_by_id", params=[("id", i) for i in ids])

    # ─── Text search ──────────────────────────────────────────────────────────

    def text_search(self, query: str, page: int = 1, page_size: int = 25) -> dict:
        """Search who/when/where wrote text (cost: 0.1, paginated)."""
        return self._request(
            "GET", "/api/v1/text/search",
            params={"input": query, "page": page, "pageSize": page_size},
        )

    # ─── Groups ───────────────────────────────────────────────────────────────

    def get_group_info(self, group_id: int) -> dict:
        """Group basic info (cost: 0.01)."""
        return self._request("GET", f"/api/v1/groups/{group_id}")

    def get_group_members(self, group_id: int) -> dict:
        """Group members (cost: 15)."""
        return self._request("GET", f"/api/v1/groups/{group_id}/members")

    def get_common_groups(self, ids: list[int]) -> dict:
        """Common groups for multiple users (cost: 0.5)."""
        return self._request("GET", "/api/v1/groups/common_groups", params=[("id", i) for i in ids])
