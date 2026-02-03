"""add data_symbol to watch_indices

Revision ID: 0005_index_data_symbol
Revises: 0004_seed_indices
Create Date: 2026-02-03 00:00:04
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_index_data_symbol"
down_revision = "0004_seed_indices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("watch_indices", sa.Column("data_symbol", sa.String(), nullable=True))
    op.execute(sa.text("UPDATE watch_indices SET data_symbol = symbol WHERE data_symbol IS NULL"))


def downgrade() -> None:
    op.drop_column("watch_indices", "data_symbol")
