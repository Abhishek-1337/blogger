"""create search_entries table

Revision ID: 0001
Revises:
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("research_brief", sa.Text(), nullable=False, server_default=""),
        sa.Column("outline", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("sections", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "outline_approved", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "outline_revisions", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("outline_feedback", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("search_entries")
