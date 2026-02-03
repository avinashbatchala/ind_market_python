from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Candle(Base):
    __tablename__ = "candles"

    symbol = Column(String, primary_key=True)
    timeframe = Column(String, primary_key=True)
    ts = Column(DateTime(timezone=True), primary_key=True)

    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    source = Column(String, nullable=False, default="groww")

    __table_args__ = (
        Index("ix_candles_symbol_timeframe_ts", "symbol", "timeframe", "ts"),
        Index("ix_candles_timeframe_ts", "timeframe", "ts"),
    )


class ScannerSnapshot(Base):
    __tablename__ = "scanner_snapshot"

    ts = Column(DateTime(timezone=True), primary_key=True)
    timeframe = Column(String, primary_key=True)
    symbol = Column(String, primary_key=True)

    rrs_vs_nifty = Column(Float, nullable=False)
    rrv_vs_nifty = Column(Float, nullable=False)
    rve_vs_nifty = Column(Float, nullable=False)
    score_vs_nifty = Column(Integer, nullable=False)
    signal_vs_nifty = Column(String, nullable=False)

    rrs_vs_bank = Column(Float, nullable=False)
    rrv_vs_bank = Column(Float, nullable=False)
    rve_vs_bank = Column(Float, nullable=False)
    score_vs_bank = Column(Integer, nullable=False)
    signal_vs_bank = Column(String, nullable=False)

    best_signal = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_snapshot_symbol_timeframe_ts", "symbol", "timeframe", "ts"),
        Index("ix_snapshot_timeframe_ts", "timeframe", "ts"),
    )


class BenchmarkState(Base):
    __tablename__ = "benchmark_state"

    ts = Column(DateTime(timezone=True), primary_key=True)
    timeframe = Column(String, primary_key=True)
    benchmark = Column(String, primary_key=True)

    regime = Column(String, nullable=False)
    trend = Column(Float, nullable=False)
    vol_expansion = Column(Float, nullable=False)
    participation = Column(Float, nullable=False)

    __table_args__ = (
        Index("ix_benchmark_timeframe_ts", "benchmark", "timeframe", "ts"),
    )
