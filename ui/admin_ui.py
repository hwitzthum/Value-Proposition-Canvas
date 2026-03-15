"""
Admin panel components for the main Streamlit UI.
Renders dashboard stats and user management within a tab.
"""

import logging
from typing import Optional

import pandas as pd
import streamlit as st

from admin_api import AdminAPIClient  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid actions per status (enforces transition rules in the UI)
# ---------------------------------------------------------------------------
_STATUS_ACTIONS = {
    "pending": [("Approve", "active"), ("Decline", "declined")],
    "active": [("Suspend", "paused")],
    "paused": [("Reactivate", "active")],
    # declined: dead end — no actions
}


# ---------------------------------------------------------------------------
# Confirmation dialogs
# ---------------------------------------------------------------------------

@st.dialog("Confirm Action")
def _confirm_status_change(client: AdminAPIClient, user_id: str, user_name: str,
                           new_status: str):
    """Dialog to confirm a status change."""
    action_labels = {
        "active": "approve",
        "paused": "suspend",
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
                st.error(result.get("error", "Action failed.") if result else "Action failed.")
    with c2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Reset Password")
def _reset_password_dialog(client: AdminAPIClient, user_id: str, user_name: str):
    """Dialog for admin to reset a user's password."""
    st.markdown(f"Reset password for **{user_name}**")
    st.caption("The user will be forced to change their password on next login.")

    new_password = st.text_input("New password", type="password",
                                  help="Min 10 chars, upper+lower+digit+special")
    confirm = st.text_input("Confirm password", type="password")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Reset", type="primary", use_container_width=True):
            if not new_password:
                st.error("Password is required.")
            elif new_password != confirm:
                st.error("Passwords do not match.")
            elif len(new_password) < 10:
                st.error("Password must be at least 10 characters.")
            else:
                result = client.reset_password(user_id, new_password)
                if result and "error" not in result:
                    st.toast("Password reset successfully.")
                    st.rerun()
                else:
                    st.error(result.get("error", "Reset failed.") if result else "Reset failed.")
    with c2:
        if st.button("Cancel", use_container_width=True, key="cancel_reset"):
            st.rerun()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def render_admin_dashboard(client: AdminAPIClient):
    """Render the admin dashboard with stat cards."""
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


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------

def render_admin_user_management(client: AdminAPIClient, current_admin_id: Optional[str] = None):
    """Render user management with status-aware action buttons."""
    status_filter = st.selectbox(
        "Filter by status",
        ["all", "pending", "active", "paused", "declined"],
        key="admin_status_filter",
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
        if st.button("Approve all pending", type="primary", key="admin_approve_all"):
            for u in pending_users:
                client.update_user_status(u["id"], "active")
            st.toast(f"Approved {len(pending_users)} user(s)")
            st.rerun()

    # Individual user actions
    st.markdown("---")
    user_options = {f"{u.get('display_name')} ({u.get('email')})": u for u in users}
    selected_name = st.selectbox("Select user for action", list(user_options.keys()),
                                  key="admin_user_select")

    if selected_name:
        user = user_options[selected_name]
        uid = user["id"]
        current_status = user["status"]
        display_name = user.get("display_name", "User")
        is_admin_user = user.get("is_admin", False)

        # No actions for admin users
        if is_admin_user:
            st.info("Admin users cannot be modified.")
            return

        # Status-aware action buttons
        actions = _STATUS_ACTIONS.get(current_status, [])
        if actions:
            cols = st.columns(len(actions) + 1)  # +1 for reset password
            for i, (label, target_status) in enumerate(actions):
                with cols[i]:
                    btn_type = "primary" if target_status == "active" else "secondary"
                    if st.button(label, key=f"admin_{target_status}_{uid}",
                                  type=btn_type, use_container_width=True):
                        _confirm_status_change(client, uid, display_name, target_status)

            # Reset password button (only for non-declined users)
            if current_status != "declined":
                with cols[-1]:
                    if st.button("Reset Password", key=f"admin_reset_pw_{uid}",
                                  use_container_width=True):
                        _reset_password_dialog(client, uid, display_name)
        elif current_status == "declined":
            st.caption("Declined users cannot be modified. They may re-register.")
