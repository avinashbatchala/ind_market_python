from __future__ import annotations

from typing import Iterable, List, Optional

from sqlalchemy import select, func, delete
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
                .order_by(WatchStock.symbol.asc(), TickerIndex.index_symbol.asc())
            )
            rows = session.execute(stmt).all()
        grouped: dict[int, dict] = {}
        for row in rows:
            item = grouped.get(row.id)
            if item is None:
                item = {
                    "id": row.id,
                    "symbol": row.symbol,
                    "name": row.name,
                    "active": row.active,
                    "industry_index_symbols": [],
                }
                grouped[row.id] = item
            if row.index_symbol:
                item["industry_index_symbols"].append(row.index_symbol)
        return list(grouped.values())

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
                    WatchIndex.data_symbol,
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
                "data_symbol": row.data_symbol,
                "name": row.name,
                "active": row.active,
            }
            for row in rows
        ]

    def create(self, symbol: str, name: Optional[str], active: bool, data_symbol: Optional[str] = None) -> WatchIndex:
        with self.db.session() as session:
            index = WatchIndex(symbol=symbol, name=name, active=active, data_symbol=data_symbol)
            session.add(index)
            session.flush()
            return index

    def get(self, index_id: int) -> Optional[WatchIndex]:
        with self.db.session() as session:
            return session.get(WatchIndex, index_id)

    def get_fields(self, index_id: int) -> Optional[dict]:
        with self.db.session() as session:
            stmt = select(
                WatchIndex.id,
                WatchIndex.symbol,
                WatchIndex.data_symbol,
                WatchIndex.name,
                WatchIndex.active,
            ).where(WatchIndex.id == index_id)
            row = session.execute(stmt).first()
        if row is None:
            return None
        return {
            "id": row.id,
            "symbol": row.symbol,
            "data_symbol": row.data_symbol,
            "name": row.name,
            "active": row.active,
        }

    def update(
        self,
        index_id: int,
        symbol: Optional[str],
        name: Optional[str],
        active: Optional[bool],
        data_symbol: Optional[str],
    ) -> WatchIndex:
        with self.db.session() as session:
            index = session.get(WatchIndex, index_id)
            if index is None:
                raise ValueError("Index not found")
            if symbol is not None:
                index.symbol = symbol
            if data_symbol is not None:
                index.data_symbol = data_symbol
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

    def get_active_mappings(self) -> dict:
        with self.db.session() as session:
            stmt = select(
                WatchIndex.symbol,
                WatchIndex.data_symbol,
            ).where(WatchIndex.active.is_(True))
            rows = session.execute(stmt).all()
        return {row.symbol: (row.data_symbol or row.symbol) for row in rows}

    def get_active_data_symbols(self) -> List[str]:
        with self.db.session() as session:
            stmt = select(WatchIndex.data_symbol, WatchIndex.symbol).where(WatchIndex.active.is_(True))
            rows = session.execute(stmt).all()
        return [row.data_symbol or row.symbol for row in rows]

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
        rows = [{"symbol": symbol, "data_symbol": symbol, "active": True} for symbol in cleaned]
        stmt = pg_insert(WatchIndex).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["symbol"])
        with self.db.session() as session:
            session.execute(stmt)


class TickerIndexRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def set_mappings(self, stock_symbol: str, index_symbols: List[str]) -> None:
        cleaned = []
        seen = set()
        for symbol in index_symbols:
            if not symbol:
                continue
            if symbol in seen:
                continue
            cleaned.append(symbol)
            seen.add(symbol)

        with self.db.session() as session:
            existing = set(
                session.execute(
                    select(TickerIndex.index_symbol).where(TickerIndex.stock_symbol == stock_symbol)
                ).scalars()
            )
            desired = set(cleaned)
            to_remove = existing - desired
            to_add = desired - existing

            if to_remove:
                session.execute(
                    delete(TickerIndex).where(
                        TickerIndex.stock_symbol == stock_symbol,
                        TickerIndex.index_symbol.in_(to_remove),
                    )
                )

            if to_add:
                rows = [{"stock_symbol": stock_symbol, "index_symbol": symbol} for symbol in to_add]
                stmt = pg_insert(TickerIndex).values(rows)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=["stock_symbol", "index_symbol"],
                )
                session.execute(stmt)

    def ensure_mapping(self, stock_symbol: str, index_symbol: str) -> None:
        if not stock_symbol or not index_symbol:
            return
        with self.db.session() as session:
            stmt = pg_insert(TickerIndex).values(
                {"stock_symbol": stock_symbol, "index_symbol": index_symbol}
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=["stock_symbol", "index_symbol"])
            session.execute(stmt)

    def clear_mappings(self, stock_symbol: str) -> None:
        with self.db.session() as session:
            session.execute(delete(TickerIndex).where(TickerIndex.stock_symbol == stock_symbol))

    def get_mappings(self) -> dict:
        with self.db.session() as session:
            stmt = select(TickerIndex.stock_symbol, TickerIndex.index_symbol).order_by(
                TickerIndex.stock_symbol.asc(),
                TickerIndex.index_symbol.asc(),
            )
            rows = session.execute(stmt).all()
        mapping: dict[str, List[str]] = {}
        for stock, index in rows:
            mapping.setdefault(stock, []).append(index)
        return mapping

    def get_indices_for_stock(self, stock_symbol: str) -> List[str]:
        with self.db.session() as session:
            stmt = (
                select(TickerIndex.index_symbol)
                .where(TickerIndex.stock_symbol == stock_symbol)
                .order_by(TickerIndex.index_symbol.asc())
            )
            return list(session.execute(stmt).scalars().all())

    def move_stock_symbol(self, old_symbol: str, new_symbol: str) -> None:
        if old_symbol == new_symbol:
            return
        with self.db.session() as session:
            stmt = select(TickerIndex).where(TickerIndex.stock_symbol == old_symbol)
            rows = session.execute(stmt).scalars().all()
            for row in rows:
                row.stock_symbol = new_symbol

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
