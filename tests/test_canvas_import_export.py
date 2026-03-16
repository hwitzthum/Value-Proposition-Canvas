"""Tests for JSON canvas import/export."""

import pytest
from tests.conftest import auth_headers


class TestCanvasExport:
    """Tests for POST /api/canvases/export/json."""

    def test_export_returns_json_structure(self, client, auth_token):
        # Create some canvas content first
        client.put(
            "/api/canvases/current",
            json={
                "title": "Test Canvas",
                "job_description": "Test job description for export",
                "pain_points": ["Pain 1", "Pain 2"],
                "gain_points": ["Gain 1"],
            },
            headers=auth_headers(auth_token),
        )

        resp = client.post(
            "/api/canvases/export/json",
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == "1.0"
        assert "exported_at" in data
        assert data["title"] == "Test Canvas"
        assert data["job_description"] == "Test job description for export"
        assert data["pain_points"] == ["Pain 1", "Pain 2"]
        assert data["gain_points"] == ["Gain 1"]

    def test_export_requires_auth(self, client):
        resp = client.post("/api/canvases/export/json")
        assert resp.status_code == 401


class TestCanvasImport:
    """Tests for POST /api/canvases/import/json."""

    def test_import_creates_canvas(self, client, auth_token):
        resp = client.post(
            "/api/canvases/import/json",
            json={
                "version": "1.0",
                "title": "Imported Canvas",
                "job_description": "Imported job description",
                "pain_points": ["Imported pain 1", "Imported pain 2"],
                "gain_points": ["Imported gain 1"],
            },
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Imported Canvas"
        assert data["job_description"] == "Imported job description"
        assert data["pain_points"] == ["Imported pain 1", "Imported pain 2"]
        assert data["is_current"] is True

    def test_import_becomes_current(self, client, auth_token):
        """Imported canvas becomes the current one."""
        # Create initial canvas
        client.put(
            "/api/canvases/current",
            json={"title": "Original"},
            headers=auth_headers(auth_token),
        )

        # Import new canvas
        client.post(
            "/api/canvases/import/json",
            json={
                "version": "1.0",
                "title": "Imported",
                "job_description": "New job",
                "pain_points": [],
                "gain_points": [],
            },
            headers=auth_headers(auth_token),
        )

        # Current canvas should be the imported one
        resp = client.get(
            "/api/canvases/current",
            headers=auth_headers(auth_token),
        )
        assert resp.json()["title"] == "Imported"

    def test_import_rejects_excessive_items(self, client, auth_token):
        resp = client.post(
            "/api/canvases/import/json",
            json={
                "version": "1.0",
                "title": "Too Many",
                "job_description": "Test",
                "pain_points": [f"Pain {i}" for i in range(51)],
                "gain_points": [],
            },
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 422

    def test_import_sanitizes_xss(self, client, auth_token):
        """XSS in imported data is sanitized."""
        resp = client.post(
            "/api/canvases/import/json",
            json={
                "version": "1.0",
                "title": "Clean Title",
                "job_description": "Normal description",
                "pain_points": ["Normal pain with <b>bold</b> text"],
                "gain_points": [],
            },
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        # HTML should be escaped
        assert "<b>" not in data["pain_points"][0]
        assert "&lt;b&gt;" in data["pain_points"][0]

    def test_import_requires_auth(self, client):
        resp = client.post(
            "/api/canvases/import/json",
            json={"version": "1.0", "title": "Test"},
        )
        assert resp.status_code == 401

    def test_roundtrip_preserves_data(self, client, auth_token):
        """Export then import preserves all canvas data."""
        # Set up canvas
        client.put(
            "/api/canvases/current",
            json={
                "title": "Roundtrip Test",
                "job_description": "A specific job description for testing roundtrip",
                "pain_points": ["First pain point here", "Second pain point here"],
                "gain_points": ["First gain point here"],
            },
            headers=auth_headers(auth_token),
        )

        # Export
        export_resp = client.post(
            "/api/canvases/export/json",
            headers=auth_headers(auth_token),
        )
        exported = export_resp.json()

        # Create new canvas to change current
        client.post(
            "/api/canvases/",
            headers=auth_headers(auth_token),
        )

        # Import the exported data
        import_resp = client.post(
            "/api/canvases/import/json",
            json=exported,
            headers=auth_headers(auth_token),
        )
        assert import_resp.status_code == 201
        imported = import_resp.json()

        assert imported["title"] == "Roundtrip Test"
        assert imported["job_description"] == "A specific job description for testing roundtrip"
        assert imported["pain_points"] == ["First pain point here", "Second pain point here"]
        assert imported["gain_points"] == ["First gain point here"]
