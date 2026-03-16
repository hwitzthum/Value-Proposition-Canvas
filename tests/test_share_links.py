"""Tests for shareable read-only canvas link endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from tests.conftest import auth_headers

from app.models import CanvasShareLink


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_canvas(client, token, title="Test Canvas"):
    """Create a canvas with some content and return its id."""
    # Ensure a canvas exists
    client.get("/api/canvases/current", headers=auth_headers(token))
    resp = client.put(
        "/api/canvases/current",
        headers=auth_headers(token),
        json={
            "title": title,
            "job_description": "Help small business owners manage invoices faster",
            "pain_points": ["Manual data entry is slow", "Errors in spreadsheets"],
            "gain_points": ["Automated invoice processing", "Real-time dashboards"],
        },
    )
    assert resp.status_code == 200
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Creating share links
# ---------------------------------------------------------------------------

class TestCreateShareLink:
    def test_create_share_link_returns_token(self, client, auth_token):
        canvas_id = _create_canvas(client, auth_token)
        resp = client.post(
            f"/api/canvases/{canvas_id}/share",
            headers=auth_headers(auth_token),
            json={},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "share_token" in data
        assert len(data["share_token"]) > 0
        assert data["has_password"] is False
        assert data["expires_at"] is None

    def test_create_share_link_with_password(self, client, auth_token):
        canvas_id = _create_canvas(client, auth_token)
        resp = client.post(
            f"/api/canvases/{canvas_id}/share",
            headers=auth_headers(auth_token),
            json={"password": "s3cret-horse-pw"},
        )
        assert resp.status_code == 201
        assert resp.json()["has_password"] is True

    def test_create_share_link_short_password_rejected(self, client, auth_token):
        canvas_id = _create_canvas(client, auth_token)
        resp = client.post(
            f"/api/canvases/{canvas_id}/share",
            headers=auth_headers(auth_token),
            json={"password": "short"},
        )
        assert resp.status_code == 422

    def test_create_share_link_with_expiry(self, client, auth_token):
        canvas_id = _create_canvas(client, auth_token)
        resp = client.post(
            f"/api/canvases/{canvas_id}/share",
            headers=auth_headers(auth_token),
            json={"expires_in_hours": 24},
        )
        assert resp.status_code == 201
        assert resp.json()["expires_at"] is not None

    def test_non_owner_cannot_create_share_link(self, client, auth_token, admin_token):
        canvas_id = _create_canvas(client, auth_token)
        resp = client.post(
            f"/api/canvases/{canvas_id}/share",
            headers=auth_headers(admin_token),
            json={},
        )
        assert resp.status_code == 404

    def test_create_share_link_no_auth(self, client, auth_token):
        canvas_id = _create_canvas(client, auth_token)
        resp = client.post(f"/api/canvases/{canvas_id}/share", json={})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Fetching shared canvas (public)
# ---------------------------------------------------------------------------

class TestGetSharedCanvas:
    def test_fetch_shared_canvas_no_auth_required(self, client, auth_token):
        canvas_id = _create_canvas(client, auth_token)
        create_resp = client.post(
            f"/api/canvases/{canvas_id}/share",
            headers=auth_headers(auth_token),
            json={},
        )
        token = create_resp.json()["share_token"]

        resp = client.get(f"/api/shared/{token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Canvas"
        assert data["job_description"] == "Help small business owners manage invoices faster"
        assert len(data["pain_points"]) == 2
        assert len(data["gain_points"]) == 2

    def test_shared_response_has_no_user_info(self, client, auth_token):
        canvas_id = _create_canvas(client, auth_token)
        create_resp = client.post(
            f"/api/canvases/{canvas_id}/share",
            headers=auth_headers(auth_token),
            json={},
        )
        token = create_resp.json()["share_token"]

        resp = client.get(f"/api/shared/{token}")
        data = resp.json()
        # Should NOT contain user-related fields
        assert "user_id" not in data
        assert "user" not in data
        assert "email" not in data
        assert "id" not in data

    def test_invalid_token_returns_410(self, client):
        resp = client.get("/api/shared/nonexistent-token")
        assert resp.status_code == 410


# ---------------------------------------------------------------------------
# Expired / revoked links
# ---------------------------------------------------------------------------

class TestExpiredAndRevokedLinks:
    def test_expired_link_returns_410(self, client, auth_token, db):
        canvas_id = _create_canvas(client, auth_token)
        create_resp = client.post(
            f"/api/canvases/{canvas_id}/share",
            headers=auth_headers(auth_token),
            json={"expires_in_hours": 1},
        )
        link_id = create_resp.json()["id"]
        share_token = create_resp.json()["share_token"]

        # Manually set expires_at to the past
        link = db.query(CanvasShareLink).filter(CanvasShareLink.id == link_id).first()
        link.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        resp = client.get(f"/api/shared/{share_token}")
        assert resp.status_code == 410

    def test_revoked_link_returns_410(self, client, auth_token):
        canvas_id = _create_canvas(client, auth_token)
        create_resp = client.post(
            f"/api/canvases/{canvas_id}/share",
            headers=auth_headers(auth_token),
            json={},
        )
        link_id = create_resp.json()["id"]
        share_token = create_resp.json()["share_token"]

        # Revoke the link
        revoke_resp = client.delete(
            f"/api/canvases/{canvas_id}/share/{link_id}",
            headers=auth_headers(auth_token),
        )
        assert revoke_resp.status_code == 200

        # Now fetching should return 410
        resp = client.get(f"/api/shared/{share_token}")
        assert resp.status_code == 410


# ---------------------------------------------------------------------------
# Password-protected links
# ---------------------------------------------------------------------------

class TestPasswordProtectedLinks:
    def test_password_required_when_set(self, client, auth_token):
        canvas_id = _create_canvas(client, auth_token)
        create_resp = client.post(
            f"/api/canvases/{canvas_id}/share",
            headers=auth_headers(auth_token),
            json={"password": "correct-horse"},
        )
        token = create_resp.json()["share_token"]

        # No password (GET) → 401
        resp = client.get(f"/api/shared/{token}")
        assert resp.status_code == 401

    def test_wrong_password_rejected(self, client, auth_token):
        canvas_id = _create_canvas(client, auth_token)
        create_resp = client.post(
            f"/api/canvases/{canvas_id}/share",
            headers=auth_headers(auth_token),
            json={"password": "correct-horse"},
        )
        token = create_resp.json()["share_token"]

        # Wrong password via POST body
        resp = client.post(f"/api/shared/{token}", json={"password": "wrong-horse"})
        assert resp.status_code == 401

    def test_correct_password_succeeds(self, client, auth_token):
        canvas_id = _create_canvas(client, auth_token)
        create_resp = client.post(
            f"/api/canvases/{canvas_id}/share",
            headers=auth_headers(auth_token),
            json={"password": "correct-horse"},
        )
        token = create_resp.json()["share_token"]

        # Correct password via POST body
        resp = client.post(f"/api/shared/{token}", json={"password": "correct-horse"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test Canvas"


# ---------------------------------------------------------------------------
# Revoking share links
# ---------------------------------------------------------------------------

class TestRevokeShareLink:
    def test_owner_can_revoke(self, client, auth_token):
        canvas_id = _create_canvas(client, auth_token)
        create_resp = client.post(
            f"/api/canvases/{canvas_id}/share",
            headers=auth_headers(auth_token),
            json={},
        )
        link_id = create_resp.json()["id"]

        resp = client.delete(
            f"/api/canvases/{canvas_id}/share/{link_id}",
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Share link revoked."

    def test_non_owner_cannot_revoke(self, client, auth_token, admin_token):
        canvas_id = _create_canvas(client, auth_token)
        create_resp = client.post(
            f"/api/canvases/{canvas_id}/share",
            headers=auth_headers(auth_token),
            json={},
        )
        link_id = create_resp.json()["id"]

        resp = client.delete(
            f"/api/canvases/{canvas_id}/share/{link_id}",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 404

    def test_revoke_nonexistent_link(self, client, auth_token):
        canvas_id = _create_canvas(client, auth_token)
        fake_link_id = str(uuid.uuid4())
        resp = client.delete(
            f"/api/canvases/{canvas_id}/share/{fake_link_id}",
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 404
