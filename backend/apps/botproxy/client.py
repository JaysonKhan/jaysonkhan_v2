"""HTTP client for the hokimiyatbot REST API with HMAC-SHA256 authentication."""
from __future__ import annotations

import hashlib
import hmac
import json as json_mod
import logging
import time

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class BotAPIError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(f"Bot API error {status}: {detail}")


class BotAPIClient:
    """Synchronous HTTP client for bot API with HMAC authentication."""

    def __init__(self):
        self._base_url = settings.BOT_API_BASE_URL.rstrip("/")
        self._secret = settings.BOT_API_SECRET_KEY
        self._timeout = getattr(settings, "BOT_API_TIMEOUT", 30)

    def _headers(self, method: str, path: str, body: str = "") -> dict:
        timestamp = str(int(time.time()))
        message = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self._secret.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        return {
            "X-Timestamp": timestamp,
            "X-Signature": signature,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self._base_url}{path}"
        body = kwargs.pop("content", "") or ""
        if "json" in kwargs:
            body = json_mod.dumps(kwargs.pop("json"))
            kwargs["content"] = body

        # Sign with path only (no query string) to match bot API's request.path
        sign_path = path.split("?", 1)[0]
        headers = self._headers(method, sign_path, body)
        headers.update(kwargs.pop("headers", {}))

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.request(method, url, headers=headers, **kwargs)
        except httpx.ConnectError:
            raise BotAPIError(0, "Cannot connect to bot API server")
        except httpx.TimeoutException:
            raise BotAPIError(0, "Bot API request timed out")

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("error", resp.text)
            except Exception:
                detail = resp.text
            raise BotAPIError(resp.status_code, detail)

        return resp

    # ─── Health ──────────────────────────────────────────────────────────────

    def health(self) -> dict:
        return self._request("GET", "/api/v1/health").json()

    # ─── Polls ───────────────────────────────────────────────────────────────

    def list_polls(self, status: str | None = None) -> list[dict]:
        params = f"?status={status}" if status else ""
        return self._request("GET", f"/api/v1/polls{params}").json()["polls"]

    def get_poll(self, poll_id: int) -> dict:
        return self._request("GET", f"/api/v1/polls/{poll_id}").json()

    def create_poll(self, data: dict) -> dict:
        return self._request("POST", "/api/v1/polls", json=data).json()

    def update_poll(self, poll_id: int, data: dict) -> dict:
        return self._request("PATCH", f"/api/v1/polls/{poll_id}", json=data).json()

    def close_poll(self, poll_id: int) -> dict:
        return self._request("POST", f"/api/v1/polls/{poll_id}/close").json()

    def get_results(self, poll_id: int) -> dict:
        return self._request("GET", f"/api/v1/polls/{poll_id}/results").json()

    # ─── Analytics ───────────────────────────────────────────────────────────

    def get_top(self, poll_id: int, limit: int = 10) -> dict:
        return self._request("GET", f"/api/v1/analytics/{poll_id}/top?limit={limit}").json()

    def get_votes_by_date(self, poll_id: int, days: int = 7) -> dict:
        return self._request("GET", f"/api/v1/analytics/{poll_id}/by-date?days={days}").json()

    def get_votes_by_hour(self, poll_id: int) -> dict:
        return self._request("GET", f"/api/v1/analytics/{poll_id}/by-hour").json()

    def get_votes_by_faculty(self, poll_id: int) -> dict:
        return self._request("GET", f"/api/v1/analytics/{poll_id}/by-faculty").json()

    # ─── Export ──────────────────────────────────────────────────────────────

    def export_csv(self, poll_id: int) -> bytes:
        return self._request("GET", f"/api/v1/export/{poll_id}/csv").content

    def export_json(self, poll_id: int) -> bytes:
        return self._request("GET", f"/api/v1/export/{poll_id}/json").content

    def export_pdf(self, poll_id: int) -> bytes:
        return self._request("GET", f"/api/v1/export/{poll_id}/pdf").content

    def get_chart(self, poll_id: int, chart_type: str, theme: str = "") -> bytes:
        params = f"?theme={theme}" if theme else ""
        return self._request("GET", f"/api/v1/export/{poll_id}/chart/{chart_type}{params}").content

    # ─── Admins ──────────────────────────────────────────────────────────────

    def list_admins(self) -> list[int]:
        return self._request("GET", "/api/v1/admins").json()["admin_ids"]

    def add_admin(self, user_id: int, added_by: int = 0) -> dict:
        return self._request("POST", "/api/v1/admins", json={"user_id": user_id, "added_by": added_by}).json()

    def remove_admin(self, user_id: int) -> dict:
        return self._request("DELETE", f"/api/v1/admins/{user_id}").json()

    # ─── Users ───────────────────────────────────────────────────────────────

    def get_user_count(self) -> int:
        return self._request("GET", "/api/v1/users/count").json()["count"]

    def get_user_stats(self) -> dict:
        """Aggregated user stats: {total, today, this_week, this_month, active_voters}."""
        return self._request("GET", "/api/v1/users/stats").json()

    def list_users(self, page: int = 1, per_page: int = 25, search: str = "",
                   sort: str = "", order: str = "asc") -> dict:
        """List users with pagination, search, and sorting.

        Returns {users: [...], total: int, page: int, per_page: int}.
        sort: 'name', 'registered_at', 'total_votes' (empty = default)
        order: 'asc' or 'desc'
        """
        params = f"?page={page}&per_page={per_page}"
        if search:
            params += f"&search={search}"
        if sort:
            params += f"&sort={sort}&order={order}"
        return self._request("GET", f"/api/v1/users{params}").json()

    def get_user_history(self, user_id: int) -> dict:
        return self._request("GET", f"/api/v1/users/{user_id}/history").json()

    def get_user_photo(self, user_id: int) -> bytes | None:
        """Fetch user profile photo as bytes. Returns None if not found."""
        try:
            return self._request("GET", f"/api/v1/users/{user_id}/photo").content
        except BotAPIError:
            return None

    def get_user_growth_chart(self, days: int = 30, theme: str = "") -> bytes:
        """User registration trend chart as PNG."""
        params = f"?days={days}"
        if theme:
            params += f"&theme={theme}"
        return self._request("GET", f"/api/v1/users/chart/growth{params}").content

    def export_users_csv(self) -> bytes:
        """Download all users as CSV."""
        return self._request("GET", "/api/v1/users/export/csv").content
