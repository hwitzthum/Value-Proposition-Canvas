"""Share links for read-only canvas sharing.

Revision ID: 003_share_links
Revises: 002_auth_improvements
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa

revision = "003_share_links"
down_revision = "002_auth_improvements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "canvas_share_links",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("canvas_id", sa.CHAR(36), sa.ForeignKey("canvases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("share_token", sa.String(64), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.create_index("ix_canvas_share_links_share_token", "canvas_share_links", ["share_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_canvas_share_links_share_token", table_name="canvas_share_links")
    op.drop_table("canvas_share_links")
