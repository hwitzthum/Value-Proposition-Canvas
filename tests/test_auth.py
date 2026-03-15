"""Tests for authentication endpoints."""

import pytest
from tests.conftest import auth_headers


class TestRegistration:
    def test_register_success(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "new@example.com",
            "display_name": "New User",
            "password": "SecureP@ss1!",
        })
        assert resp.status_code == 201
        assert "message" in resp.json()

    def test_register_duplicate_email_no_enumeration(self, client, active_user):
        """Should return same message for duplicate emails (no enumeration)."""
        user, _ = active_user
        resp = client.post("/api/auth/register", json={
            "email": user.email,
            "display_name": "Dup User",
            "password": "SecureP@ss1!",
        })
        assert resp.status_code == 201
        # Same message as success to prevent enumeration
        assert "message" in resp.json()

    def test_register_weak_password(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "weak@example.com",
            "display_name": "Weak",
            "password": "short",
        })
        assert resp.status_code == 422

    def test_register_invalid_email(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "display_name": "Bad Email",
            "password": "SecureP@ss1!",
        })
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client, active_user):
        user, password = active_user
        resp = client.post("/api/auth/login", json={
            "email": user.email,
            "password": password,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["email"] == user.email

    def test_login_wrong_password(self, client, active_user):
        user, _ = active_user
        resp = client.post("/api/auth/login", json={
            "email": user.email,
            "password": "WrongP@ss1!",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_email(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "noone@example.com",
            "password": "AnyP@ss1!zz",
        })
        assert resp.status_code == 401

    def test_login_pending_user(self, client, db):
        from app.auth import hash_password
        from app.models import User
        user = User(
            email="pending@example.com",
            display_name="Pending",
            password_hash=hash_password("SecureP@ss1!"),
            status="pending",
        )
        db.add(user)
        db.commit()

        resp = client.post("/api/auth/login", json={
            "email": "pending@example.com",
            "password": "SecureP@ss1!",
        })
        assert resp.status_code == 403
        assert "pending" in resp.json()["detail"].lower()

    def test_account_lockout(self, client, active_user):
        """After 5 failed attempts, account should be locked."""
        user, _ = active_user
        for _ in range(5):
            client.post("/api/auth/login", json={
                "email": user.email,
                "password": "WrongP@ss1!",
            })
        # 6th attempt should get lockout message
        resp = client.post("/api/auth/login", json={
            "email": user.email,
            "password": "WrongP@ss1!",
        })
        assert resp.status_code == 429
        assert "locked" in resp.json()["detail"].lower()


class TestLogout:
    def test_logout_success(self, client, auth_token):
        resp = client.post(
            "/api/auth/logout",
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 200

    def test_logout_invalidates_token(self, client, auth_token):
        client.post("/api/auth/logout", headers=auth_headers(auth_token))
        # Token should now be invalid
        resp = client.get("/api/auth/me", headers=auth_headers(auth_token))
        assert resp.status_code == 401


class TestMe:
    def test_me_authenticated(self, client, auth_token, active_user):
        user, _ = active_user
        resp = client.get("/api/auth/me", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        assert resp.json()["email"] == user.email

    def test_me_no_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client):
        resp = client.get("/api/auth/me", headers=auth_headers("invalid"))
        assert resp.status_code == 401


class TestSessionCleanup:
    def test_expired_sessions_cleaned_on_login(self, client, db):
        """Logging in should clean up expired sessions for that user."""
        from datetime import datetime, timedelta, timezone
        from app.models import User, UserSession
        from app.auth import hash_password

        password = "TestPass1!xy"
        user = User(
            email="cleanup@example.com",
            display_name="Cleanup",
            password_hash=hash_password(password),
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create an expired session manually
        expired = UserSession(
            user_id=user.id,
            token="expired-token-xyz",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.add(expired)
        db.commit()

        # Login should trigger cleanup
        resp = client.post("/api/auth/login", json={
            "email": "cleanup@example.com",
            "password": password,
        })
        assert resp.status_code == 200

        # Expired session should be gone
        remaining = db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.token == "expired-token-xyz",
        ).first()
        assert remaining is None


class TestRegistrationRace:
    def test_duplicate_registration_returns_success_message(self, client, active_user):
        """Duplicate email registration should return same message (no enumeration)."""
        user, _ = active_user
        resp = client.post("/api/auth/register", json={
            "email": user.email,
            "display_name": "Dup",
            "password": "SecureP@ss1!",
        })
        # Should return 201 with same generic message
        assert resp.status_code == 201
        assert "message" in resp.json()
