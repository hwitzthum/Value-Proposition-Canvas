"""
Admin Dashboard – Streamlit application for user management.
Deployed as a separate Render web service (vpc-admin).
"""

import os
import sys
import logging

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from admin.admin_api import AdminAPIClient  # noqa: E402

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="VPC Admin Dashboard",
    page_icon="⚙️",
    layout="wide",
)


# ---- Auth ----
def admin_login():
    """Admin login form."""
    st.title("Admin Dashboard")
    st.markdown("Sign in with your admin account.")

    with st.form("admin_login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In")

        if submitted and email and password:
            try:
                resp = httpx.post(
                    f"{API_BASE_URL}/api/auth/login",
                    json={"email": email, "password": password},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    user = data.get("user", {})
                    if not user.get("is_admin"):
                        st.error("This account does not have admin privileges.")
                    else:
                        st.session_state["admin_token"] = data["token"]
                        st.session_state["admin_user"] = user
                        st.rerun()
                else:
                    st.error(resp.json().get("detail", "Login failed."))
            except Exception as e:
                st.error(f"Connection error: {e}")


def admin_logout():
    token = st.session_state.get("admin_token")
    if token:
        try:
            httpx.post(
                f"{API_BASE_URL}/api/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
        except Exception:
            pass
    st.session_state.pop("admin_token", None)
    st.session_state.pop("admin_user", None)
    st.rerun()


# ---- Dashboard ----
def render_dashboard(client: AdminAPIClient):
    """Render the admin dashboard."""
    stats = client.get_stats()
    if not stats:
        st.error("Failed to load statistics.")
        return

    st.subheader("Overview")
    cols = st.columns(4)
    cols[0].metric("Total Users", stats["total_users"])
    cols[1].metric("Pending", stats["pending_users"])
    cols[2].metric("Active", stats["active_users"])
    cols[3].metric("Total Canvases", stats["total_canvases"])

    if stats["paused_users"] or stats["declined_users"]:
        cols2 = st.columns(4)
        cols2[0].metric("Paused", stats["paused_users"])
        cols2[1].metric("Declined", stats["declined_users"])


def render_user_management(client: AdminAPIClient):
    """Render user management section."""
    st.subheader("User Management")

    status_filter = st.selectbox(
        "Filter by status",
        ["all", "pending", "active", "paused", "declined"],
    )

    users = client.list_users(
        status_filter=status_filter if status_filter != "all" else None
    )

    if not users:
        st.info("No users found.")
        return

    for user in users:
        with st.expander(
            f"{user['display_name']} ({user['email']}) — {user['status']}",
            expanded=(user["status"] == "pending"),
        ):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**Email:** {user['email']}")
                st.write(f"**Status:** {user['status']}")
                st.write(f"**Admin:** {'Yes' if user.get('is_admin') else 'No'}")
                st.write(f"**Canvases:** {user.get('canvas_count', 0)}")
                st.write(f"**Created:** {user['created_at']}")
                if user.get("last_login_at"):
                    st.write(f"**Last login:** {user['last_login_at']}")

            with col2:
                uid = user["id"]
                current_status = user["status"]

                if current_status == "pending":
                    if st.button("Approve", key=f"approve_{uid}", type="primary"):
                        result = client.update_user_status(uid, "active")
                        if result and "error" not in result:
                            st.success("User approved!")
                            st.rerun()
                        else:
                            st.error(result.get("error", "Failed"))

                    if st.button("Decline", key=f"decline_{uid}"):
                        result = client.update_user_status(uid, "declined")
                        if result and "error" not in result:
                            st.warning("User declined.")
                            st.rerun()
                        else:
                            st.error(result.get("error", "Failed"))

                elif current_status == "active":
                    if st.button("Pause", key=f"pause_{uid}"):
                        result = client.update_user_status(uid, "paused")
                        if result and "error" not in result:
                            st.warning("User paused.")
                            st.rerun()
                        else:
                            st.error(result.get("error", "Failed"))

                elif current_status in ("paused", "declined"):
                    if st.button("Reactivate", key=f"reactivate_{uid}", type="primary"):
                        result = client.update_user_status(uid, "active")
                        if result and "error" not in result:
                            st.success("User reactivated!")
                            st.rerun()
                        else:
                            st.error(result.get("error", "Failed"))


# ---- Main ----
def main():
    token = st.session_state.get("admin_token")
    if not token:
        admin_login()
        return

    admin_user = st.session_state.get("admin_user", {})

    # Sidebar
    with st.sidebar:
        st.title("Admin Panel")
        st.markdown(f"**{admin_user.get('display_name', 'Admin')}**")
        st.caption(admin_user.get("email", ""))
        if st.button("Sign Out"):
            admin_logout()

    client = AdminAPIClient(API_BASE_URL, token)

    tab_dashboard, tab_users = st.tabs(["Dashboard", "Users"])

    with tab_dashboard:
        render_dashboard(client)

    with tab_users:
        render_user_management(client)


if __name__ == "__main__":
    main()
