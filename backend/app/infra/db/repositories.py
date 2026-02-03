from __future__ import annotations

from typing import Iterable, List, Optional

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.infra.db.models import Candle, ScannerSnapshot, BenchmarkState
from app.infra.db.session import Database


class CandleRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert_candles(self, symbol: str, timeframe: str, candles: Iterable[dict]) -> None:
        rows = []
        for candle in candles:
            rows.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "ts": candle["ts"],
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "volume": candle["volume"],
                    "source": candle.get("source", "groww"),
                }
            )
        if not rows:
            return

        stmt = pg_insert(Candle).values(rows)
        update_cols = {c: stmt.excluded[c] for c in ["open", "high", "low", "close", "volume", "source"]}
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "timeframe", "ts"],
            set_=update_cols,
        )

        with self.db.session() as session:
            session.execute(stmt)

    def get_latest_candles(self, symbol: str, timeframe: str, limit: int) -> List[Candle]:
        with self.db.session() as session:
            stmt = (
                select(Candle)
                .where(Candle.symbol == symbol, Candle.timeframe == timeframe)
                .order_by(Candle.ts.desc())
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()
        return list(reversed(rows))


class SnapshotRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save_snapshot(self, timeframe: str, ts, rows: Iterable[dict]) -> None:
        items = []
        for row in rows:
            items.append(
                {
                    "ts": ts,
                    "timeframe": timeframe,
                    "symbol": row["symbol"],
                    "rrs_vs_nifty": row["rrs_vs_nifty"],
                    "rrv_vs_nifty": row["rrv_vs_nifty"],
                    "rve_vs_nifty": row["rve_vs_nifty"],
                    "score_vs_nifty": row["score_vs_nifty"],
                    "signal_vs_nifty": row["signal_vs_nifty"],
                    "rrs_vs_bank": row["rrs_vs_bank"],
                    "rrv_vs_bank": row["rrv_vs_bank"],
                    "rve_vs_bank": row["rve_vs_bank"],
                    "score_vs_bank": row["score_vs_bank"],
                    "signal_vs_bank": row["signal_vs_bank"],
                    "best_signal": row["best_signal"],
                }
            )
        if not items:
            return

        stmt = pg_insert(ScannerSnapshot).values(items)
        update_cols = {c: stmt.excluded[c] for c in [
            "rrs_vs_nifty",
            "rrv_vs_nifty",
            "rve_vs_nifty",
            "score_vs_nifty",
            "signal_vs_nifty",
            "rrs_vs_bank",
            "rrv_vs_bank",
            "rve_vs_bank",
            "score_vs_bank",
            "signal_vs_bank",
            "best_signal",
        ]}
        stmt = stmt.on_conflict_do_update(
            index_elements=["ts", "timeframe", "symbol"],
            set_=update_cols,
        )
        with self.db.session() as session:
            session.execute(stmt)

    def get_latest_snapshot(self, timeframe: str) -> Optional[dict]:
        with self.db.session() as session:
            ts_stmt = select(func.max(ScannerSnapshot.ts)).where(ScannerSnapshot.timeframe == timeframe)
            ts = session.execute(ts_stmt).scalar()
            if ts is None:
                return None
            rows_stmt = (
                select(ScannerSnapshot)
                .where(ScannerSnapshot.timeframe == timeframe, ScannerSnapshot.ts == ts)
                .order_by(ScannerSnapshot.best_signal.asc(), ScannerSnapshot.symbol.asc())
            )
            rows = session.execute(rows_stmt).scalars().all()

            payload_rows = [
                {
                    "symbol": row.symbol,
                    "timeframe": row.timeframe,
                    "rrs_vs_nifty": row.rrs_vs_nifty,
                    "rrv_vs_nifty": row.rrv_vs_nifty,
                    "rve_vs_nifty": row.rve_vs_nifty,
                    "score_vs_nifty": row.score_vs_nifty,
                    "signal_vs_nifty": row.signal_vs_nifty,
                    "rrs_vs_bank": row.rrs_vs_bank,
                    "rrv_vs_bank": row.rrv_vs_bank,
                    "rve_vs_bank": row.rve_vs_bank,
                    "score_vs_bank": row.score_vs_bank,
                    "signal_vs_bank": row.signal_vs_bank,
                    "best_signal": row.best_signal,
                }
                for row in rows
            ]

            return {
                "timeframe": timeframe,
                "ts": ts.isoformat(),
                "rows": payload_rows,
            }


class BenchmarkRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save_states(self, timeframe: str, ts, states: Iterable[dict]) -> None:
        items = []
        for state in states:
            items.append(
                {
                    "ts": ts,
                    "timeframe": timeframe,
                    "benchmark": state["benchmark"],
                    "regime": state["regime"],
                    "trend": state["trend"],
                    "vol_expansion": state["vol_expansion"],
                    "participation": state["participation"],
                }
            )
        if not items:
            return

        stmt = pg_insert(BenchmarkState).values(items)
        update_cols = {c: stmt.excluded[c] for c in [
            "regime",
            "trend",
            "vol_expansion",
            "participation",
        ]}
        stmt = stmt.on_conflict_do_update(
            index_elements=["ts", "timeframe", "benchmark"],
            set_=update_cols,
        )
        with self.db.session() as session:
            session.execute(stmt)

    def get_latest_states(self, timeframe: str) -> Optional[dict]:
        with self.db.session() as session:
            ts_stmt = select(func.max(BenchmarkState.ts)).where(BenchmarkState.timeframe == timeframe)
            ts = session.execute(ts_stmt).scalar()
            if ts is None:
                return None
            rows_stmt = (
                select(BenchmarkState)
                .where(BenchmarkState.timeframe == timeframe, BenchmarkState.ts == ts)
                .order_by(BenchmarkState.benchmark.asc())
            )
            rows = session.execute(rows_stmt).scalars().all()

            payload_rows = [
                {
                    "benchmark": row.benchmark,
                    "timeframe": row.timeframe,
                    "ts": row.ts.isoformat(),
                    "regime": row.regime,
                    "trend": row.trend,
                    "vol_expansion": row.vol_expansion,
                    "participation": row.participation,
                }
                for row in rows
            ]

            return {
                "timeframe": timeframe,
                "ts": ts.isoformat(),
                "states": payload_rows,
            }
