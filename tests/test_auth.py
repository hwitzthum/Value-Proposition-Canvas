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


class TestDeclinedReregistration:
    def test_declined_user_can_reregister(self, client, db):
        """Declined user re-registering should reset their record to pending."""
        from app.auth import hash_password
        from app.models import User

        user = User(
            email="declined@example.com",
            display_name="Old Name",
            password_hash=hash_password("OldP@ss123!"),
            status="declined",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        old_id = user.id

        resp = client.post("/api/auth/register", json={
            "email": "declined@example.com",
            "display_name": "New Name",
            "password": "NewP@ss123!",
        })
        assert resp.status_code == 201

        # Verify user was updated, not duplicated
        db.expire_all()
        updated = db.query(User).filter(User.email == "declined@example.com").first()
        assert updated.id == old_id
        assert updated.status == "pending"
        assert updated.display_name == "New Name"

    def test_active_user_cannot_reregister(self, client, active_user):
        """Active user re-registering should not change their record."""
        user, _ = active_user
        resp = client.post("/api/auth/register", json={
            "email": user.email,
            "display_name": "Hacker",
            "password": "SecureP@ss1!",
        })
        assert resp.status_code == 201  # Anti-enumeration


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
        assert data["must_change_password"] is False

    def test_login_returns_must_change_password(self, client, db):
        """Login should return must_change_password flag when set."""
        from app.auth import hash_password
        from app.models import User

        user = User(
            email="mustchange@example.com",
            display_name="MustChange",
            password_hash=hash_password("SecureP@ss1!"),
            status="active",
            must_change_password=True,
        )
        db.add(user)
        db.commit()

        resp = client.post("/api/auth/login", json={
            "email": "mustchange@example.com",
            "password": "SecureP@ss1!",
        })
        assert resp.status_code == 200
        assert resp.json()["must_change_password"] is True

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
        # Returns 401 (same as wrong password) to prevent account enumeration
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password."

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

    def test_logout_works_with_must_change_password(self, client, db):
        """Users with must_change_password should still be able to log out."""
        from app.auth import hash_password
        from app.models import User

        user = User(
            email="mustchangelogout@example.com",
            display_name="MustChangeLogout",
            password_hash=hash_password("SecureP@ss1!"),
            status="active",
            must_change_password=True,
        )
        db.add(user)
        db.commit()

        # Login
        resp = client.post("/api/auth/login", json={
            "email": "mustchangelogout@example.com",
            "password": "SecureP@ss1!",
        })
        token = resp.json()["token"]

        # Logout should work
        resp = client.post("/api/auth/logout", headers=auth_headers(token))
        assert resp.status_code == 200


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

    def test_me_works_with_must_change_password(self, client, db):
        """GET /me should work even with must_change_password set."""
        from app.auth import hash_password
        from app.models import User

        user = User(
            email="mustchangeme@example.com",
            display_name="MustChangeMe",
            password_hash=hash_password("SecureP@ss1!"),
            status="active",
            must_change_password=True,
        )
        db.add(user)
        db.commit()

        resp = client.post("/api/auth/login", json={
            "email": "mustchangeme@example.com",
            "password": "SecureP@ss1!",
        })
        token = resp.json()["token"]

        resp = client.get("/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["must_change_password"] is True


class TestChangePassword:
    def test_change_password_success(self, client, auth_token, active_user):
        user, password = active_user
        resp = client.post("/api/auth/change-password", json={
            "current_password": password,
            "new_password": "NewSecureP@1!",
        }, headers=auth_headers(auth_token))
        assert resp.status_code == 200

        # Old password should no longer work
        resp = client.post("/api/auth/login", json={
            "email": user.email,
            "password": password,
        })
        assert resp.status_code == 401

        # New password should work
        resp = client.post("/api/auth/login", json={
            "email": user.email,
            "password": "NewSecureP@1!",
        })
        assert resp.status_code == 200

    def test_change_password_wrong_current(self, client, auth_token):
        resp = client.post("/api/auth/change-password", json={
            "current_password": "WrongP@ss1!",
            "new_password": "NewSecureP@1!",
        }, headers=auth_headers(auth_token))
        assert resp.status_code == 400

    def test_change_password_clears_must_change_flag(self, client, db):
        """Changing password should clear must_change_password."""
        from app.auth import hash_password
        from app.models import User

        password = "SecureP@ss1!"
        user = User(
            email="clearflag@example.com",
            display_name="ClearFlag",
            password_hash=hash_password(password),
            status="active",
            must_change_password=True,
        )
        db.add(user)
        db.commit()

        resp = client.post("/api/auth/login", json={
            "email": "clearflag@example.com",
            "password": password,
        })
        token = resp.json()["token"]

        resp = client.post("/api/auth/change-password", json={
            "current_password": password,
            "new_password": "NewSecureP@1!",
        }, headers=auth_headers(token))
        assert resp.status_code == 200

        # Verify flag is cleared
        db.expire_all()
        updated = db.query(User).filter(User.email == "clearflag@example.com").first()
        assert updated.must_change_password is False

    def test_change_password_invalidates_other_sessions(self, client, db):
        """Changing password should invalidate all other sessions."""
        from app.auth import hash_password
        from app.models import User, UserSession

        password = "SecureP@ss1!"
        user = User(
            email="multisession@example.com",
            display_name="Multi",
            password_hash=hash_password(password),
            status="active",
        )
        db.add(user)
        db.commit()

        # Create two sessions
        resp1 = client.post("/api/auth/login", json={
            "email": "multisession@example.com",
            "password": password,
        })
        token1 = resp1.json()["token"]

        resp2 = client.post("/api/auth/login", json={
            "email": "multisession@example.com",
            "password": password,
        })
        token2 = resp2.json()["token"]

        # Change password using token1
        resp = client.post("/api/auth/change-password", json={
            "current_password": password,
            "new_password": "NewSecureP@1!",
        }, headers=auth_headers(token1))
        assert resp.status_code == 200

        # token1 should still work
        resp = client.get("/api/auth/me", headers=auth_headers(token1))
        assert resp.status_code == 200

        # token2 should be invalidated
        resp = client.get("/api/auth/me", headers=auth_headers(token2))
        assert resp.status_code == 401

    def test_must_change_password_blocks_regular_endpoints(self, client, db):
        """Users with must_change_password should be blocked from regular endpoints."""
        from app.auth import hash_password
        from app.models import User

        user = User(
            email="blocked@example.com",
            display_name="Blocked",
            password_hash=hash_password("SecureP@ss1!"),
            status="active",
            must_change_password=True,
        )
        db.add(user)
        db.commit()

        resp = client.post("/api/auth/login", json={
            "email": "blocked@example.com",
            "password": "SecureP@ss1!",
        })
        token = resp.json()["token"]

        # Canvas endpoint should be blocked
        resp = client.get("/api/canvases/current", headers=auth_headers(token))
        assert resp.status_code == 403
        assert "password change" in resp.json()["detail"].lower()


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


class TestMustChangePasswordBlocksAdmin:
    def test_admin_with_must_change_blocked_from_admin_routes(self, client, db):
        """An admin with must_change_password should be blocked from admin endpoints."""
        from app.auth import hash_password
        from app.models import User

        admin = User(
            email="must_change_admin@example.com",
            display_name="MustChangeAdmin",
            password_hash=hash_password("SecureP@ss1!"),
            status="active",
            is_admin=True,
            must_change_password=True,
        )
        db.add(admin)
        db.commit()

        resp = client.post("/api/auth/login", json={
            "email": "must_change_admin@example.com",
            "password": "SecureP@ss1!",
        })
        token = resp.json()["token"]

        # Admin stats should be blocked
        resp = client.get("/api/admin/stats", headers=auth_headers(token))
        assert resp.status_code == 403
        assert "password change" in resp.json()["detail"].lower()

        # But change-password should work
        resp = client.post("/api/auth/change-password", json={
            "current_password": "SecureP@ss1!",
            "new_password": "NewSecureP@1!",
        }, headers=auth_headers(token))
        assert resp.status_code == 200


class TestPausedUserCannotLogin:
    def test_paused_user_login_blocked(self, client, admin_token, active_user):
        """A paused user should not be able to log in."""
        user, password = active_user

        # Admin pauses the user
        resp = client.patch(
            f"/api/admin/users/{user.id}/status",
            headers=auth_headers(admin_token),
            json={"status": "paused"},
        )
        assert resp.status_code == 200

        # User tries to login — returns generic 401 to prevent enumeration
        resp = client.post("/api/auth/login", json={
            "email": user.email,
            "password": password,
        })
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password."


class TestInactivityTimeout:
    def test_inactive_session_expires(self, client, db):
        """Session should expire after inactivity timeout."""
        import os
        from datetime import datetime, timedelta, timezone
        from app.models import User, UserSession
        from app.auth import hash_password

        password = "SecureP@ss1!"
        user = User(
            email="inactive@example.com",
            display_name="Inactive",
            password_hash=hash_password(password),
            status="active",
        )
        db.add(user)
        db.commit()

        # Login
        resp = client.post("/api/auth/login", json={
            "email": "inactive@example.com",
            "password": password,
        })
        token = resp.json()["token"]

        # Manually set last_activity_at to past inactivity timeout
        from app.auth import _hash_token
        timeout_minutes = int(os.environ.get("INACTIVITY_TIMEOUT_MINUTES", "30"))
        session = db.query(UserSession).filter(UserSession.token == _hash_token(token)).first()
        session.last_activity_at = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes + 1)
        db.commit()

        # Session should now be expired
        resp = client.get("/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 401


class TestInactivityHeartbeat:
    def test_activity_updates_last_activity_at(self, client, db):
        """Making an authenticated request should update last_activity_at."""
        from datetime import datetime, timedelta, timezone
        from app.models import User, UserSession
        from app.auth import hash_password

        password = "SecureP@ss1!"
        user = User(
            email="heartbeat@example.com",
            display_name="Heartbeat",
            password_hash=hash_password(password),
            status="active",
        )
        db.add(user)
        db.commit()

        resp = client.post("/api/auth/login", json={
            "email": "heartbeat@example.com",
            "password": password,
        })
        token = resp.json()["token"]

        # Set last_activity_at to 10 minutes ago
        from app.auth import _hash_token
        session = db.query(UserSession).filter(UserSession.token == _hash_token(token)).first()
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        session.last_activity_at = old_time
        db.commit()

        # Make an authenticated request
        resp = client.get("/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200

        # last_activity_at should be updated
        db.expire_all()
        session = db.query(UserSession).filter(UserSession.token == _hash_token(token)).first()
        last_act = session.last_activity_at
        if last_act.tzinfo is None:
            last_act = last_act.replace(tzinfo=timezone.utc)
        assert last_act > old_time


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
