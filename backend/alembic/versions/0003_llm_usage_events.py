"""llm_usage_events table for per-query token usage dashboard

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("search_entry_id", sa.Integer(), nullable=True),
        sa.Column("query", sa.Text(), nullable=False, server_default=""),
        sa.Column("stage", sa.Text(), nullable=False, server_default=""),
        sa.Column("model", sa.Text(), nullable=False, server_default=""),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "completion_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_llm_usage_events_user_id", "llm_usage_events", ["user_id"]
    )
    op.create_index(
        "ix_llm_usage_events_search_entry_id",
        "llm_usage_events",
        ["search_entry_id"],
    )
    op.create_foreign_key(
        "fk_llm_usage_events_user_id",
        "llm_usage_events",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_llm_usage_events_search_entry_id",
        "llm_usage_events",
        "search_entries",
        ["search_entry_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_llm_usage_events_search_entry_id",
        "llm_usage_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_llm_usage_events_user_id", "llm_usage_events", type_="foreignkey"
    )
    op.drop_index("ix_llm_usage_events_search_entry_id", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_events_user_id", table_name="llm_usage_events")
    op.drop_table("llm_usage_events")
