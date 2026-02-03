"""init

Revision ID: 0001_init
Revises: 
Create Date: 2026-02-03 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candles",
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("timeframe", sa.String(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("symbol", "timeframe", "ts"),
    )
    op.create_index("ix_candles_symbol_timeframe_ts", "candles", ["symbol", "timeframe", "ts"])
    op.create_index("ix_candles_timeframe_ts", "candles", ["timeframe", "ts"])

    op.create_table(
        "scanner_snapshot",
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timeframe", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("rrs_vs_nifty", sa.Float(), nullable=False),
        sa.Column("rrv_vs_nifty", sa.Float(), nullable=False),
        sa.Column("rve_vs_nifty", sa.Float(), nullable=False),
        sa.Column("score_vs_nifty", sa.Integer(), nullable=False),
        sa.Column("signal_vs_nifty", sa.String(), nullable=False),
        sa.Column("rrs_vs_bank", sa.Float(), nullable=False),
        sa.Column("rrv_vs_bank", sa.Float(), nullable=False),
        sa.Column("rve_vs_bank", sa.Float(), nullable=False),
        sa.Column("score_vs_bank", sa.Integer(), nullable=False),
        sa.Column("signal_vs_bank", sa.String(), nullable=False),
        sa.Column("best_signal", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("ts", "timeframe", "symbol"),
    )
    op.create_index("ix_snapshot_symbol_timeframe_ts", "scanner_snapshot", ["symbol", "timeframe", "ts"])
    op.create_index("ix_snapshot_timeframe_ts", "scanner_snapshot", ["timeframe", "ts"])

    op.create_table(
        "benchmark_state",
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timeframe", sa.String(), nullable=False),
        sa.Column("benchmark", sa.String(), nullable=False),
        sa.Column("regime", sa.String(), nullable=False),
        sa.Column("trend", sa.Float(), nullable=False),
        sa.Column("vol_expansion", sa.Float(), nullable=False),
        sa.Column("participation", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("ts", "timeframe", "benchmark"),
    )
    op.create_index("ix_benchmark_timeframe_ts", "benchmark_state", ["benchmark", "timeframe", "ts"])


def downgrade() -> None:
    op.drop_index("ix_benchmark_timeframe_ts", table_name="benchmark_state")
    op.drop_table("benchmark_state")
    op.drop_index("ix_snapshot_timeframe_ts", table_name="scanner_snapshot")
    op.drop_index("ix_snapshot_symbol_timeframe_ts", table_name="scanner_snapshot")
    op.drop_table("scanner_snapshot")
    op.drop_index("ix_candles_timeframe_ts", table_name="candles")
    op.drop_index("ix_candles_symbol_timeframe_ts", table_name="candles")
    op.drop_table("candles")
