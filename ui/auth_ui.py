"""
Authentication UI components for Streamlit.
Handles login, registration, pending/blocked status screens.
"""

import os
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
    """Check if the user is authenticated with an active session.
    Returns True if authenticated, False otherwise."""
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

    # Token invalid – clear it
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


def render_login_page():
    """Render the login/register page."""

    st.markdown("""
    <div style="text-align: center; padding: 2rem 0 1rem;">
        <h1 style="font-size: 2rem; margin-bottom: 0.5rem;">Value Proposition Canvas</h1>
        <p style="color: #6b7280;">Sign in to continue</p>
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
                        detail = result.get("detail", "Login failed.")
                        st.error(detail)

    with tab_register:
        with st.form("register_form"):
            reg_name = st.text_input("Display Name", placeholder="Your name")
            reg_email = st.text_input("Email", placeholder="you@example.com", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_pass",
                                         help="Min 10 chars, upper+lower+digit+special")
            reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
            reg_submitted = st.form_submit_button("Create Account", use_container_width=True)

            if reg_submitted:
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
                        # Validation error
                        detail = result.get("detail", "Invalid input.")
                        if isinstance(detail, list):
                            for err in detail:
                                msg = err.get("msg", str(err))
                                st.error(msg)
                        else:
                            st.error(str(detail))
                    else:
                        msg = result.get("message") or result.get("detail", "Registration submitted.")
                        st.info(msg)


def render_pending_page():
    """Show when user account is pending approval."""
    st.markdown("""
    <div style="text-align: center; padding: 3rem 0;">
        <h2>Account Pending Approval</h2>
        <p style="color: #6b7280; max-width: 400px; margin: 0 auto;">
            Your account has been created and is waiting for administrator approval.
            You'll be able to access the application once approved.
        </p>
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
    <div style="text-align: center; padding: 3rem 0;">
        <h2>{title}</h2>
        <p style="color: #6b7280; max-width: 400px; margin: 0 auto;">{desc}</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Sign Out", use_container_width=True):
        logout()
