"""
Tests for BYOK (Bring Your Own Key) feature.
Covers encryption, CRUD endpoints, and key resolution.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from tests.conftest import auth_headers


class TestEncryption:
    """Test the encryption module."""

    def test_encrypt_decrypt_roundtrip(self):
        from app.encryption import encrypt_api_key, decrypt_api_key
        original = "sk-test1234567890abcdef"
        encrypted = encrypt_api_key(original)
        assert encrypted != original
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == original

    def test_decrypt_returns_none_on_bad_data(self):
        from app.encryption import decrypt_api_key
        result = decrypt_api_key("totally-not-encrypted")
        assert result is None

    def test_decrypt_returns_none_on_rotated_key(self):
        from app.encryption import encrypt_api_key, decrypt_api_key
        original = "sk-test1234567890abcdef"
        encrypted = encrypt_api_key(original)

        # Simulate key rotation by changing API_SECRET_KEY
        old_key = os.environ["API_SECRET_KEY"]
        os.environ["API_SECRET_KEY"] = "rotated-secret-key-different"
        try:
            result = decrypt_api_key(encrypted)
            assert result is None
        finally:
            os.environ["API_SECRET_KEY"] = old_key

    def test_encrypt_requires_api_secret_key(self):
        from app.encryption import encrypt_api_key
        old_key = os.environ.get("API_SECRET_KEY", "")
        os.environ["API_SECRET_KEY"] = ""
        try:
            with pytest.raises(RuntimeError):
                encrypt_api_key("sk-test")
        finally:
            os.environ["API_SECRET_KEY"] = old_key


class TestBYOKStatus:
    """Test GET /api/byok/status."""

    def test_status_no_key(self, client, auth_token):
        resp = client.get("/api/byok/status", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_key"] is False
        assert data["key_hint"] == ""
        assert data["key_valid"] is False

    def test_status_requires_auth(self, client):
        resp = client.get("/api/byok/status")
        assert resp.status_code == 401

    def test_status_with_key(self, client, auth_token):
        # Save a key first
        client.post(
            "/api/byok/save",
            json={"openai_api_key": "sk-testkey1234567890abcdef"},
            headers=auth_headers(auth_token),
        )
        resp = client.get("/api/byok/status", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_key"] is True
        assert data["key_hint"].endswith("cdef")
        assert data["key_valid"] is True


class TestBYOKSave:
    """Test POST /api/byok/save."""

    def test_save_valid_key(self, client, auth_token):
        resp = client.post(
            "/api/byok/save",
            json={"openai_api_key": "sk-testkey1234567890abcdef"},
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_key"] is True
        assert data["key_valid"] is True
        assert "cdef" in data["key_hint"]

    def test_save_requires_sk_prefix(self, client, auth_token):
        resp = client.post(
            "/api/byok/save",
            json={"openai_api_key": "not-a-valid-key-1234567890"},
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 422

    def test_save_requires_min_length(self, client, auth_token):
        resp = client.post(
            "/api/byok/save",
            json={"openai_api_key": "sk-short"},
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 422

    def test_save_requires_auth(self, client):
        resp = client.post(
            "/api/byok/save",
            json={"openai_api_key": "sk-testkey1234567890abcdef"},
        )
        assert resp.status_code == 401


class TestBYOKDelete:
    """Test DELETE /api/byok/delete."""

    def test_delete_key(self, client, auth_token):
        # Save first
        client.post(
            "/api/byok/save",
            json={"openai_api_key": "sk-testkey1234567890abcdef"},
            headers=auth_headers(auth_token),
        )
        # Delete
        resp = client.delete("/api/byok/delete", headers=auth_headers(auth_token))
        assert resp.status_code == 200

        # Verify it's gone
        status = client.get("/api/byok/status", headers=auth_headers(auth_token))
        assert status.json()["has_key"] is False

    def test_delete_requires_auth(self, client):
        resp = client.delete("/api/byok/delete")
        assert resp.status_code == 401


class TestBYOKTest:
    """Test POST /api/byok/test."""

    def test_test_no_key_returns_404(self, client, auth_token):
        resp = client.post("/api/byok/test", headers=auth_headers(auth_token))
        assert resp.status_code == 404

    @patch("app.routes.byok_routes.decrypt_api_key")
    def test_test_unreadable_key(self, mock_decrypt, client, auth_token, db):
        # Save a key, then mock decryption failure
        client.post(
            "/api/byok/save",
            json={"openai_api_key": "sk-testkey1234567890abcdef"},
            headers=auth_headers(auth_token),
        )
        mock_decrypt.return_value = None
        resp = client.post("/api/byok/test", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert "re-enter" in data["message"].lower()


class TestBYOKConfigIntegration:
    """Test that /api/config reflects BYOK state."""

    def test_config_no_user_key(self, client, auth_token):
        resp = client.get("/api/config", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        data = resp.json()
        # Without OPENAI_API_KEY set and no user key, ai_source should be "none"
        assert data["ai_source"] in ("none", "server_key")

    def test_config_with_user_key(self, client, auth_token):
        # Save a BYOK key
        client.post(
            "/api/byok/save",
            json={"openai_api_key": "sk-testkey1234567890abcdef"},
            headers=auth_headers(auth_token),
        )
        resp = client.get("/api/config", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["ai_source"] == "user_key"
        assert data["ai_enabled"] is True
