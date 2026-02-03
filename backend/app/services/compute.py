from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.alignment import align_ohlcv
from app.domain.indicators.rrs_rrv_rve import classify, rrs, rrv, rve
from app.domain.universe import NIFTY_50, BANK_UNIVERSE
from app.infra.cache.redis_cache import RedisCache
from app.infra.db.repositories import CandleRepository, SnapshotRepository, BenchmarkRepository
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
    ) -> None:
        self.settings = settings
        self.candle_repo = candle_repo
        self.snapshot_repo = snapshot_repo
        self.benchmark_repo = benchmark_repo
        self.cache = cache
        self.broadcaster = broadcaster
        self.logger = get_logger(self.__class__.__name__)

    def compute_timeframe(self, timeframe: str) -> None:
        now = datetime.now(timezone.utc)

        nifty = self._load_candles(self.settings.nifty_symbol, timeframe)
        bank = self._load_candles(self.settings.banknifty_symbol, timeframe)
        if nifty is None or bank is None:
            self.logger.warning(
                "Missing benchmark candles",
                extra={"timeframe": timeframe, "nifty": nifty is not None, "bank": bank is not None},
            )
            return

        benchmark_states = [
            compute_benchmark_state(self.settings.nifty_symbol, nifty),
            compute_benchmark_state(self.settings.banknifty_symbol, bank),
        ]

        symbols = sorted(set(NIFTY_50) | set(BANK_UNIVERSE))
        rows: List[dict] = []

        for symbol in symbols:
            sym_data = self._load_candles(symbol, timeframe)
            if sym_data is None:
                self.logger.warning("Missing symbol candles", extra={"symbol": symbol, "timeframe": timeframe})
                continue

            row = self._compute_symbol(symbol, timeframe, sym_data, nifty, bank)
            if row is not None:
                rows.append(row)

        sig_rank = {"TRIGGER_LONG": 0, "WATCH": 1, "NEUTRAL": 2, "EXIT/AVOID": 3}
        rows.sort(
            key=lambda r: (
                sig_rank.get(r["best_signal"], 9),
                -max(r["score_vs_nifty"], r["score_vs_bank"]),
                -max(r["rve_vs_nifty"], r["rve_vs_bank"]),
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
        nifty: Dict[str, np.ndarray],
        bank: Dict[str, np.ndarray],
    ) -> Optional[dict]:
        sym_vs_nifty = self._compute_vs_benchmark(symbol, sym_data, nifty)
        sym_vs_bank = self._compute_vs_benchmark(symbol, sym_data, bank)
        if sym_vs_nifty is None or sym_vs_bank is None:
            return None

        best_signal = self._best_signal(sym_vs_nifty["signal"], sym_vs_bank["signal"])

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "rrs_vs_nifty": sym_vs_nifty["rrs"],
            "rrv_vs_nifty": sym_vs_nifty["rrv"],
            "rve_vs_nifty": sym_vs_nifty["rve"],
            "score_vs_nifty": sym_vs_nifty["score"],
            "signal_vs_nifty": sym_vs_nifty["signal"],
            "rrs_vs_bank": sym_vs_bank["rrs"],
            "rrv_vs_bank": sym_vs_bank["rrv"],
            "rve_vs_bank": sym_vs_bank["rve"],
            "score_vs_bank": sym_vs_bank["score"],
            "signal_vs_bank": sym_vs_bank["signal"],
            "best_signal": best_signal,
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

        score, signal = classify(rrs_val, rrv_val, rve_val, rrs_series)

        return {
            "symbol": symbol,
            "rrs": rrs_val,
            "rrv": rrv_val,
            "rve": rve_val,
            "score": score,
            "signal": signal,
        }

    def _best_signal(self, nifty_signal: str, bank_signal: str) -> str:
        priority = {"TRIGGER_LONG": 0, "WATCH": 1, "NEUTRAL": 2, "EXIT/AVOID": 3}
        if priority.get(nifty_signal, 9) <= priority.get(bank_signal, 9):
            return nifty_signal
        return bank_signal

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
