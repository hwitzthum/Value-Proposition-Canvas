"""Tests for PDF and CSV export endpoints."""

import csv
import io

import pytest
from tests.conftest import auth_headers


class TestPDFExport:
    """Tests for POST /api/generate-pdf."""

    VALID_CANVAS = {
        "job_description": "When deploying software updates, I want to automate the release pipeline so that deployments are fast and reliable",
        "pain_points": [
            "Manual deployment process takes over 45 minutes each time",
            "Configuration drift between staging and production environments causes failures",
            "No automated rollback mechanism when deployments fail in production",
            "Team members must coordinate deployment windows via manual scheduling",
            "Missing deployment logs make it difficult to diagnose production issues",
            "Database migration scripts must be run manually on each environment",
            "Load balancer configuration requires manual DNS updates during releases",
        ],
        "gain_points": [
            "Reduce deployment time from 45 minutes to under 5 minutes per release",
            "Automated environment parity eliminates configuration drift completely",
            "One-click rollback restores previous version within 30 seconds of failure",
            "Self-service deployment scheduling eliminates coordination overhead",
            "Centralized deployment dashboard provides real-time visibility into release status",
            "Automated migration runner ensures database changes apply consistently",
            "Zero-downtime blue-green deploys eliminate customer-facing service interruptions",
        ],
        "title": "Deployment Pipeline Canvas",
    }

    def test_pdf_returns_bytes(self, client, auth_token):
        resp = client.post(
            "/api/generate-pdf",
            json=self.VALID_CANVAS,
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        # PDF files start with %PDF
        assert resp.content[:5] == b"%PDF-"

    def test_pdf_content_disposition(self, client, auth_token):
        resp = client.post(
            "/api/generate-pdf",
            json=self.VALID_CANVAS,
            headers=auth_headers(auth_token),
        )
        assert "Deployment_Pipeline_Canvas.pdf" in resp.headers.get("content-disposition", "")

    def test_pdf_invalid_canvas_rejected(self, client, auth_token):
        resp = client.post(
            "/api/generate-pdf",
            json={
                "job_description": "short",
                "pain_points": ["x"],
                "gain_points": ["y"],
                "title": "Test",
            },
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 400


class TestCSVExport:
    """Tests for POST /api/generate-csv."""

    VALID_CANVAS = TestPDFExport.VALID_CANVAS

    def test_csv_has_correct_structure(self, client, auth_token):
        resp = client.post(
            "/api/generate-csv",
            json=self.VALID_CANVAS,
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)

        # Header row
        assert rows[0] == ["section", "item_number", "content"]
        # Job description
        assert rows[1][0] == "job_description"
        # Pain points
        pain_rows = [r for r in rows if r[0] == "pain_point"]
        assert len(pain_rows) == 7
        # Gain points
        gain_rows = [r for r in rows if r[0] == "gain_point"]
        assert len(gain_rows) == 7

    def test_csv_content_disposition(self, client, auth_token):
        resp = client.post(
            "/api/generate-csv",
            json=self.VALID_CANVAS,
            headers=auth_headers(auth_token),
        )
        assert "Deployment_Pipeline_Canvas.csv" in resp.headers.get("content-disposition", "")

    def test_csv_invalid_canvas_rejected(self, client, auth_token):
        resp = client.post(
            "/api/generate-csv",
            json={
                "job_description": "short",
                "pain_points": ["x"],
                "gain_points": ["y"],
            },
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 400
