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
