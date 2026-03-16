"""
E2E test infrastructure for Value Proposition Canvas.

Starts real backend (uvicorn) and frontend (streamlit) subprocesses against
a temporary SQLite database. Provides authenticated Playwright pages.
"""

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENV_PYTHON = str(PROJECT_ROOT / ".venv" / "bin" / "python")

BACKEND_PORT = 18765
FRONTEND_PORT = 18766
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"
FRONTEND_URL = f"http://127.0.0.1:{FRONTEND_PORT}"

TEST_USER_EMAIL = "e2etest@example.com"
TEST_USER_PASSWORD = "E2eTestPass1!z"
TEST_USER_NAME = "E2E Tester"
ADMIN_EMAIL = "e2eadmin@example.com"
ADMIN_PASSWORD = "AdminPass1!z"


def _wait_for_url(url: str, timeout: float = 30.0, interval: float = 0.5) -> bool:
    """Poll a URL until it responds with 200 or timeout is reached."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(url, timeout=3.0)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def _run_db_script(db_path: str, script_body: str):
    """Run a Python script in a subprocess with DATABASE_URL pointed at db_path.

    The script_body should NOT set DATABASE_URL or import app modules — this
    wrapper handles that. The script receives a pre-configured engine,
    sessionmaker, Base, model classes, and hash_password.
    """
    preamble = (
        f'import os, sys\n'
        f'os.environ["DATABASE_URL"] = "sqlite:///{db_path}"\n'
        f'sys.path.insert(0, "{PROJECT_ROOT}")\n'
        f'from sqlalchemy import create_engine, event\n'
        f'from sqlalchemy.orm import sessionmaker\n'
        f'from app.database import Base\n'
        f'from app.models import User, Canvas, UserSession, CanvasShareLink\n'
        f'from app.auth import hash_password\n'
        f'engine = create_engine("sqlite:///{db_path}", connect_args={{"check_same_thread": False}})\n'
        f'@event.listens_for(engine, "connect")\n'
        f'def _pragma(conn, rec):\n'
        f'    c = conn.cursor()\n'
        f'    c.execute("PRAGMA foreign_keys=ON")\n'
        f'    c.close()\n'
    )
    full_script = preamble + textwrap.dedent(script_body)

    # Write to temp file to avoid quoting issues with -c
    script_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, prefix="vpc_e2e_script_"
    )
    script_file.write(full_script)
    script_file.close()

    try:
        result = subprocess.run(
            [VENV_PYTHON, script_file.name],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"DB script failed:\n{result.stderr}")
    finally:
        os.unlink(script_file.name)


@pytest.fixture(scope="session")
def _tmp_db():
    """Create a temporary directory for the test SQLite database."""
    tmpdir = tempfile.mkdtemp(prefix="vpc_e2e_")
    db_path = os.path.join(tmpdir, "e2e_test.db")
    yield db_path
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope="session")
def _backend(_tmp_db):
    """Start the FastAPI backend as a subprocess."""
    # Create tables first
    _run_db_script(_tmp_db, "Base.metadata.create_all(bind=engine)")

    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{_tmp_db}",
        "API_SECRET_KEY": "",
        "PYTHON_ENV": "development",
        "OPENAI_API_KEY": "",
        "RATE_LIMIT_AUTH": "1000/minute",
        "RATE_LIMIT_REGISTER": "1000/hour",
        "RATE_LIMIT_CANVAS": "1000/minute",
        "RATE_LIMIT_ADMIN": "1000/minute",
        "RATE_LIMIT_AI": "1000/minute",
        "RATE_LIMIT_VALIDATION": "1000/minute",
        "INACTIVITY_TIMEOUT_MINUTES": "60",
    }

    proc = subprocess.Popen(
        [
            VENV_PYTHON, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1",
            "--port", str(BACKEND_PORT),
            "--log-level", "warning",
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if not _wait_for_url(f"{BACKEND_URL}/", timeout=30):
        proc.kill()
        out = proc.stdout.read().decode() if proc.stdout else ""
        err = proc.stderr.read().decode() if proc.stderr else ""
        pytest.fail(f"Backend failed to start.\nstdout: {out}\nstderr: {err}")

    yield proc

    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def _frontend(_backend, _tmp_db):
    """Start the Streamlit frontend as a subprocess."""
    env = {
        **os.environ,
        "API_BASE_URL": BACKEND_URL,
        "API_SECRET_KEY": "",
        "FRONTEND_URL": FRONTEND_URL,
        "DATABASE_URL": f"sqlite:///{_tmp_db}",
    }

    proc = subprocess.Popen(
        [
            VENV_PYTHON, "-m", "streamlit", "run",
            str(PROJECT_ROOT / "ui" / "streamlit_app.py"),
            "--server.port", str(FRONTEND_PORT),
            "--server.address", "127.0.0.1",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--logger.level", "warning",
        ],
        cwd=str(PROJECT_ROOT / "ui"),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if not _wait_for_url(f"{FRONTEND_URL}/_stcore/health", timeout=45):
        proc.kill()
        out = proc.stdout.read().decode() if proc.stdout else ""
        err = proc.stderr.read().decode() if proc.stderr else ""
        pytest.fail(f"Frontend failed to start.\nstdout: {out}\nstderr: {err}")

    yield proc

    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def _seed_users(_backend, _tmp_db):
    """Register and activate users for E2E testing."""
    # Seed admin directly in DB
    _run_db_script(_tmp_db, textwrap.dedent(f"""\
        Session = sessionmaker(bind=engine)
        db = Session()
        admin = db.query(User).filter(User.email == "{ADMIN_EMAIL}").first()
        if not admin:
            admin = User(
                email="{ADMIN_EMAIL}",
                display_name="Admin",
                password_hash=hash_password("{ADMIN_PASSWORD}"),
                status="active",
                is_admin=True,
            )
            db.add(admin)
            db.commit()
        db.close()
    """))

    # Login as admin
    resp = httpx.post(f"{BACKEND_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    }, timeout=10.0)
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    admin_token = resp.json()["token"]

    # Register test user via API
    httpx.post(f"{BACKEND_URL}/api/auth/register", json={
        "email": TEST_USER_EMAIL,
        "display_name": TEST_USER_NAME,
        "password": TEST_USER_PASSWORD,
    }, timeout=10.0)

    # Approve test user via admin API
    users_resp = httpx.get(
        f"{BACKEND_URL}/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"status": "pending"},
        timeout=10.0,
    )
    assert users_resp.status_code == 200
    for u in users_resp.json():
        if u["email"] == TEST_USER_EMAIL:
            approve_resp = httpx.patch(
                f"{BACKEND_URL}/api/admin/users/{u['id']}/status",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"status": "active"},
                timeout=10.0,
            )
            assert approve_resp.status_code == 200, f"Approve failed: {approve_resp.text}"
            break

    yield {"admin_token": admin_token}


@pytest.fixture()
def auth_token(_seed_users) -> str:
    """Get a fresh auth token for the test user (function-scoped to avoid eviction)."""
    resp = httpx.post(f"{BACKEND_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
    }, timeout=10.0)
    assert resp.status_code == 200, f"Test user login failed: {resp.text}"
    return resp.json()["token"]


def login_on_page(page):
    """Log in as the test user on a Playwright page. Reusable after reloads."""
    page.goto(FRONTEND_URL, wait_until="networkidle")
    page.wait_for_timeout(2000)

    # Click "Sign In" tab if visible
    sign_in_tab = page.get_by_role("tab", name="Sign In")
    if sign_in_tab.is_visible():
        sign_in_tab.click()

    # Fill login form
    email_input = page.locator('input[aria-label="Email"]').first
    email_input.wait_for(state="visible", timeout=10000)
    email_input.fill(TEST_USER_EMAIL)

    password_input = page.locator('input[aria-label="Password"]').first
    password_input.fill(TEST_USER_PASSWORD)

    # Submit
    page.get_by_role("button", name="Sign In").click()

    # Wait for canvas to load
    page.wait_for_timeout(3000)
    page.locator(f"text={TEST_USER_NAME}").first.wait_for(state="visible", timeout=15000)


@pytest.fixture()
def authenticated_page(_frontend, _seed_users, page):
    """A Playwright page that is logged in as the test user."""
    login_on_page(page)
    yield page


@pytest.fixture()
def seeded_canvas(auth_token) -> dict:
    """Create a canvas with valid content via the API. Returns canvas data."""
    headers = {"Authorization": f"Bearer {auth_token}"}

    data = {
        "title": "E2E Test Canvas",
        "job_description": (
            "When deploying software updates, I want to automate the release "
            "pipeline so that deployments are fast, reliable, and stress-free"
        ),
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
    }

    resp = httpx.put(
        f"{BACKEND_URL}/api/canvases/current",
        headers=headers,
        json=data,
        timeout=10.0,
    )
    assert resp.status_code == 200
    return resp.json()
