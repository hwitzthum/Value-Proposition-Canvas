"""
Canvas API client for the Streamlit frontend.
Replaces local JSON file persistence with database-backed storage via the backend API.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class CanvasAPIClient:
    """Thin wrapper around the canvas REST API."""

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

    # ----- Canvas CRUD -----

    def get_current(self) -> Optional[dict]:
        """Fetch the current canvas (creates one server-side if needed)."""
        try:
            resp = httpx.get(
                self._url("/api/canvases/current"),
                headers=self._headers(),
                timeout=15.0,
            )
            if resp.status_code == 200:
                return resp.json()
            logger.warning("get_current failed: %s", resp.status_code)
        except Exception as e:
            logger.error("get_current error: %s", e)
        return None

    def save_current(self, data: dict) -> Optional[dict]:
        """Save/update the current canvas."""
        try:
            resp = httpx.put(
                self._url("/api/canvases/current"),
                json=data,
                headers=self._headers(),
                timeout=15.0,
            )
            if resp.status_code == 200:
                return resp.json()
            logger.warning("save_current failed: %s", resp.status_code)
        except Exception as e:
            logger.error("save_current error: %s", e)
        return None

    def create_new(self) -> Optional[dict]:
        """Create a new canvas and make it current."""
        try:
            resp = httpx.post(
                self._url("/api/canvases/"),
                headers=self._headers(),
                timeout=15.0,
            )
            if resp.status_code in (200, 201):
                return resp.json()
        except Exception as e:
            logger.error("create_new error: %s", e)
        return None

    def list_all(self) -> list:
        """List all canvases for the current user."""
        try:
            resp = httpx.get(
                self._url("/api/canvases/"),
                headers=self._headers(),
                timeout=15.0,
            )
            if resp.status_code == 200:
                return resp.json().get("canvases", [])
        except Exception as e:
            logger.error("list_all error: %s", e)
        return []

    def delete(self, canvas_id: str) -> bool:
        """Delete a canvas by ID."""
        try:
            resp = httpx.delete(
                self._url(f"/api/canvases/{canvas_id}"),
                headers=self._headers(),
                timeout=15.0,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("delete error: %s", e)
        return False
