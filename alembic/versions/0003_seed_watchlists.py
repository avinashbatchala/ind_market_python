"""seed watchlists from universe

Revision ID: 0003_seed_watchlists
Revises: 0002_watchlists
Create Date: 2026-02-03 00:00:02
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_seed_watchlists"
down_revision = "0002_watchlists"
branch_labels = None
depends_on = None

NIFTY_50 = [
    "ADANIPORTS",
    "APOLLOHOSP",
    "ASIANPAINT",
    "AXISBANK",
    "BAJAJFINSV",
    "BAJFINANCE",
    "BHARTIARTL",
    "BPCL",
    "BRITANNIA",
    "CIPLA",
    "COALINDIA",
    "DIVISLAB",
    "DRREDDY",
    "EICHERMOT",
    "GRASIM",
    "HCLTECH",
    "HDFCBANK",
    "HDFCLIFE",
    "HINDALCO",
    "HINDUNILVR",
    "ICICIBANK",
    "ITC",
    "JSWSTEEL",
    "KOTAKBANK",
    "LT",
    "M&M",
    "MARUTI",
    "NESTLEIND",
    "NTPC",
    "ONGC",
    "POWERGRID",
    "RELIANCE",
    "SBILIFE",
    "SBIN",
    "SUNPHARMA",
    "TATACONSUM",
    "TATAMOTORS",
    "TATASTEEL",
    "TECHM",
    "TITAN",
    "ULTRACEMCO",
    "UPL",
    "WIPRO",
    "HEROMOTOCO",
    "INDUSINDBK",
    "SHREECEM",
    "BAJAJ-AUTO",
    "ADANIENT",
    "HDFCAMC",
]

BANK_UNIVERSE = [
    "HDFCBANK",
    "ICICIBANK",
    "SBIN",
    "AXISBANK",
    "KOTAKBANK",
    "INDUSINDBK",
    "BANKBARODA",
    "PNB",
    "IDFCFIRSTB",
    "FEDERALBNK",
]


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO watch_indices (symbol, active)
            VALUES ('NIFTY', true), ('BANKNIFTY', true)
            ON CONFLICT (symbol) DO NOTHING
            """
        )
    )

    def insert_watch_stocks(symbols):
        for symbol in symbols:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO watch_stocks (symbol, active)
                    VALUES (:symbol, true)
                    ON CONFLICT (symbol) DO NOTHING
                    """
                ),
                {"symbol": symbol},
            )

    insert_watch_stocks(NIFTY_50)
    insert_watch_stocks(BANK_UNIVERSE)

    for symbol in set(NIFTY_50):
        conn.execute(
            sa.text(
                """
                INSERT INTO ticker_index (stock_symbol, index_symbol)
                VALUES (:symbol, 'NIFTY')
                ON CONFLICT (stock_symbol) DO NOTHING
                """
            ),
            {"symbol": symbol},
        )

    for symbol in set(BANK_UNIVERSE):
        conn.execute(
            sa.text(
                """
                INSERT INTO ticker_index (stock_symbol, index_symbol)
                VALUES (:symbol, 'BANKNIFTY')
                ON CONFLICT (stock_symbol) DO NOTHING
                """
            ),
            {"symbol": symbol},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for symbol in set(NIFTY_50) | set(BANK_UNIVERSE):
        conn.execute(
            sa.text("DELETE FROM ticker_index WHERE stock_symbol = :symbol"),
            {"symbol": symbol},
        )
        conn.execute(
            sa.text("DELETE FROM watch_stocks WHERE symbol = :symbol"),
            {"symbol": symbol},
        )
    conn.execute(sa.text("DELETE FROM watch_indices WHERE symbol IN ('NIFTY','BANKNIFTY')"))
