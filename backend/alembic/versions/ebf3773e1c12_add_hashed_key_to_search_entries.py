"""add hashed key to search entries

Revision ID: ebf3773e1c12
Revises: 0003
Create Date: 2026-11-24 23:45:31.222437

"""

import hashlib

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ebf3773e1c12'
down_revision = '0003'
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "uq_search_entries_user_hashed_key"


def _hash_query(query: str) -> str:
    return hashlib.sha256((query or "").strip().lower().encode("utf-8")).hexdigest()


def upgrade() -> None:
    op.add_column('search_entries', sa.Column('hashed_key', sa.Text(), nullable=True))
    op.add_column('search_entries', sa.Column('last_updated', sa.DateTime(timezone=True), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, query FROM search_entries")).all()
    for row_id, query in rows:
        bind.execute(
            sa.text("UPDATE search_entries SET hashed_key = :hashed_key WHERE id = :entry_id"),
            {"hashed_key": _hash_query(query), "entry_id": row_id},
        )

    op.alter_column(
        'search_entries', 'hashed_key', existing_type=sa.Text(), nullable=False
    )
    op.create_unique_constraint(
        CONSTRAINT_NAME, 'search_entries', ['user_id', 'hashed_key']
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, 'search_entries', type_='unique')
    op.drop_column('search_entries', 'last_updated')
    op.drop_column('search_entries', 'hashed_key')
