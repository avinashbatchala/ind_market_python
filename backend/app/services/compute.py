from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.alignment import align_ohlcv
from app.domain.indicators.rrs_rrv_rve import classify, rrs, rrv, rve
from app.infra.cache.redis_cache import RedisCache
from app.infra.db.repositories import (
    CandleRepository,
    SnapshotRepository,
    BenchmarkRepository,
    WatchStockRepository,
    WatchIndexRepository,
    TickerIndexRepository,
)
from app.services.benchmarks import compute_benchmark_state


class ComputeService:
    def __init__(
        self,
        settings: Settings,
        candle_repo: CandleRepository,
        snapshot_repo: SnapshotRepository,
        benchmark_repo: BenchmarkRepository,
        cache: RedisCache,
        broadcaster,
        watch_stock_repo: WatchStockRepository,
        watch_index_repo: WatchIndexRepository,
        ticker_index_repo: TickerIndexRepository,
    ) -> None:
        self.settings = settings
        self.candle_repo = candle_repo
        self.snapshot_repo = snapshot_repo
        self.benchmark_repo = benchmark_repo
        self.cache = cache
        self.broadcaster = broadcaster
        self.watch_stock_repo = watch_stock_repo
        self.watch_index_repo = watch_index_repo
        self.ticker_index_repo = ticker_index_repo
        self.logger = get_logger(self.__class__.__name__)

    def compute_timeframe(self, timeframe: str) -> None:
        now = datetime.now(timezone.utc)

        benchmark_states: List[dict] = []
        benchmark_data: Dict[str, Dict[str, np.ndarray]] = {}

        base_benchmarks = set(self.settings.benchmark_symbols_list())
        watch_indices = set(self.watch_index_repo.get_active_symbols())
        benchmarks = base_benchmarks | watch_indices

        for benchmark in sorted(benchmarks):
            data = self._load_candles(benchmark, timeframe)
            if data is None:
                self.logger.warning(
                    "Missing benchmark candles",
                    extra={"timeframe": timeframe, "benchmark": benchmark},
                )
                benchmark_states.append(
                    {
                        "benchmark": benchmark,
                        "regime": "NO_DATA",
                        "trend": 0.0,
                        "vol_expansion": 0.0,
                        "participation": 0.0,
                    }
                )
                continue
            benchmark_data[benchmark] = data
            benchmark_states.append(compute_benchmark_state(benchmark, data))

        symbols = self._symbols()
        rows: List[dict] = []
        mapping = self.ticker_index_repo.get_mapping()

        for symbol in symbols:
            sym_data = self._load_candles(symbol, timeframe)
            if sym_data is None:
                self.logger.warning("Missing symbol candles", extra={"symbol": symbol, "timeframe": timeframe})
                continue

            benchmark_symbol = mapping.get(symbol, self.settings.nifty_symbol)
            benchmark = benchmark_data.get(benchmark_symbol)
            if benchmark is None:
                benchmark = self._load_candles(benchmark_symbol, timeframe)
                if benchmark is None:
                    self.logger.warning(
                        "Missing benchmark for symbol",
                        extra={"symbol": symbol, "benchmark": benchmark_symbol, "timeframe": timeframe},
                    )
                    continue
                benchmark_data[benchmark_symbol] = benchmark

            row = self._compute_symbol(symbol, timeframe, sym_data, benchmark, benchmark_symbol)
            if row is not None:
                rows.append(row)

        sig_rank = {
            "TRIGGER_LONG": 0,
            "TRIGGER_SHORT": 1,
            "WATCH": 2,
            "NEUTRAL": 3,
            "EXIT/AVOID": 4,
        }
        rows.sort(
            key=lambda r: (
                sig_rank.get(r["signal"], 9),
                -abs(r["rrs"]),
                -abs(r["rve"]),
            )
        )

        payload = {
            "timeframe": timeframe,
            "ts": now.isoformat(),
            "rows": rows,
        }

        self.cache.set_json(f"scanner:{timeframe}", payload)
        self.snapshot_repo.save_snapshot(timeframe, now, rows)

        bench_payload = {
            "timeframe": timeframe,
            "ts": now.isoformat(),
            "states": [
                {
                    "benchmark": s["benchmark"],
                    "timeframe": timeframe,
                    "ts": now.isoformat(),
                    "regime": s["regime"],
                    "trend": s["trend"],
                    "vol_expansion": s["vol_expansion"],
                    "participation": s["participation"],
                }
                for s in benchmark_states
            ],
        }

        self.cache.set_json(f"benchmarks:{timeframe}", bench_payload)
        self.benchmark_repo.save_states(timeframe, now, benchmark_states)

        # Broadcast to websocket clients
        if self.broadcaster:
            self.broadcaster.publish_threadsafe(timeframe, payload)

        self.logger.info(
            "Compute complete",
            extra={"timeframe": timeframe, "rows": len(rows)},
        )

    def _compute_symbol(
        self,
        symbol: str,
        timeframe: str,
        sym_data: Dict[str, np.ndarray],
        benchmark: Dict[str, np.ndarray],
        benchmark_symbol: str,
    ) -> Optional[dict]:
        sym_vs_benchmark = self._compute_vs_benchmark(symbol, sym_data, benchmark)
        if sym_vs_benchmark is None:
            return None

        signal = sym_vs_benchmark["signal"]

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "benchmark_symbol": benchmark_symbol,
            "rrs": sym_vs_benchmark["rrs"],
            "rrv": sym_vs_benchmark["rrv"],
            "rve": sym_vs_benchmark["rve"],
            "signal": signal,
            "rrs_vs_nifty": sym_vs_benchmark["rrs"],
            "rrv_vs_nifty": sym_vs_benchmark["rrv"],
            "rve_vs_nifty": sym_vs_benchmark["rve"],
            "score_vs_nifty": 0,
            "signal_vs_nifty": signal,
            "rrs_vs_bank": 0.0,
            "rrv_vs_bank": 0.0,
            "rve_vs_bank": 0.0,
            "score_vs_bank": 0,
            "signal_vs_bank": "NEUTRAL",
            "best_signal": signal,
        }

    def _compute_vs_benchmark(
        self,
        symbol: str,
        sym_data: Dict[str, np.ndarray],
        bench_data: Dict[str, np.ndarray],
    ) -> Optional[dict]:
        sym_aligned, bench_aligned, common_ts = align_ohlcv(sym_data, bench_data)
        if common_ts.size < 30:
            self.logger.warning(
                "Insufficient aligned candles",
                extra={"symbol": symbol, "aligned": int(common_ts.size)},
            )
            return None

        sym_ohlc = {k: sym_aligned[k] for k in ["high", "low", "close"]}
        ben_ohlc = {k: bench_aligned[k] for k in ["high", "low", "close"]}

        rrs_series = rrs(sym_ohlc, ben_ohlc, length=12)
        rrv_series = rrv(sym_aligned["volume"], bench_aligned["volume"], length=12, smooth=3, use_log=True)
        rve_series = rve(sym_ohlc, ben_ohlc, length=12, atr_period=14, smooth_atr=1)

        rrs_val = float(rrs_series[-1])
        rrv_val = float(rrv_series[-1])
        rve_val = float(rve_series[-1])

        signal = classify(rrs_val, rrv_val, rve_val, rrs_series)

        return {
            "symbol": symbol,
            "rrs": rrs_val,
            "rrv": rrv_val,
            "rve": rve_val,
            "signal": signal,
        }

    def _symbols(self) -> List[str]:
        return self.watch_stock_repo.get_active_symbols()

    def _load_candles(self, symbol: str, timeframe: str) -> Optional[Dict[str, np.ndarray]]:
        payload = self.cache.get_json(f"candles:{symbol}:{timeframe}")
        if payload is None:
            records = self.candle_repo.get_latest_candles(symbol, timeframe, self.settings.compute_bars)
            if not records:
                return None
            payload = {
                "ts": [int(r.ts.timestamp()) for r in records],
                "open": [r.open for r in records],
                "high": [r.high for r in records],
                "low": [r.low for r in records],
                "close": [r.close for r in records],
                "volume": [r.volume for r in records],
            }

        aligned = {}
        for key, value in payload.items():
            dtype = "int64" if key == "ts" else float
            aligned[key] = np.asarray(value, dtype=dtype)
        return aligned
