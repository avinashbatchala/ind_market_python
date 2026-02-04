from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np

from app.core.config import Settings
from app.domain.alignment import align_ohlcv
from app.domain.indicators.rrs_rrv_rve import classify, rrs, rrv, rve
from app.infra.cache.redis_cache import RedisCache
from app.infra.db.repositories import CandleRepository, TickerIndexRepository, WatchIndexRepository
from app.services.candles_repo import CandlesRepo
from app.services.indices import get_associated_indices


class RelativeMetricsService:
    def __init__(
        self,
        settings: Settings,
        candle_repo: CandleRepository,
        ticker_index_repo: TickerIndexRepository,
        watch_index_repo: WatchIndexRepository,
        cache: RedisCache,
    ) -> None:
        self.settings = settings
        self.ticker_index_repo = ticker_index_repo
        self.watch_index_repo = watch_index_repo
        self.cache = cache
        self.candles_repo = CandlesRepo(candle_repo, cache)

    def get_metrics(self, symbol: str, timeframe: str, lookback: int) -> dict:
        cache_key = f"relative:{symbol}:{timeframe}:{lookback}"
        cached = self.cache.get_json(cache_key)
        if cached is not None:
            return cached

        stock_symbol = symbol.strip().upper()
        indices = get_associated_indices(stock_symbol, self.settings, self.ticker_index_repo)
        index_map = self.watch_index_repo.get_active_mappings()

        data_symbols = {stock_symbol}
        for idx in indices:
            data_symbols.add(index_map.get(idx, idx))

        candles = self.candles_repo.get_candles(sorted(data_symbols), timeframe, lookback)
        stock_data = candles.get(stock_symbol)

        rows: List[dict] = []
        for idx in indices:
            data_symbol = index_map.get(idx, idx)
            bench_data = candles.get(data_symbol)
            if stock_data is None or bench_data is None:
                rows.append(
                    {
                        "index": idx,
                        "rrs": None,
                        "rrv": None,
                        "rve": None,
                        "signal": "NO_DATA",
                        "timeframe": timeframe,
                        "updated_at": None,
                        "error": "Missing candles",
                    }
                )
                continue

            metric = compute_relative_metrics(stock_data, bench_data)
            if metric is None:
                rows.append(
                    {
                        "index": idx,
                        "rrs": None,
                        "rrv": None,
                        "rve": None,
                        "signal": "NO_DATA",
                        "timeframe": timeframe,
                        "updated_at": None,
                        "error": "Insufficient aligned candles",
                    }
                )
                continue

            rows.append(
                {
                    "index": idx,
                    "rrs": metric["rrs"],
                    "rrv": metric["rrv"],
                    "rve": metric["rve"],
                    "signal": metric["signal"],
                    "timeframe": timeframe,
                    "updated_at": metric["updated_at"],
                    "error": None,
                }
            )

        payload = {
            "symbol": stock_symbol,
            "timeframe": timeframe,
            "rows": rows,
        }
        self.cache.set_json(cache_key, payload, ttl=20)
        return payload


def compute_relative_metrics(
    stock_data: Dict[str, np.ndarray],
    bench_data: Dict[str, np.ndarray],
) -> Optional[dict]:
    sym_aligned, ben_aligned, common_ts = align_ohlcv(stock_data, bench_data)
    if common_ts.size < 30:
        return None

    sym_ohlc = {k: sym_aligned[k] for k in ["high", "low", "close"]}
    ben_ohlc = {k: ben_aligned[k] for k in ["high", "low", "close"]}

    rrs_series = rrs(sym_ohlc, ben_ohlc, length=12)
    rrv_series = rrv(sym_aligned["volume"], ben_aligned["volume"], length=12, smooth=3, use_log=True)
    rve_series = rve(sym_ohlc, ben_ohlc, length=12, atr_period=14, smooth_atr=1)

    rrs_val = float(rrs_series[-1])
    rrv_val = float(rrv_series[-1])
    rve_val = float(rve_series[-1])
    signal = classify(rrs_val, rrv_val, rve_val, rrs_series)

    updated_at = datetime.fromtimestamp(int(common_ts[-1]), tz=timezone.utc).isoformat()

    return {
        "rrs": rrs_val,
        "rrv": rrv_val,
        "rve": rve_val,
        "signal": signal,
        "updated_at": updated_at,
    }
