"""split blog_contents from search_entries

Revision ID: 0004
Revises: ebf3773e1c12
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "ebf3773e1c12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_UNIQUE_CONSTRAINT = "uq_search_entries_user_hashed_key"
NEW_UNIQUE_CONSTRAINT = "uq_search_entries_user_content"
CONTENT_UNIQUE_CONSTRAINT = "uq_blog_contents_hashed_key"


def upgrade() -> None:
    op.create_table(
        "blog_contents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("hashed_key", sa.Text(), nullable=False),
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
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hashed_key", name=CONTENT_UNIQUE_CONSTRAINT),
    )

    op.add_column(
        "search_entries", sa.Column("content_id", sa.Integer(), nullable=True)
    )
    op.create_index("ix_search_entries_content_id", "search_entries", ["content_id"])
    op.create_foreign_key(
        "fk_search_entries_content_id",
        "search_entries",
        "blog_contents",
        ["content_id"],
        ["id"],
    )

    op.execute(
        """
        INSERT INTO blog_contents (
            hashed_key, query, research_brief, outline, sections,
            outline_approved, outline_revisions, outline_feedback,
            created_at, last_updated
        )
        SELECT DISTINCT ON (hashed_key)
            hashed_key, query, research_brief, outline, sections,
            outline_approved, outline_revisions, outline_feedback,
            created_at, last_updated
        FROM search_entries
        ORDER BY hashed_key, id DESC
        """
    )
    op.execute(
        """
        UPDATE search_entries AS se
        SET content_id = bc.id
        FROM blog_contents AS bc
        WHERE se.hashed_key = bc.hashed_key
        """
    )

    op.alter_column(
        "search_entries", "content_id", existing_type=sa.Integer(), nullable=False
    )
    op.drop_constraint(OLD_UNIQUE_CONSTRAINT, "search_entries", type_="unique")
    op.create_unique_constraint(
        NEW_UNIQUE_CONSTRAINT, "search_entries", ["user_id", "content_id"]
    )

    op.drop_column("search_entries", "last_updated")
    op.drop_column("search_entries", "outline_feedback")
    op.drop_column("search_entries", "outline_revisions")
    op.drop_column("search_entries", "outline_approved")
    op.drop_column("search_entries", "sections")
    op.drop_column("search_entries", "outline")
    op.drop_column("search_entries", "research_brief")
    op.drop_column("search_entries", "hashed_key")


def downgrade() -> None:
    op.add_column("search_entries", sa.Column("hashed_key", sa.Text(), nullable=True))
    op.add_column(
        "search_entries",
        sa.Column("research_brief", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "search_entries",
        sa.Column("outline", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "search_entries",
        sa.Column("sections", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "search_entries",
        sa.Column(
            "outline_approved", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "search_entries",
        sa.Column("outline_revisions", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "search_entries",
        sa.Column("outline_feedback", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "search_entries",
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        """
        UPDATE search_entries AS se
        SET
            hashed_key = bc.hashed_key,
            research_brief = bc.research_brief,
            outline = bc.outline,
            sections = bc.sections,
            outline_approved = bc.outline_approved,
            outline_revisions = bc.outline_revisions,
            outline_feedback = bc.outline_feedback,
            last_updated = bc.last_updated
        FROM blog_contents AS bc
        WHERE se.content_id = bc.id
        """
    )

    op.alter_column(
        "search_entries", "hashed_key", existing_type=sa.Text(), nullable=False
    )
    op.drop_constraint(NEW_UNIQUE_CONSTRAINT, "search_entries", type_="unique")
    op.create_unique_constraint(
        OLD_UNIQUE_CONSTRAINT, "search_entries", ["user_id", "hashed_key"]
    )
    op.drop_constraint(
        "fk_search_entries_content_id", "search_entries", type_="foreignkey"
    )
    op.drop_index("ix_search_entries_content_id", table_name="search_entries")
    op.drop_column("search_entries", "content_id")
    op.drop_table("blog_contents")
