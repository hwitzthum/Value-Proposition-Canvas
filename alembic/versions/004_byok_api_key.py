"""Add encrypted_openai_key to users for BYOK.

Revision ID: 004_byok_api_key
Revises: 003_share_links
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa

revision = "004_byok_api_key"
down_revision = "003_share_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("encrypted_openai_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "encrypted_openai_key")
