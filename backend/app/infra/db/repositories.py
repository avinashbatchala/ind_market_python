from __future__ import annotations

from typing import Iterable, List, Optional

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.infra.db.models import (
    Candle,
    ScannerSnapshot,
    BenchmarkState,
    WatchStock,
    WatchIndex,
    TickerIndex,
)
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
            rrs = row.get("rrs", row.get("rrs_vs_nifty", 0.0))
            rrv = row.get("rrv", row.get("rrv_vs_nifty", 0.0))
            rve = row.get("rve", row.get("rve_vs_nifty", 0.0))
            signal = row.get("signal", row.get("signal_vs_nifty", "NEUTRAL"))
            benchmark_symbol = row.get("benchmark_symbol", "NIFTY")
            items.append(
                {
                    "ts": ts,
                    "timeframe": timeframe,
                    "symbol": row["symbol"],
                    "rrs_vs_nifty": rrs,
                    "rrv_vs_nifty": rrv,
                    "rve_vs_nifty": rve,
                    "score_vs_nifty": row.get("score_vs_nifty", 0),
                    "signal_vs_nifty": signal,
                    "rrs_vs_bank": row.get("rrs_vs_bank", 0.0),
                    "rrv_vs_bank": row.get("rrv_vs_bank", 0.0),
                    "rve_vs_bank": row.get("rve_vs_bank", 0.0),
                    "score_vs_bank": row.get("score_vs_bank", 0),
                    "signal_vs_bank": row.get("signal_vs_bank", "NEUTRAL"),
                    "best_signal": row.get("best_signal", signal),
                    "benchmark_symbol": benchmark_symbol,
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
            "benchmark_symbol",
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
                    "benchmark_symbol": row.benchmark_symbol,
                    "rrs": row.rrs_vs_nifty,
                    "rrv": row.rrv_vs_nifty,
                    "rve": row.rve_vs_nifty,
                    "signal": row.signal_vs_nifty,
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


class WatchStockRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list(self) -> List[dict]:
        with self.db.session() as session:
            stmt = (
                select(
                    WatchStock.id,
                    WatchStock.symbol,
                    WatchStock.name,
                    WatchStock.active,
                    TickerIndex.index_symbol,
                )
                .outerjoin(TickerIndex, WatchStock.symbol == TickerIndex.stock_symbol)
                .order_by(WatchStock.symbol.asc())
            )
            rows = session.execute(stmt).all()
        return [
            {
                "id": row.id,
                "symbol": row.symbol,
                "name": row.name,
                "active": row.active,
                "industry_index_symbol": row.index_symbol,
            }
            for row in rows
        ]

    def create(self, symbol: str, name: Optional[str], active: bool) -> WatchStock:
        with self.db.session() as session:
            stock = WatchStock(symbol=symbol, name=name, active=active)
            session.add(stock)
            session.flush()
            return stock

    def get(self, stock_id: int) -> Optional[WatchStock]:
        with self.db.session() as session:
            return session.get(WatchStock, stock_id)

    def get_fields(self, stock_id: int) -> Optional[dict]:
        with self.db.session() as session:
            stmt = select(
                WatchStock.id,
                WatchStock.symbol,
                WatchStock.name,
                WatchStock.active,
            ).where(WatchStock.id == stock_id)
            row = session.execute(stmt).first()
        if row is None:
            return None
        return {
            "id": row.id,
            "symbol": row.symbol,
            "name": row.name,
            "active": row.active,
        }

    def update(self, stock_id: int, symbol: Optional[str], name: Optional[str], active: Optional[bool]) -> WatchStock:
        with self.db.session() as session:
            stock = session.get(WatchStock, stock_id)
            if stock is None:
                raise ValueError("Stock not found")
            if symbol is not None:
                stock.symbol = symbol
            if name is not None:
                stock.name = name
            if active is not None:
                stock.active = active
            session.flush()
            return stock

    def delete(self, stock_id: int) -> None:
        with self.db.session() as session:
            stock = session.get(WatchStock, stock_id)
            if stock is None:
                raise ValueError("Stock not found")
            session.delete(stock)

    def get_active_symbols(self) -> List[str]:
        with self.db.session() as session:
            stmt = select(WatchStock.symbol).where(WatchStock.active.is_(True))
            rows = session.execute(stmt).scalars().all()
        return list(rows)

    def ensure_defaults(self, symbols: List[str]) -> None:
        cleaned = [s.strip().upper() for s in symbols if s.strip()]
        if not cleaned:
            return
        rows = [{"symbol": symbol, "active": True} for symbol in cleaned]
        stmt = pg_insert(WatchStock).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["symbol"])
        with self.db.session() as session:
            session.execute(stmt)


class WatchIndexRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list(self) -> List[dict]:
        with self.db.session() as session:
            stmt = (
                select(
                    WatchIndex.id,
                    WatchIndex.symbol,
                    WatchIndex.name,
                    WatchIndex.active,
                )
                .order_by(WatchIndex.symbol.asc())
            )
            rows = session.execute(stmt).all()
        return [
            {
                "id": row.id,
                "symbol": row.symbol,
                "name": row.name,
                "active": row.active,
            }
            for row in rows
        ]

    def create(self, symbol: str, name: Optional[str], active: bool) -> WatchIndex:
        with self.db.session() as session:
            index = WatchIndex(symbol=symbol, name=name, active=active)
            session.add(index)
            session.flush()
            return index

    def get(self, index_id: int) -> Optional[WatchIndex]:
        with self.db.session() as session:
            return session.get(WatchIndex, index_id)

    def update(self, index_id: int, symbol: Optional[str], name: Optional[str], active: Optional[bool]) -> WatchIndex:
        with self.db.session() as session:
            index = session.get(WatchIndex, index_id)
            if index is None:
                raise ValueError("Index not found")
            if symbol is not None:
                index.symbol = symbol
            if name is not None:
                index.name = name
            if active is not None:
                index.active = active
            session.flush()
            return index

    def delete(self, index_id: int) -> None:
        with self.db.session() as session:
            index = session.get(WatchIndex, index_id)
            if index is None:
                raise ValueError("Index not found")
            session.delete(index)

    def get_active_symbols(self) -> List[str]:
        with self.db.session() as session:
            stmt = select(WatchIndex.symbol).where(WatchIndex.active.is_(True))
            rows = session.execute(stmt).scalars().all()
        return list(rows)

    def exists(self, symbol: str) -> bool:
        with self.db.session() as session:
            stmt = (
                select(func.count())
                .select_from(WatchIndex)
                .where(WatchIndex.symbol == symbol, WatchIndex.active.is_(True))
            )
            return bool(session.execute(stmt).scalar())

    def ensure_defaults(self, symbols: List[str]) -> None:
        cleaned = [s.strip().upper() for s in symbols if s.strip()]
        if not cleaned:
            return
        rows = [{"symbol": symbol, "active": True} for symbol in cleaned]
        stmt = pg_insert(WatchIndex).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["symbol"])
        with self.db.session() as session:
            session.execute(stmt)


class TickerIndexRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def set_mapping(self, stock_symbol: str, index_symbol: str) -> None:
        with self.db.session() as session:
            stmt = select(TickerIndex).where(TickerIndex.stock_symbol == stock_symbol)
            mapping = session.execute(stmt).scalar_one_or_none()
            if mapping is None:
                mapping = TickerIndex(stock_symbol=stock_symbol, index_symbol=index_symbol)
                session.add(mapping)
            else:
                mapping.index_symbol = index_symbol

    def clear_mapping(self, stock_symbol: str) -> None:
        with self.db.session() as session:
            stmt = select(TickerIndex).where(TickerIndex.stock_symbol == stock_symbol)
            mapping = session.execute(stmt).scalar_one_or_none()
            if mapping is not None:
                session.delete(mapping)

    def get_mapping(self) -> dict:
        with self.db.session() as session:
            stmt = select(TickerIndex.stock_symbol, TickerIndex.index_symbol)
            rows = session.execute(stmt).all()
        return {stock: index for stock, index in rows}

    def get_index_for_stock(self, stock_symbol: str) -> Optional[str]:
        with self.db.session() as session:
            stmt = select(TickerIndex.index_symbol).where(TickerIndex.stock_symbol == stock_symbol)
            return session.execute(stmt).scalar_one_or_none()

    def move_index_symbol(self, old_symbol: str, new_symbol: str) -> None:
        with self.db.session() as session:
            stmt = select(TickerIndex).where(TickerIndex.index_symbol == old_symbol)
            rows = session.execute(stmt).scalars().all()
            for row in rows:
                row.index_symbol = new_symbol

    def get_index_symbols(self) -> List[str]:
        with self.db.session() as session:
            stmt = select(func.distinct(TickerIndex.index_symbol))
            rows = session.execute(stmt).scalars().all()
        return list(rows)
