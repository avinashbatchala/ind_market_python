from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, List

import numpy as np

from app.core.config import Settings
from app.core.logging import get_logger
from app.infra.db.repositories import CandleRepository, WatchStockRepository, WatchIndexRepository, TickerIndexRepository
from app.infra.cache.redis_cache import RedisCache
from app.infra.groww.client import GrowwClient, TIMEFRAME_INTERVALS
from app.services.rate_limit import RateLimiter
from app.services.retries import RetryPolicy
from app.services.timeframes import timeframe_to_minutes


class IngestionService:
    def __init__(
        self,
        settings: Settings,
        groww_client: GrowwClient,
        candle_repo: CandleRepository,
        cache: RedisCache,
        rate_limiter: RateLimiter,
        retry_policy: RetryPolicy,
        watch_stock_repo: WatchStockRepository,
        watch_index_repo: WatchIndexRepository,
        ticker_index_repo: TickerIndexRepository,
    ) -> None:
        self.settings = settings
        self.groww_client = groww_client
        self.candle_repo = candle_repo
        self.cache = cache
        self.rate_limiter = rate_limiter
        self.retry_policy = retry_policy
        self.watch_stock_repo = watch_stock_repo
        self.watch_index_repo = watch_index_repo
        self.ticker_index_repo = ticker_index_repo
        self.logger = get_logger(self.__class__.__name__)

    def run_once(self, timeframe: str) -> None:
        symbols = self._symbols()
        interval = TIMEFRAME_INTERVALS.get(timeframe)
        if interval is None:
            self.logger.warning("Unknown timeframe", extra={"timeframe": timeframe})
            return

        now = datetime.now(ZoneInfo(self.settings.market_tz))
        minutes = timeframe_to_minutes(timeframe)
        bars = min(self.settings.ingest_bars, int(interval.max_days * 24 * 60 / minutes))
        start_time = now - timedelta(minutes=bars * minutes)

        self.logger.info(
            "Ingestion start",
            extra={
                "timeframe": timeframe,
                "symbols": len(symbols),
                "start_time": start_time.isoformat(),
                "end_time": now.isoformat(),
            },
        )

        for symbol in symbols:
            try:
                self.rate_limiter.acquire()
                candles = self.retry_policy.run(
                    self.groww_client.fetch_candles,
                    trading_symbol=symbol,
                    timeframe=timeframe,
                    start_time=start_time,
                    end_time=now,
                    exchange=self.settings.groww_exchange,
                    segment=self.settings.groww_segment,
                )
                if not candles:
                    self.logger.warning("No candles returned", extra={"symbol": symbol, "timeframe": timeframe})
                    continue

                self.candle_repo.upsert_candles(symbol, timeframe, candles)
                cache_payload = self._to_cache_payload(candles)
                self.cache.set_json(f"candles:{symbol}:{timeframe}", cache_payload)
                self.logger.info(
                    "Ingestion success",
                    extra={"symbol": symbol, "timeframe": timeframe, "candles": len(candles)},
                )
            except Exception as exc:
                self.logger.exception(
                    "Ingestion failed",
                    extra={"symbol": symbol, "timeframe": timeframe, "error": str(exc)},
                )

        self.logger.info("Ingestion complete", extra={"timeframe": timeframe})

    def _symbols(self) -> List[str]:
        stock_symbols = self.watch_stock_repo.get_active_symbols()
        index_symbols = self.watch_index_repo.get_active_symbols()
        mapped_indices = self.ticker_index_repo.get_index_symbols()
        symbols = set(stock_symbols)
        symbols.update(index_symbols)
        symbols.update(mapped_indices)
        symbols.update(self.settings.benchmark_symbols_list())
        return sorted(symbols)

    @staticmethod
    def _to_cache_payload(candles: List[dict]) -> Dict[str, List[float]]:
        ts = np.array([int(c["ts"].timestamp()) for c in candles], dtype="int64")
        return {
            "ts": ts.tolist(),
            "open": [c["open"] for c in candles],
            "high": [c["high"] for c in candles],
            "low": [c["low"] for c in candles],
            "close": [c["close"] for c in candles],
            "volume": [c["volume"] for c in candles],
        }
