"""Auth improvements – must_change_password, last_activity_at.

Revision ID: 002_auth_improvements
Revises: 001_initial
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa

revision = "002_auth_improvements"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "user_sessions",
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_column("user_sessions", "last_activity_at")
    op.drop_column("users", "must_change_password")
