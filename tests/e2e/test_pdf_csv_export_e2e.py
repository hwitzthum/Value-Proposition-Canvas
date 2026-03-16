"""E2E tests for Feature 3: PDF/CSV Export."""

import csv
import io

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


class TestPDFExportE2E:
    """Test PDF export via browser and API."""

    def test_pdf_download_via_api(self, seeded_canvas, auth_token):
        """Generate PDF via API and verify it's a valid PDF."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = httpx.post(
            f"{BACKEND_URL}/api/generate-pdf",
            headers=headers,
            json={
                "job_description": seeded_canvas["job_description"],
                "pain_points": seeded_canvas["pain_points"],
                "gain_points": seeded_canvas["gain_points"],
                "title": "E2E Test Canvas",
            },
            timeout=15.0,
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:5] == b"%PDF-"
        assert len(resp.content) > 500

    def test_pdf_button_visible_in_ui(self, authenticated_page, seeded_canvas):
        """Verify the PDF export button is visible in the export section."""
        page = authenticated_page
        _relogin_for_seeded_data(page)
        _scroll_to_bottom(page)

        pdf_btn = page.locator("button", has_text="Generate PDF")
        pdf_btn.wait_for(state="visible", timeout=15000)
        assert pdf_btn.is_visible()

    def test_pdf_generate_and_download_button_appears(self, authenticated_page, seeded_canvas):
        """Click Generate PDF and verify the download button appears."""
        page = authenticated_page
        _relogin_for_seeded_data(page)
        _scroll_to_bottom(page)

        pdf_btn = page.locator("button", has_text="Generate PDF")
        pdf_btn.wait_for(state="visible", timeout=15000)
        pdf_btn.click()

        page.wait_for_timeout(5000)
        download_btn = page.locator("button", has_text="Download .pdf")
        download_btn.wait_for(state="visible", timeout=15000)
        assert download_btn.is_visible()


class TestCSVExportE2E:
    """Test CSV export via browser and API."""

    def test_csv_download_via_api(self, seeded_canvas, auth_token):
        """Generate CSV via API and verify structure."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = httpx.post(
            f"{BACKEND_URL}/api/generate-csv",
            headers=headers,
            json={
                "job_description": seeded_canvas["job_description"],
                "pain_points": seeded_canvas["pain_points"],
                "gain_points": seeded_canvas["gain_points"],
                "title": "E2E Test Canvas",
            },
            timeout=15.0,
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)

        assert rows[0] == ["section", "item_number", "content"]
        assert rows[1][0] == "job_description"

        pain_rows = [r for r in rows if r[0] == "pain_point"]
        gain_rows = [r for r in rows if r[0] == "gain_point"]
        assert len(pain_rows) == 7
        assert len(gain_rows) == 7

    def test_csv_button_visible_in_ui(self, authenticated_page, seeded_canvas):
        """Verify the CSV export button is visible."""
        page = authenticated_page
        _relogin_for_seeded_data(page)
        _scroll_to_bottom(page)

        csv_btn = page.locator("button", has_text="Generate CSV")
        csv_btn.wait_for(state="visible", timeout=15000)
        assert csv_btn.is_visible()

    def test_csv_generate_and_download_button_appears(self, authenticated_page, seeded_canvas):
        """Click Generate CSV and verify the download button appears."""
        page = authenticated_page
        _relogin_for_seeded_data(page)
        _scroll_to_bottom(page)

        csv_btn = page.locator("button", has_text="Generate CSV")
        csv_btn.wait_for(state="visible", timeout=15000)
        csv_btn.click()

        page.wait_for_timeout(5000)
        download_btn = page.locator("button", has_text="Download .csv")
        download_btn.wait_for(state="visible", timeout=15000)
        assert download_btn.is_visible()

    def test_word_export_still_works(self, seeded_canvas, auth_token):
        """Verify existing Word export still works alongside new exports."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = httpx.post(
            f"{BACKEND_URL}/api/generate-document",
            headers=headers,
            json={
                "job_description": seeded_canvas["job_description"],
                "pain_points": seeded_canvas["pain_points"],
                "gain_points": seeded_canvas["gain_points"],
                "title": "E2E Test Canvas",
            },
            timeout=15.0,
        )
        assert resp.status_code == 200
        assert "officedocument" in resp.headers["content-type"]
