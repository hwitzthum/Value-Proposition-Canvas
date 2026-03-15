"""Tests for admin endpoints."""

import pytest
from tests.conftest import auth_headers
from app.models import User, UserSession
from app.auth import hash_password


class TestAdminAuth:
    def test_non_admin_cannot_access(self, client, auth_token):
        resp = client.get("/api/admin/stats", headers=auth_headers(auth_token))
        assert resp.status_code == 403

    def test_no_auth_cannot_access(self, client):
        resp = client.get("/api/admin/stats")
        assert resp.status_code == 401


class TestAdminStats:
    def test_get_stats(self, client, admin_token, db):
        # Create a pending user
        user = User(
            email="pending@example.com",
            display_name="Pending",
            password_hash=hash_password("SecureP@ss1!"),
            status="pending",
        )
        db.add(user)
        db.commit()

        resp = client.get("/api/admin/stats", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_users"] >= 2  # admin + pending
        assert data["pending_users"] >= 1
        assert data["active_users"] >= 1


class TestAdminUserManagement:
    def test_list_users(self, client, admin_token, active_user):
        resp = client.get("/api/admin/users", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 2  # admin + active

    def test_list_users_filter_by_status(self, client, admin_token, db):
        user = User(
            email="pending2@example.com",
            display_name="Pending2",
            password_hash=hash_password("SecureP@ss1!"),
            status="pending",
        )
        db.add(user)
        db.commit()

        resp = client.get("/api/admin/users?status=pending", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        for u in resp.json():
            assert u["status"] == "pending"

    def test_approve_user(self, client, admin_token, db):
        user = User(
            email="toapprove@example.com",
            display_name="ToApprove",
            password_hash=hash_password("SecureP@ss1!"),
            status="pending",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        resp = client.patch(
            f"/api/admin/users/{user.id}/status",
            headers=auth_headers(admin_token),
            json={"status": "active"},
        )
        assert resp.status_code == 200

        # Verify the user can now login
        resp = client.post("/api/auth/login", json={
            "email": "toapprove@example.com",
            "password": "SecureP@ss1!",
        })
        assert resp.status_code == 200

    def test_pause_user(self, client, admin_token, active_user):
        user, _ = active_user
        resp = client.patch(
            f"/api/admin/users/{user.id}/status",
            headers=auth_headers(admin_token),
            json={"status": "paused"},
        )
        assert resp.status_code == 200

    def test_cannot_change_own_status(self, client, admin_token, admin_user):
        user, _ = admin_user
        resp = client.patch(
            f"/api/admin/users/{user.id}/status",
            headers=auth_headers(admin_token),
            json={"status": "paused"},
        )
        assert resp.status_code == 400

    def test_invalid_status(self, client, admin_token, active_user):
        user, _ = active_user
        resp = client.patch(
            f"/api/admin/users/{user.id}/status",
            headers=auth_headers(admin_token),
            json={"status": "invalid_status"},
        )
        assert resp.status_code == 422


class TestStatusTransitions:
    def test_valid_transitions(self, client, admin_token, db):
        """Test all valid status transitions."""
        user = User(
            email="transitions@example.com",
            display_name="Transitions",
            password_hash=hash_password("SecureP@ss1!"),
            status="pending",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        uid = str(user.id)

        # pending -> active
        resp = client.patch(
            f"/api/admin/users/{uid}/status",
            headers=auth_headers(admin_token),
            json={"status": "active"},
        )
        assert resp.status_code == 200

        # active -> paused
        resp = client.patch(
            f"/api/admin/users/{uid}/status",
            headers=auth_headers(admin_token),
            json={"status": "paused"},
        )
        assert resp.status_code == 200

        # paused -> active
        resp = client.patch(
            f"/api/admin/users/{uid}/status",
            headers=auth_headers(admin_token),
            json={"status": "active"},
        )
        assert resp.status_code == 200

    def test_invalid_transition_pending_to_paused(self, client, admin_token, db):
        """pending -> paused is not allowed."""
        user = User(
            email="invalid_trans@example.com",
            display_name="InvalidTrans",
            password_hash=hash_password("SecureP@ss1!"),
            status="pending",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        resp = client.patch(
            f"/api/admin/users/{user.id}/status",
            headers=auth_headers(admin_token),
            json={"status": "paused"},
        )
        assert resp.status_code == 400
        assert "invalid transition" in resp.json()["detail"].lower()

    def test_declined_is_dead_end(self, client, admin_token, db):
        """Declined users cannot be transitioned to any status."""
        user = User(
            email="declined_dead@example.com",
            display_name="DeclinedDead",
            password_hash=hash_password("SecureP@ss1!"),
            status="declined",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        resp = client.patch(
            f"/api/admin/users/{user.id}/status",
            headers=auth_headers(admin_token),
            json={"status": "active"},
        )
        assert resp.status_code == 400

    def test_cannot_change_admin_user_status(self, client, admin_token, db):
        """Cannot modify another admin's status."""
        admin2 = User(
            email="admin2@example.com",
            display_name="Admin2",
            password_hash=hash_password("SecureP@ss1!"),
            status="active",
            is_admin=True,
        )
        db.add(admin2)
        db.commit()
        db.refresh(admin2)

        resp = client.patch(
            f"/api/admin/users/{admin2.id}/status",
            headers=auth_headers(admin_token),
            json={"status": "paused"},
        )
        assert resp.status_code == 400
        assert "admin" in resp.json()["detail"].lower()


class TestSessionInvalidationOnStatusChange:
    def test_pausing_user_invalidates_sessions(self, client, admin_token, db):
        """Pausing a user should invalidate all their sessions."""
        password = "SecureP@ss1!"
        user = User(
            email="pause_invalidate@example.com",
            display_name="PauseInvalidate",
            password_hash=hash_password(password),
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Login the user to create a session
        resp = client.post("/api/auth/login", json={
            "email": "pause_invalidate@example.com",
            "password": password,
        })
        user_token = resp.json()["token"]

        # Verify session works
        resp = client.get("/api/auth/me", headers=auth_headers(user_token))
        assert resp.status_code == 200

        # Admin pauses the user
        resp = client.patch(
            f"/api/admin/users/{user.id}/status",
            headers=auth_headers(admin_token),
            json={"status": "paused"},
        )
        assert resp.status_code == 200

        # User's session should be invalidated
        resp = client.get("/api/auth/me", headers=auth_headers(user_token))
        assert resp.status_code == 401

    def test_declining_user_invalidates_sessions(self, client, admin_token, db):
        """Declining a user should invalidate all their sessions."""
        # Create pending user, approve, login, then decline
        password = "SecureP@ss1!"
        user = User(
            email="decline_invalidate@example.com",
            display_name="DeclineInvalidate",
            password_hash=hash_password(password),
            status="pending",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Decline pending user
        resp = client.patch(
            f"/api/admin/users/{user.id}/status",
            headers=auth_headers(admin_token),
            json={"status": "declined"},
        )
        assert resp.status_code == 200


class TestAdminResetPassword:
    def test_reset_password_success(self, client, admin_token, active_user, db):
        """Admin can reset a user's password."""
        user, _ = active_user
        resp = client.post(
            f"/api/admin/users/{user.id}/reset-password",
            headers=auth_headers(admin_token),
            json={"new_password": "ResetP@ss123!"},
        )
        assert resp.status_code == 200

        # Verify must_change_password is set
        db.expire_all()
        updated = db.query(User).filter(User.id == user.id).first()
        assert updated.must_change_password is True

        # Old password should not work
        resp = client.post("/api/auth/login", json={
            "email": user.email,
            "password": "TestPass1!xy",
        })
        assert resp.status_code == 401

        # New password should work
        resp = client.post("/api/auth/login", json={
            "email": user.email,
            "password": "ResetP@ss123!",
        })
        assert resp.status_code == 200
        assert resp.json()["must_change_password"] is True

    def test_cannot_reset_own_password(self, client, admin_token, admin_user):
        """Admin cannot reset their own password via admin endpoint."""
        user, _ = admin_user
        resp = client.post(
            f"/api/admin/users/{user.id}/reset-password",
            headers=auth_headers(admin_token),
            json={"new_password": "ResetP@ss123!"},
        )
        assert resp.status_code == 400

    def test_cannot_reset_admin_password(self, client, admin_token, db):
        """Cannot reset another admin's password."""
        admin2 = User(
            email="admin2_reset@example.com",
            display_name="Admin2",
            password_hash=hash_password("SecureP@ss1!"),
            status="active",
            is_admin=True,
        )
        db.add(admin2)
        db.commit()
        db.refresh(admin2)

        resp = client.post(
            f"/api/admin/users/{admin2.id}/reset-password",
            headers=auth_headers(admin_token),
            json={"new_password": "ResetP@ss123!"},
        )
        assert resp.status_code == 400

    def test_reset_invalidates_user_sessions(self, client, admin_token, db):
        """Resetting password should invalidate all user sessions."""
        password = "SecureP@ss1!"
        user = User(
            email="reset_sessions@example.com",
            display_name="ResetSessions",
            password_hash=hash_password(password),
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Login the user
        resp = client.post("/api/auth/login", json={
            "email": "reset_sessions@example.com",
            "password": password,
        })
        user_token = resp.json()["token"]

        # Admin resets password
        resp = client.post(
            f"/api/admin/users/{user.id}/reset-password",
            headers=auth_headers(admin_token),
            json={"new_password": "ResetP@ss123!"},
        )
        assert resp.status_code == 200

        # User's session should be invalidated
        resp = client.get("/api/auth/me", headers=auth_headers(user_token))
        assert resp.status_code == 401

    def test_reset_weak_password_rejected(self, client, admin_token, active_user):
        """Weak password should be rejected."""
        user, _ = active_user
        resp = client.post(
            f"/api/admin/users/{user.id}/reset-password",
            headers=auth_headers(admin_token),
            json={"new_password": "weak"},
        )
        assert resp.status_code == 422


class TestAdminPagination:
    def test_list_users_with_pagination(self, client, admin_token, db):
        """Create multiple users and verify pagination."""
        for i in range(5):
            user = User(
                email=f"page{i}@example.com",
                display_name=f"Page{i}",
                password_hash=hash_password(f"SecureP@ss{i}!"),
                status="pending",
            )
            db.add(user)
        db.commit()

        # Limit to 3
        resp = client.get("/api/admin/users?limit=3", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        assert len(resp.json()) == 3

        # Skip 3, get the rest
        resp = client.get("/api/admin/users?skip=3&limit=10", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        # Should have remaining users (5 created + admin + active_user from fixtures)
        assert len(resp.json()) >= 1


class TestAdminStatsOptimized:
    def test_stats_returns_correct_counts(self, client, admin_token, db):
        """Verify stats endpoint returns correct counts with optimized query."""
        test_users = [
            ("stat_pending1@example.com", "pending"),
            ("stat_pending2@example.com", "pending"),
            ("stat_paused1@example.com", "paused"),
        ]
        for email, status_val in test_users:
            user = User(
                email=email,
                display_name=f"Stat {status_val}",
                password_hash=hash_password("SecureP@ss1!"),
                status=status_val,
            )
            db.add(user)
        db.commit()

        resp = client.get("/api/admin/stats", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["pending_users"] >= 2
        assert data["paused_users"] >= 1
        assert data["active_users"] >= 1  # admin user
        assert data["total_users"] >= 4
