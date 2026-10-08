"""users table + search_entries.user_id

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("google_sub", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False, server_default=""),
        sa.Column("name", sa.Text(), nullable=False, server_default=""),
        sa.Column("picture", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_sub"),
    )
    op.add_column(
        "search_entries", sa.Column("user_id", sa.Integer(), nullable=True)
    )
    op.create_index("ix_search_entries_user_id", "search_entries", ["user_id"])
    op.create_foreign_key(
        "fk_search_entries_user_id",
        "search_entries",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_search_entries_user_id", "search_entries", type_="foreignkey"
    )
    op.drop_index("ix_search_entries_user_id", table_name="search_entries")
    op.drop_column("search_entries", "user_id")
    op.drop_table("users")
