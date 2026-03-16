"""E2E tests for Feature A: Shareable Read-Only Canvas Links."""

import httpx
import pytest

from .conftest import BACKEND_URL, FRONTEND_URL, login_on_page


def _scroll_to_bottom(page):
    """Scroll to the bottom of the page to reveal the export/share section."""
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1000)


def _relogin_for_seeded_data(page):
    """Re-login so the Streamlit app loads the latest canvas from DB."""
    login_on_page(page)


class TestShareLinksE2E:
    """Test the share link flow end-to-end via the browser."""

    def test_create_share_link_and_view(self, authenticated_page, seeded_canvas, auth_token):
        """Create a share link via UI, then verify the share URL appears."""
        page = authenticated_page
        _relogin_for_seeded_data(page)
        _scroll_to_bottom(page)

        share_heading = page.locator("text=Share Canvas").first
        share_heading.wait_for(state="visible", timeout=15000)

        create_btn = page.locator("button", has_text="Create Share Link")
        create_btn.wait_for(state="visible", timeout=10000)
        create_btn.click()
        page.wait_for_timeout(5000)

        # The share URL should appear in a code block
        share_code = page.locator("code").filter(has_text="share=")
        share_code.wait_for(state="visible", timeout=15000)
        share_url = share_code.inner_text()
        assert "share=" in share_url

    def test_shared_canvas_via_api(self, seeded_canvas, auth_token):
        """Create a share link via API, then verify the public endpoint works."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        canvas_id = seeded_canvas["id"]

        resp = httpx.post(
            f"{BACKEND_URL}/api/canvases/{canvas_id}/share",
            headers=headers,
            json={},
            timeout=10.0,
        )
        assert resp.status_code == 201
        token = resp.json()["share_token"]

        shared_resp = httpx.get(
            f"{BACKEND_URL}/api/shared/{token}",
            timeout=10.0,
        )
        assert shared_resp.status_code == 200
        data = shared_resp.json()
        assert data["title"] == "E2E Test Canvas"
        assert len(data["pain_points"]) == 7
        assert len(data["gain_points"]) == 7
        assert "user_id" not in data
        assert "email" not in data

    def test_shared_link_renders_in_browser(self, _frontend, seeded_canvas, auth_token, page):
        """Open a shared link in the browser and verify the read-only view renders."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        canvas_id = seeded_canvas["id"]

        resp = httpx.post(
            f"{BACKEND_URL}/api/canvases/{canvas_id}/share",
            headers=headers,
            json={},
            timeout=10.0,
        )
        assert resp.status_code == 201
        token = resp.json()["share_token"]

        page.goto(f"{FRONTEND_URL}/?share={token}", wait_until="networkidle")
        page.wait_for_timeout(5000)

        page.locator("text=Shared read-only view").first.wait_for(state="visible", timeout=15000)
        page.locator("text=Pain Points").first.wait_for(state="visible", timeout=5000)
        page.locator("text=Gain Points").first.wait_for(state="visible", timeout=5000)

        # No edit controls in read-only mode
        assert page.locator("textarea").count() == 0

    def test_expired_share_link_shows_error(self, _frontend, seeded_canvas, auth_token, page):
        """A revoked share link shows an error message."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        canvas_id = seeded_canvas["id"]

        resp = httpx.post(
            f"{BACKEND_URL}/api/canvases/{canvas_id}/share",
            headers=headers,
            json={"expires_in_hours": 1},
            timeout=10.0,
        )
        assert resp.status_code == 201
        link_id = resp.json()["id"]
        token = resp.json()["share_token"]

        # Revoke the link
        del_resp = httpx.delete(
            f"{BACKEND_URL}/api/canvases/{canvas_id}/share/{link_id}",
            headers=headers,
            timeout=10.0,
        )
        assert del_resp.status_code == 200

        page.goto(f"{FRONTEND_URL}/?share={token}", wait_until="networkidle")
        page.wait_for_timeout(5000)

        page.locator("text=expired").first.wait_for(state="visible", timeout=15000)

    def test_password_protected_link_via_api(self, seeded_canvas, auth_token):
        """Password-protected share link requires correct password."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        canvas_id = seeded_canvas["id"]

        resp = httpx.post(
            f"{BACKEND_URL}/api/canvases/{canvas_id}/share",
            headers=headers,
            json={"password": "secret12345"},
            timeout=10.0,
        )
        assert resp.status_code == 201
        token = resp.json()["share_token"]

        # Without password (GET)
        assert httpx.get(f"{BACKEND_URL}/api/shared/{token}", timeout=10.0).status_code == 401
        # Wrong password (POST body)
        assert httpx.post(f"{BACKEND_URL}/api/shared/{token}", json={"password": "wrongpass"}, timeout=10.0).status_code == 401
        # Correct password (POST body)
        ok_resp = httpx.post(f"{BACKEND_URL}/api/shared/{token}", json={"password": "secret12345"}, timeout=10.0)
        assert ok_resp.status_code == 200
        assert ok_resp.json()["title"] == "E2E Test Canvas"
