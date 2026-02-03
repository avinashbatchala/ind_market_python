"""allow multiple index mappings per stock

Revision ID: 0006_multi_index_mapping
Revises: 0005_index_data_symbol
Create Date: 2026-02-03 00:00:05
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_multi_index_mapping"
down_revision = "0005_index_data_symbol"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ux_ticker_index_stock", "ticker_index", type_="unique")
    op.create_unique_constraint(
        "ux_ticker_index_stock_index",
        "ticker_index",
        ["stock_symbol", "index_symbol"],
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO watch_indices (symbol, active)
            VALUES ('NIFTY', true)
            ON CONFLICT (symbol) DO NOTHING
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO ticker_index (stock_symbol, index_symbol)
            SELECT symbol, 'NIFTY'
            FROM watch_stocks
            ON CONFLICT (stock_symbol, index_symbol) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM ticker_index a
            USING ticker_index b
            WHERE a.stock_symbol = b.stock_symbol
              AND a.id > b.id
            """
        )
    )
    op.drop_constraint("ux_ticker_index_stock_index", "ticker_index", type_="unique")
    op.create_unique_constraint("ux_ticker_index_stock", "ticker_index", ["stock_symbol"])
