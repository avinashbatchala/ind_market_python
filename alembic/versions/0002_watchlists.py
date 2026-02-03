"""watchlists and ticker index

Revision ID: 0002_watchlists
Revises: 0001_init
Create Date: 2026-02-03 00:00:01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_watchlists"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watch_stocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("symbol", name="ux_watch_stocks_symbol"),
    )
    op.create_index("ix_watch_stocks_symbol", "watch_stocks", ["symbol"])

    op.create_table(
        "watch_indices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("symbol", name="ux_watch_indices_symbol"),
    )
    op.create_index("ix_watch_indices_symbol", "watch_indices", ["symbol"])

    op.create_table(
        "ticker_index",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stock_symbol", sa.String(), sa.ForeignKey("watch_stocks.symbol", ondelete="CASCADE"), nullable=False),
        sa.Column("index_symbol", sa.String(), sa.ForeignKey("watch_indices.symbol", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("stock_symbol", name="ux_ticker_index_stock"),
    )
    op.create_index("ix_ticker_index_stock_symbol", "ticker_index", ["stock_symbol"])
    op.create_index("ix_ticker_index_index_symbol", "ticker_index", ["index_symbol"])

    op.add_column("scanner_snapshot", sa.Column("benchmark_symbol", sa.String(), nullable=True))
    op.execute("UPDATE scanner_snapshot SET benchmark_symbol = 'NIFTY' WHERE benchmark_symbol IS NULL")
    op.alter_column("scanner_snapshot", "benchmark_symbol", nullable=False)


def downgrade() -> None:
    op.drop_column("scanner_snapshot", "benchmark_symbol")

    op.drop_index("ix_ticker_index_index_symbol", table_name="ticker_index")
    op.drop_index("ix_ticker_index_stock_symbol", table_name="ticker_index")
    op.drop_table("ticker_index")

    op.drop_index("ix_watch_indices_symbol", table_name="watch_indices")
    op.drop_table("watch_indices")

    op.drop_index("ix_watch_stocks_symbol", table_name="watch_stocks")
    op.drop_table("watch_stocks")
