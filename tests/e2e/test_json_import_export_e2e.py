"""E2E tests for Feature C: JSON Import/Export."""

import json

import httpx
import pytest

from .conftest import BACKEND_URL, FRONTEND_URL, login_on_page


def _scroll_to_bottom(page):
    """Scroll to the bottom of the page to reveal the export section."""
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1000)


def _relogin_for_seeded_data(page):
    """Re-login so the Streamlit app loads the latest canvas from DB."""
    login_on_page(page)


class TestJSONExportE2E:
    """Test JSON export via browser and API."""

    def test_export_via_api(self, seeded_canvas, auth_token):
        """Export canvas as JSON via API and verify structure."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = httpx.post(
            f"{BACKEND_URL}/api/canvases/export/json",
            headers=headers,
            timeout=10.0,
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["version"] == "1.0"
        assert "exported_at" in data
        assert data["title"] == "E2E Test Canvas"
        assert data["job_description"] == seeded_canvas["job_description"]
        assert len(data["pain_points"]) == 7
        assert len(data["gain_points"]) == 7

    def test_export_json_button_visible(self, authenticated_page, seeded_canvas):
        """Verify Export JSON button is visible in UI."""
        page = authenticated_page
        _relogin_for_seeded_data(page)
        _scroll_to_bottom(page)

        export_btn = page.locator("button", has_text="Export JSON")
        export_btn.wait_for(state="visible", timeout=15000)
        assert export_btn.is_visible()

    def test_export_json_generates_download(self, authenticated_page, seeded_canvas):
        """Click Export JSON and verify download button appears."""
        page = authenticated_page
        _relogin_for_seeded_data(page)
        _scroll_to_bottom(page)

        export_btn = page.locator("button", has_text="Export JSON")
        export_btn.wait_for(state="visible", timeout=15000)
        export_btn.click()

        page.wait_for_timeout(5000)

        download_btn = page.locator("button", has_text="Download .json")
        download_btn.wait_for(state="visible", timeout=15000)
        assert download_btn.is_visible()


class TestJSONImportE2E:
    """Test JSON import via browser and API."""

    def test_import_via_api(self, auth_token):
        """Import a canvas via API and verify it becomes current."""
        headers = {"Authorization": f"Bearer {auth_token}"}

        import_data = {
            "version": "1.0",
            "title": "Imported via API",
            "job_description": "When managing infrastructure, I want to use IaC so that environments are reproducible",
            "pain_points": [
                "Manual server configuration takes 2 hours per environment",
                "Configuration inconsistencies between dev and production cause outages",
            ],
            "gain_points": [
                "Infrastructure provisioning completes in under 5 minutes",
                "Identical environments eliminate works-on-my-machine issues",
            ],
        }

        resp = httpx.post(
            f"{BACKEND_URL}/api/canvases/import/json",
            headers=headers,
            json=import_data,
            timeout=10.0,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Imported via API"
        assert data["is_current"] is True
        assert len(data["pain_points"]) == 2

        # Verify it's now the current canvas
        current = httpx.get(
            f"{BACKEND_URL}/api/canvases/current",
            headers=headers,
            timeout=10.0,
        )
        assert current.json()["title"] == "Imported via API"

    def test_roundtrip_via_api(self, seeded_canvas, auth_token):
        """Export a canvas, create a new one, import the export, verify data preserved."""
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Export
        export_resp = httpx.post(
            f"{BACKEND_URL}/api/canvases/export/json",
            headers=headers,
            timeout=10.0,
        )
        assert export_resp.status_code == 200
        exported = export_resp.json()

        # Create a new empty canvas (changes current)
        httpx.post(
            f"{BACKEND_URL}/api/canvases/",
            headers=headers,
            timeout=10.0,
        )

        # Import the exported data
        import_resp = httpx.post(
            f"{BACKEND_URL}/api/canvases/import/json",
            headers=headers,
            json=exported,
            timeout=10.0,
        )
        assert import_resp.status_code == 201
        imported = import_resp.json()

        # Verify data preserved
        assert imported["title"] == exported["title"]
        assert imported["job_description"] == exported["job_description"]
        assert imported["pain_points"] == exported["pain_points"]
        assert imported["gain_points"] == exported["gain_points"]

    def test_import_rejects_xss(self, auth_token):
        """XSS payloads in imported data should be sanitized."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = httpx.post(
            f"{BACKEND_URL}/api/canvases/import/json",
            headers=headers,
            json={
                "version": "1.0",
                "title": "Test Canvas",
                "job_description": "Normal description",
                "pain_points": ["Normal pain with <b>bold</b> attempt"],
                "gain_points": [],
            },
            timeout=10.0,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "<b>" not in data["pain_points"][0]
        assert "&lt;b&gt;" in data["pain_points"][0]

    def test_import_rejects_too_many_items(self, auth_token):
        """Importing more than 50 items should be rejected."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = httpx.post(
            f"{BACKEND_URL}/api/canvases/import/json",
            headers=headers,
            json={
                "version": "1.0",
                "title": "Too Many Items",
                "job_description": "Test",
                "pain_points": [f"Pain point {i}" for i in range(51)],
                "gain_points": [],
            },
            timeout=10.0,
        )
        assert resp.status_code == 422

    def test_import_file_uploader_visible(self, authenticated_page, seeded_canvas):
        """Verify the JSON file uploader is visible in the UI."""
        page = authenticated_page
        _relogin_for_seeded_data(page)
        _scroll_to_bottom(page)

        import_label = page.locator("text=Import Canvas")
        import_label.wait_for(state="visible", timeout=10000)
        assert import_label.is_visible()
