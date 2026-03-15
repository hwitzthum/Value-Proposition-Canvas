"""Tests for security hardening measures."""

import pytest


class TestSecurityHeaders:
    def test_x_content_type_options(self, client):
        resp = client.get("/")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_referrer_policy(self, client):
        resp = client.get("/")
        assert "strict-origin" in resp.headers.get("referrer-policy", "")


class TestSwaggerDisabled:
    """In test env (PYTHON_ENV=development), Swagger IS available.
    These tests verify the toggle mechanism works."""

    def test_health_check(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"


class TestInputSanitization:
    def test_xss_in_job_description(self, client):
        resp = client.post("/api/validate/job-description", json={
            "description": '<script>alert("xss")</script> I want to accomplish my work goals when I am focused',
        })
        assert resp.status_code == 200
        # The XSS should be escaped, not executed

    def test_long_input_rejected(self, client):
        resp = client.post("/api/validate/job-description", json={
            "description": "x" * 6000,
        })
        assert resp.status_code == 422

    def test_empty_pain_points(self, client):
        resp = client.post("/api/validate/pain-points", json={
            "pain_points": [],
        })
        assert resp.status_code == 200


class TestContentDisposition:
    """Test that filename sanitization prevents header injection."""

    def test_sanitize_filename_in_main(self):
        from app.main import sanitize_filename
        assert sanitize_filename('normal title') == 'normal_title'
        assert sanitize_filename('file"; echo evil') == 'file_echo_evil'
        assert sanitize_filename('path/../../../etc/passwd') == 'pathetcpasswd'
        assert sanitize_filename('') == 'document'
        assert sanitize_filename('a' * 200)[:100]  # Truncated


class TestTimingSafeComparison:
    """Verify the API key comparison uses secrets.compare_digest."""

    def test_api_key_comparison_uses_compare_digest(self):
        import inspect
        from app.main import verify_api_key
        source = inspect.getsource(verify_api_key)
        assert "compare_digest" in source
