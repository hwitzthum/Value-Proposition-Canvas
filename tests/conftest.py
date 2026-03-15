"""
Shared test fixtures for the Value Proposition Canvas test suite.
Uses an in-memory SQLite database for speed and isolation.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Force test environment BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["API_SECRET_KEY"] = ""  # Disable API key auth in tests
os.environ["PYTHON_ENV"] = "development"
os.environ["OPENAI_API_KEY"] = ""  # Disable OpenAI in tests

from app.database import Base, get_db  # noqa: E402
from app.models import User, UserSession, Canvas  # noqa: E402
from app.auth import hash_password, create_session  # noqa: E402
from app.main import app  # noqa: E402


# Test database engine (SQLite in-memory per session)
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    """Get a test database session."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def active_user(db):
    """Create an active user and return (user, password)."""
    password = "TestPass1!xy"
    user = User(
        email="testuser@example.com",
        display_name="Test User",
        password_hash=hash_password(password),
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, password


@pytest.fixture
def admin_user(db):
    """Create an admin user and return (user, password)."""
    password = "AdminPass1!z"
    user = User(
        email="admin@example.com",
        display_name="Admin",
        password_hash=hash_password(password),
        status="active",
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, password


@pytest.fixture
def auth_token(client, active_user):
    """Get a valid auth token for the active_user."""
    user, password = active_user
    resp = client.post("/api/auth/login", json={
        "email": user.email,
        "password": password,
    })
    return resp.json()["token"]


@pytest.fixture
def admin_token(client, admin_user):
    """Get a valid auth token for the admin_user."""
    user, password = admin_user
    resp = client.post("/api/auth/login", json={
        "email": user.email,
        "password": password,
    })
    return resp.json()["token"]


def auth_headers(token: str) -> dict:
    """Helper to build Bearer auth headers."""
    return {"Authorization": f"Bearer {token}"}
