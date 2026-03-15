"""Tests for canvas CRUD endpoints."""

import pytest
from tests.conftest import auth_headers


class TestCanvasCurrentGet:
    def test_get_current_creates_canvas(self, client, auth_token):
        resp = client.get("/api/canvases/current", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_current"] is True
        assert data["job_description"] == ""

    def test_get_current_returns_same(self, client, auth_token):
        resp1 = client.get("/api/canvases/current", headers=auth_headers(auth_token))
        resp2 = client.get("/api/canvases/current", headers=auth_headers(auth_token))
        assert resp1.json()["id"] == resp2.json()["id"]

    def test_get_current_no_auth(self, client):
        resp = client.get("/api/canvases/current")
        assert resp.status_code == 401


class TestCanvasSave:
    def test_save_current(self, client, auth_token):
        resp = client.put("/api/canvases/current", headers=auth_headers(auth_token), json={
            "job_description": "Test job description for canvas",
            "pain_points": ["Pain 1", "Pain 2"],
            "wizard_step": 2,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_description"] == "Test job description for canvas"
        assert data["wizard_step"] == 2
        assert len(data["pain_points"]) == 2

    def test_save_partial_update(self, client, auth_token):
        # First ensure a canvas exists by getting current
        client.get("/api/canvases/current", headers=auth_headers(auth_token))
        # First save
        client.put("/api/canvases/current", headers=auth_headers(auth_token), json={
            "job_description": "Original job",
            "wizard_step": 1,
        })
        # Partial update — should preserve job_description
        resp = client.put("/api/canvases/current", headers=auth_headers(auth_token), json={
            "pain_points": ["New pain"],
        })
        data = resp.json()
        assert data["job_description"] == "Original job"
        assert data["pain_points"] == ["New pain"]


class TestCanvasCreate:
    def test_create_new_canvas(self, client, auth_token):
        # Get first canvas
        resp1 = client.get("/api/canvases/current", headers=auth_headers(auth_token))
        first_id = resp1.json()["id"]

        # Create new
        resp2 = client.post("/api/canvases/", headers=auth_headers(auth_token))
        assert resp2.status_code == 201
        second_id = resp2.json()["id"]
        assert first_id != second_id
        assert resp2.json()["is_current"] is True


class TestCanvasList:
    def test_list_canvases(self, client, auth_token):
        # Create a couple of canvases
        client.get("/api/canvases/current", headers=auth_headers(auth_token))
        client.post("/api/canvases/", headers=auth_headers(auth_token))

        resp = client.get("/api/canvases/", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        assert len(resp.json()["canvases"]) == 2


class TestCanvasDelete:
    def test_delete_own_canvas(self, client, auth_token):
        resp = client.get("/api/canvases/current", headers=auth_headers(auth_token))
        canvas_id = resp.json()["id"]

        resp = client.delete(f"/api/canvases/{canvas_id}", headers=auth_headers(auth_token))
        assert resp.status_code == 200

    def test_delete_other_users_canvas_fails(self, client, auth_token, admin_token):
        # Create canvas as regular user
        resp = client.get("/api/canvases/current", headers=auth_headers(auth_token))
        canvas_id = resp.json()["id"]

        # Try to delete as admin (different user)
        resp = client.delete(f"/api/canvases/{canvas_id}", headers=auth_headers(admin_token))
        assert resp.status_code == 404

    def test_delete_nonexistent(self, client, auth_token):
        resp = client.delete(
            "/api/canvases/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 404

    def test_delete_current_then_get_creates_new(self, client, auth_token):
        """Deleting current canvas should result in a new one on next GET."""
        resp = client.get("/api/canvases/current", headers=auth_headers(auth_token))
        old_id = resp.json()["id"]

        client.delete(f"/api/canvases/{old_id}", headers=auth_headers(auth_token))

        resp = client.get("/api/canvases/current", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        assert resp.json()["id"] != old_id


class TestCanvasPagination:
    def test_list_with_pagination(self, client, auth_token):
        """Create multiple canvases and verify pagination works."""
        # Create 3 canvases
        client.get("/api/canvases/current", headers=auth_headers(auth_token))
        client.post("/api/canvases/", headers=auth_headers(auth_token))
        client.post("/api/canvases/", headers=auth_headers(auth_token))

        # Get first page (limit=2)
        resp = client.get("/api/canvases/?limit=2", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        assert len(resp.json()["canvases"]) == 2

        # Get second page
        resp = client.get("/api/canvases/?skip=2&limit=2", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        assert len(resp.json()["canvases"]) == 1


class TestCanvasIsCurrentConsistency:
    def test_create_canvas_uncurrents_previous(self, client, auth_token):
        """Creating a new canvas should mark the old one as not current."""
        resp1 = client.get("/api/canvases/current", headers=auth_headers(auth_token))
        first_id = resp1.json()["id"]

        client.post("/api/canvases/", headers=auth_headers(auth_token))

        # List all and check only one is current
        resp = client.get("/api/canvases/", headers=auth_headers(auth_token))
        canvases = resp.json()["canvases"]
        current_canvases = [c for c in canvases if c["is_current"]]
        assert len(current_canvases) == 1
        assert current_canvases[0]["id"] != first_id


class TestSaveLoadRoundTrip:
    def test_save_and_reload_preserves_data(self, client, auth_token):
        """Saving a canvas and reloading should return the same data."""
        save_data = {
            "job_description": "Improve deployment pipeline for faster releases",
            "pain_points": ["Slow CI builds", "Manual rollback procedures"],
            "gain_points": ["Automated deployments", "Faster feedback loops"],
            "wizard_step": 3,
            "title": "DevOps Canvas",
        }
        client.put("/api/canvases/current", headers=auth_headers(auth_token), json=save_data)

        resp = client.get("/api/canvases/current", headers=auth_headers(auth_token))
        data = resp.json()
        assert data["job_description"] == save_data["job_description"]
        assert data["pain_points"] == save_data["pain_points"]
        assert data["gain_points"] == save_data["gain_points"]
        assert data["wizard_step"] == save_data["wizard_step"]
        assert data["title"] == save_data["title"]
