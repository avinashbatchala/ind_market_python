from __future__ import annotations

from typing import Dict, List

import numpy as np

from app.infra.cache.redis_cache import RedisCache
from app.infra.db.models import Candle
from app.infra.db.repositories import CandleRepository


class CandlesRepo:
    def __init__(self, candle_repo: CandleRepository, cache: RedisCache) -> None:
        self.candle_repo = candle_repo
        self.cache = cache

    def get_candles(self, symbols: List[str], timeframe: str, limit: int) -> Dict[str, Dict[str, np.ndarray]]:
        results: Dict[str, Dict[str, np.ndarray]] = {}
        missing = []

        for symbol in symbols:
            cache_key = f"candles:{symbol}:{timeframe}:{limit}"
            cached = self.cache.get_json(cache_key)
            if cached is not None:
                results[symbol] = {
                    "ts": np.asarray(cached["ts"], dtype="int64"),
                    "open": np.asarray(cached["open"], dtype=float),
                    "high": np.asarray(cached["high"], dtype=float),
                    "low": np.asarray(cached["low"], dtype=float),
                    "close": np.asarray(cached["close"], dtype=float),
                    "volume": np.asarray(cached["volume"], dtype=float),
                }
                continue
            missing.append(symbol)

        if missing:
            batch = self.candle_repo.get_latest_candles_batch(missing, timeframe, limit)
            for symbol, records in batch.items():
                payload = _records_to_payload(records)
                results[symbol] = payload
                self.cache.set_json(
                    f"candles:{symbol}:{timeframe}:{limit}",
                    {
                        "ts": payload["ts"].tolist(),
                        "open": payload["open"].tolist(),
                        "high": payload["high"].tolist(),
                        "low": payload["low"].tolist(),
                        "close": payload["close"].tolist(),
                        "volume": payload["volume"].tolist(),
                    },
                    ttl=30,
                )

        return results


def _records_to_payload(records: List[Candle]) -> Dict[str, np.ndarray]:
    return {
        "ts": np.asarray([int(r.ts.timestamp()) for r in records], dtype="int64"),
        "open": np.asarray([r.open for r in records], dtype=float),
        "high": np.asarray([r.high for r in records], dtype=float),
        "low": np.asarray([r.low for r in records], dtype=float),
        "close": np.asarray([r.close for r in records], dtype=float),
        "volume": np.asarray([r.volume for r in records], dtype=float),
    }
