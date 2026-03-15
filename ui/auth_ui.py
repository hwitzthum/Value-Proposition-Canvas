"""
Authentication UI components for Streamlit.
Handles login, registration, pending/blocked status screens.
"""

import os
import re
import logging

import httpx
import streamlit as st

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def _auth_request(endpoint: str, payload: dict) -> dict:
    """Make an auth API request."""
    try:
        resp = httpx.post(
            f"{API_BASE_URL}/api/auth/{endpoint}",
            json=payload,
            timeout=15.0,
        )
        return {"status_code": resp.status_code, **resp.json()}
    except Exception as e:
        return {"status_code": 0, "detail": f"Connection error: {e}"}


def check_auth() -> bool:
    """Check if the user is authenticated with an active session."""
    token = st.session_state.get("auth_token")
    if not token:
        return False

    try:
        resp = httpx.get(
            f"{API_BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        if resp.status_code == 200:
            st.session_state["auth_user"] = resp.json()
            return True
    except Exception:
        pass

    st.session_state.pop("auth_token", None)
    st.session_state.pop("auth_user", None)
    return False


def logout():
    """Log the user out."""
    token = st.session_state.get("auth_token")
    if token:
        try:
            httpx.post(
                f"{API_BASE_URL}/api/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
        except Exception:
            pass

    st.session_state.pop("auth_token", None)
    st.session_state.pop("auth_user", None)
    st.rerun()


def _password_strength(password: str) -> tuple:
    """Returns (score 0-4, label, color, width%)."""
    score = 0
    if len(password) >= 10:
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"[0-9]", password):
        score += 1
    if re.search(r"[^A-Za-z0-9]", password):
        score += 1

    labels = {0: "Too weak", 1: "Weak", 2: "Fair", 3: "Good", 4: "Strong"}
    colors = {
        0: "var(--color-error, #dc2626)",
        1: "var(--color-error, #dc2626)",
        2: "var(--color-warning, #d97706)",
        3: "var(--color-success, #059669)",
        4: "var(--color-success, #059669)",
    }
    return score, labels[score], colors[score], score * 25


def render_login_page():
    """Render the login/register page."""
    st.markdown("""
    <div class="auth-container">
        <h1>Value Proposition Canvas</h1>
        <p>Sign in to continue</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("Please enter email and password.")
                else:
                    result = _auth_request("login", {
                        "email": email,
                        "password": password,
                    })
                    if result.get("token"):
                        st.session_state["auth_token"] = result["token"]
                        st.session_state["auth_user"] = result.get("user")
                        st.rerun()
                    else:
                        st.error(result.get("detail", "Login failed."))

    with tab_register:
        reg_name = st.text_input("Display Name", placeholder="Your name", key="reg_name")
        reg_email = st.text_input("Email", placeholder="you@example.com", key="reg_email")
        reg_password = st.text_input(
            "Password", type="password", key="reg_pass",
            help="Min 10 chars, upper+lower+digit+special",
        )

        # Password strength meter (updates live outside form)
        if reg_password:
            score, label, color, width = _password_strength(reg_password)
            st.markdown(
                f'<div class="pw-strength">'
                f'<div class="pw-strength-bar">'
                f'<div class="pw-strength-fill" style="width:{width}%;background:{color}"></div>'
                f'</div>'
                f'<div class="pw-strength-text" style="color:{color}">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")

        if st.button("Create Account", use_container_width=True, key="reg_submit_btn"):
            if not reg_name or not reg_email or not reg_password:
                st.error("All fields are required.")
            elif reg_password != reg_confirm:
                st.error("Passwords do not match.")
            else:
                result = _auth_request("register", {
                    "email": reg_email,
                    "display_name": reg_name,
                    "password": reg_password,
                })
                if result.get("status_code") == 201:
                    st.success(
                        "Account created! An administrator will review your "
                        "registration. You'll be able to log in once approved."
                    )
                elif result.get("status_code") == 422:
                    detail = result.get("detail", "Invalid input.")
                    if isinstance(detail, list):
                        for err in detail:
                            st.error(err.get("msg", str(err)))
                    else:
                        st.error(str(detail))
                else:
                    msg = result.get("message") or result.get("detail", "Registration submitted.")
                    st.info(msg)


def render_pending_page():
    """Show when user account is pending approval."""
    st.markdown("""
    <div class="auth-status-page">
        <h2>Account Pending Approval</h2>
        <p>Your account has been created and is waiting for administrator approval.
           You'll be able to access the application once approved.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Sign Out", use_container_width=True):
        logout()


def render_blocked_page(status: str):
    """Show when user account is paused or declined."""
    messages = {
        "paused": ("Account Paused", "Your account has been temporarily paused by an administrator."),
        "declined": ("Account Declined", "Your registration has been declined by an administrator."),
    }
    title, desc = messages.get(status, ("Account Unavailable", "Contact an administrator."))

    st.markdown(f"""
    <div class="auth-status-page">
        <h2>{title}</h2>
        <p>{desc}</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Sign Out", use_container_width=True):
        logout()
