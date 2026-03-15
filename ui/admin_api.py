"""
Admin API client for the main Streamlit UI.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class AdminAPIClient:
    """Thin wrapper around the admin REST API."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get_stats(self) -> Optional[dict]:
        try:
            resp = httpx.get(self._url("/api/admin/stats"), headers=self._headers(), timeout=10.0)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error("get_stats error: %s", e)
        return None

    def list_users(self, status_filter: Optional[str] = None) -> list:
        try:
            params = {"status": status_filter} if status_filter else {}
            resp = httpx.get(
                self._url("/api/admin/users"),
                headers=self._headers(),
                params=params,
                timeout=10.0,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error("list_users error: %s", e)
        return []

    def get_user(self, user_id: str) -> Optional[dict]:
        try:
            resp = httpx.get(
                self._url(f"/api/admin/users/{user_id}"),
                headers=self._headers(),
                timeout=10.0,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error("get_user error: %s", e)
        return None

    def update_user_status(self, user_id: str, new_status: str) -> Optional[dict]:
        try:
            resp = httpx.patch(
                self._url(f"/api/admin/users/{user_id}/status"),
                json={"status": new_status},
                headers=self._headers(),
                timeout=10.0,
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": resp.json().get("detail", "Unknown error")}
        except Exception as e:
            logger.error("update_user_status error: %s", e)
        return None

    def reset_password(self, user_id: str, new_password: str) -> Optional[dict]:
        try:
            resp = httpx.post(
                self._url(f"/api/admin/users/{user_id}/reset-password"),
                json={"new_password": new_password},
                headers=self._headers(),
                timeout=10.0,
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": resp.json().get("detail", "Unknown error")}
        except Exception as e:
            logger.error("reset_password error: %s", e)
        return None
