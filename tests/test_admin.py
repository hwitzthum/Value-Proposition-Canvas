"""Tests for admin endpoints."""

import pytest
from tests.conftest import auth_headers
from app.models import User
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
