"""seed sector indices

Revision ID: 0004_seed_indices
Revises: 0003_seed_watchlists
Create Date: 2026-02-03 00:00:03
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_seed_indices"
down_revision = "0003_seed_watchlists"
branch_labels = None
depends_on = None

SECTOR_INDICES = [
    "NIFTYAUTO",
    "NIFTYFIN",
    "NIFTYFMCG",
    "NIFHEIN",
    "NIFTYIT",
    "NIFTYMED",
    "NIFTYMET",
    "NIPHARM",
    "NIFTYREAL",
    "NIFCODU",
    "NIFOILGAS",
]


def upgrade() -> None:
    conn = op.get_bind()
    for symbol in SECTOR_INDICES:
        conn.execute(
            sa.text(
                """
                INSERT INTO watch_indices (symbol, active)
                VALUES (:symbol, true)
                ON CONFLICT (symbol) DO NOTHING
                """
            ),
            {"symbol": symbol},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for symbol in SECTOR_INDICES:
        conn.execute(
            sa.text("DELETE FROM watch_indices WHERE symbol = :symbol"),
            {"symbol": symbol},
        )
