"""
Admin Dashboard -- Streamlit application for user management.
Deployed as a separate Render web service (vpc-admin).
"""

import os
import sys
import logging
from pathlib import Path

import httpx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from admin.admin_api import AdminAPIClient  # noqa: E402

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="VPC Admin",
    page_icon="⚙",
    layout="wide",
)

# Load shared CSS + admin overrides
_BASE_CSS = Path(__file__).parent.parent / "ui" / "assets" / "style.css"
_ADMIN_CSS = Path(__file__).parent.parent / "ui" / "assets" / "admin.css"
_css = ""
if _BASE_CSS.exists():
    _css += _BASE_CSS.read_text()
if _ADMIN_CSS.exists():
    _css += "\n" + _ADMIN_CSS.read_text()
if _css:
    st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)


# ── Auth ──

def admin_login():
    st.markdown("""
    <div class="auth-container">
        <h1>Admin Dashboard</h1>
        <p>Sign in with your admin account</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("admin_login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In", use_container_width=True)

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


# ── Confirmation Dialogs ──

@st.dialog("Confirm Action")
def _confirm_status_change(client: AdminAPIClient, user_id: str, user_name: str,
                           new_status: str):
    """Dialog to confirm a destructive status change."""
    action_labels = {
        "active": "approve",
        "paused": "pause",
        "declined": "decline",
    }
    action = action_labels.get(new_status, new_status)

    st.markdown(f"Are you sure you want to **{action}** user **{user_name}**?")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Confirm", type="primary", use_container_width=True):
            result = client.update_user_status(user_id, new_status)
            if result and "error" not in result:
                st.toast(f"User {action}d successfully.")
                st.rerun()
            else:
                st.error(result.get("error", "Action failed."))
    with c2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


# ── Dashboard ──

def render_dashboard(client: AdminAPIClient):
    stats = client.get_stats()
    if not stats:
        st.error("Failed to load statistics.")
        return

    cols = st.columns(4)
    metrics = [
        ("Total Users", stats.get("total_users", 0)),
        ("Pending", stats.get("pending_users", 0)),
        ("Active", stats.get("active_users", 0)),
        ("Total Canvases", stats.get("total_canvases", 0)),
    ]
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(
                f'<div class="admin-stat-card">'
                f'<div class="admin-stat-value">{value}</div>'
                f'<div class="admin-stat-label">{label}</div></div>',
                unsafe_allow_html=True,
            )

    if stats.get("paused_users") or stats.get("declined_users"):
        cols2 = st.columns(4)
        cols2[0].metric("Paused", stats.get("paused_users", 0))
        cols2[1].metric("Declined", stats.get("declined_users", 0))


# ── User Management ──

def render_user_management(client: AdminAPIClient):
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

    # Build dataframe
    rows = []
    for u in users:
        rows.append({
            "Name": u.get("display_name", ""),
            "Email": u.get("email", ""),
            "Status": u.get("status", ""),
            "Admin": "Yes" if u.get("is_admin") else "No",
            "Canvases": u.get("canvas_count", 0),
            "Created": u.get("created_at", "")[:10],
            "Last Login": (u.get("last_login_at") or "Never")[:10] if u.get("last_login_at") else "Never",
            "_id": u.get("id", ""),
        })

    df = pd.DataFrame(rows)
    display_df = df.drop(columns=["_id"])

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Admin": st.column_config.TextColumn("Admin", width="small"),
            "Canvases": st.column_config.NumberColumn("Canvases", width="small"),
        },
    )

    # Action section below dataframe
    st.markdown("### Actions")

    # Pending users: batch approve
    pending_users = [u for u in users if u.get("status") == "pending"]
    if pending_users:
        st.markdown(f"**{len(pending_users)} pending user(s)**")
        if st.button("Approve all pending", type="primary"):
            for u in pending_users:
                client.update_user_status(u["id"], "active")
            st.toast(f"Approved {len(pending_users)} user(s)")
            st.rerun()

    # Individual user actions
    st.markdown("---")
    user_options = {f"{u.get('display_name')} ({u.get('email')})": u for u in users}
    selected_name = st.selectbox("Select user for action", list(user_options.keys()))

    if selected_name:
        user = user_options[selected_name]
        uid = user["id"]
        current_status = user["status"]
        display_name = user.get("display_name", "User")

        col1, col2, col3 = st.columns(3)

        with col1:
            if current_status in ("pending", "paused", "declined"):
                if st.button("Approve", key=f"approve_{uid}", type="primary",
                              use_container_width=True):
                    _confirm_status_change(client, uid, display_name, "active")

        with col2:
            if current_status in ("pending", "active"):
                if st.button("Pause", key=f"pause_{uid}", use_container_width=True):
                    _confirm_status_change(client, uid, display_name, "paused")

        with col3:
            if current_status in ("pending", "active", "paused"):
                if st.button("Decline", key=f"decline_{uid}", use_container_width=True):
                    _confirm_status_change(client, uid, display_name, "declined")


# ── Main ──

def main():
    token = st.session_state.get("admin_token")
    if not token:
        admin_login()
        return

    admin_user = st.session_state.get("admin_user", {})

    with st.sidebar:
        st.markdown(f"**{admin_user.get('display_name', 'Admin')}**")
        st.caption(admin_user.get("email", ""))
        st.markdown("---")
        if st.button("Sign Out", use_container_width=True):
            admin_logout()

    client = AdminAPIClient(API_BASE_URL, token)

    tab_dashboard, tab_users = st.tabs(["Dashboard", "Users"])

    with tab_dashboard:
        render_dashboard(client)

    with tab_users:
        render_user_management(client)


if __name__ == "__main__":
    main()
