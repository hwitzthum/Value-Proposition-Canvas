"""Initial schema – users, sessions, canvases.

Revision ID: 001_initial
Revises:
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _guid_col():
    """Return the right column type for UUID depending on dialect."""
    return sa.String(36)


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("approved_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_status", "users", ["status"])
    op.create_index("ix_users_email_status", "users", ["email", "status"])

    # --- user_sessions ---
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
    )
    op.create_index("ix_user_sessions_token", "user_sessions", ["token"])

    # --- canvases ---
    op.create_table(
        "canvases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False, server_default="Untitled Canvas"),
        sa.Column("job_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("pain_points", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("gain_points", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("wizard_step", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("job_validated", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("pains_validated", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("gains_validated", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_canvases_user_current", "canvases", ["user_id", "is_current"])


def downgrade() -> None:
    op.drop_table("canvases")
    op.drop_table("user_sessions")
    op.drop_table("users")
