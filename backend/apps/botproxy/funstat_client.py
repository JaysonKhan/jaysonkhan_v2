"""HTTP client for the FunStat OSINT API with Bearer JWT authentication."""
from __future__ import annotations

import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class FunStatAPIError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(f"FunStat API error {status}: {detail}")


class FunStatClient:
    """Synchronous HTTP client for FunStat Telegram OSINT API."""

    def __init__(self):
        self._base_url = settings.FUNSTAT_API_BASE_URL.rstrip("/")
        self._token = settings.FUNSTAT_API_TOKEN
        self._timeout = settings.FUNSTAT_API_TIMEOUT

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self._base_url}{path}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.request(method, url, headers=self._headers(), **kwargs)
        except httpx.ConnectError:
            raise FunStatAPIError(0, "FunStat serveriga ulanib bo'lmadi")
        except httpx.TimeoutException:
            raise FunStatAPIError(0, "FunStat API so'rovi vaqti o'tdi")

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise FunStatAPIError(resp.status_code, detail)

        data = resp.json()
        if isinstance(data, dict) and data.get("success") is False:
            raise FunStatAPIError(
                resp.status_code,
                data.get("detail", "API xatosi"),
            )
        return data

    # ─── Free endpoints ───────────────────────────────────────────────────────

    def get_user_stats_min(self, user_id: int) -> dict:
        """Basic user stats (FREE)."""
        return self._request("GET", f"/api/v1/users/{user_id}/stats_min")

    def get_user_reputation(self, user_id: int) -> dict:
        """User reputation (FREE)."""
        return self._request("GET", f"/api/v1/users/reputation?id={user_id}")

    def get_user_groups_count(self, user_id: int, only_msg: bool = True) -> dict:
        """Total groups count (FREE)."""
        return self._request(
            "GET", f"/api/v1/users/{user_id}/groups_count?onlyMsg={str(only_msg).lower()}"
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
            "GET",
            f"/api/v1/users/{user_id}/gifts_relation?page={page}&pageSize={page_size}",
        )

    def get_user_common_groups(self, user_id: int) -> dict:
        """Users who share groups with this user (cost: 5)."""
        return self._request("GET", f"/api/v1/users/{user_id}/common_groups_stat")

    def get_user_messages(
        self, user_id: int, page: int = 1, page_size: int = 25,
        group_id: int | None = None, text_contains: str | None = None,
    ) -> dict:
        """User messages (cost: 10, paginated)."""
        params = f"?page={page}&pageSize={page_size}"
        if group_id:
            params += f"&group_id={group_id}"
        if text_contains:
            params += f"&text_contains={text_contains}"
        return self._request("GET", f"/api/v1/users/{user_id}/messages{params}")

    # ─── Search / resolve ─────────────────────────────────────────────────────

    def resolve_username(self, username: str) -> dict:
        """Resolve @username to user info (cost: 0.10)."""
        name = username.lstrip("@")
        return self._request("GET", f"/api/v1/users/resolve_username?name={name}")

    def get_username_usage(self, username: str) -> dict:
        """Username usage — who used, where mentioned (cost: 0.1)."""
        name = username.lstrip("@")
        return self._request("GET", f"/api/v1/users/username_usage?username={name}")

    def get_basic_info(self, ids: list[int]) -> dict:
        """Basic info by multiple Telegram IDs (cost: 0.10 per found)."""
        id_params = "&".join(f"id={i}" for i in ids)
        return self._request("GET", f"/api/v1/users/basic_info_by_id?{id_params}")

    # ─── Text search ──────────────────────────────────────────────────────────

    def text_search(self, query: str, page: int = 1, page_size: int = 25) -> dict:
        """Search who/when/where wrote text (cost: 0.1, paginated)."""
        from urllib.parse import quote
        return self._request(
            "GET",
            f"/api/v1/text/search?input={quote(query)}&page={page}&pageSize={page_size}",
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
        id_params = "&".join(f"id={i}" for i in ids)
        return self._request("GET", f"/api/v1/groups/common_groups?{id_params}")
