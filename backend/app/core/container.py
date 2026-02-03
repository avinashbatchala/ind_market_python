from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.config import Settings
from app.infra.cache.redis_cache import RedisCache
from app.infra.db.session import Database
from app.infra.db.repositories import (
    CandleRepository,
    SnapshotRepository,
    BenchmarkRepository,
    WatchStockRepository,
    WatchIndexRepository,
    TickerIndexRepository,
)
from app.infra.groww.client import GrowwClientFactory, GrowwClient
from app.services.broadcaster import Broadcaster
from app.services.compute import ComputeService
from app.services.ingestion import IngestionService
from app.services.rate_limit import RateLimiter
from app.services.retries import RetryPolicy
from app.services.scheduler import Scheduler


@dataclass
class Container:
    settings: Settings
    db: Database
    candle_repo: CandleRepository
    snapshot_repo: SnapshotRepository
    benchmark_repo: BenchmarkRepository
    watch_stock_repo: WatchStockRepository
    watch_index_repo: WatchIndexRepository
    ticker_index_repo: TickerIndexRepository
    redis_cache: RedisCache
    rate_limiter: RateLimiter
    retry_policy: RetryPolicy
    groww_client: GrowwClient
    broadcaster: Broadcaster
    ingestion_service: IngestionService
    compute_service: ComputeService
    scheduler: Scheduler

    async def start(self) -> None:
        import asyncio
        self.redis_cache.connect()
        self.broadcaster.set_loop(asyncio.get_running_loop())
        self.watch_index_repo.ensure_defaults(self.settings.benchmark_symbols_list())
        self.scheduler.start()

    async def stop(self) -> None:
        await self.scheduler.stop()
        self.redis_cache.close()
        self.db.dispose()


_container: Optional[Container] = None


def build_container() -> Container:
    settings = Settings()
    db = Database(settings.database_url)

    candle_repo = CandleRepository(db)
    snapshot_repo = SnapshotRepository(db)
    benchmark_repo = BenchmarkRepository(db)
    watch_stock_repo = WatchStockRepository(db)
    watch_index_repo = WatchIndexRepository(db)
    ticker_index_repo = TickerIndexRepository(db)

    redis_cache = RedisCache(settings.redis_url)
    rate_limiter = RateLimiter(
        max_per_sec=settings.rate_limit_per_sec,
        max_per_min=settings.rate_limit_per_min,
    )
    retry_policy = RetryPolicy(max_attempts=4, base_delay=0.5, max_delay=6.0)

    groww_client = GrowwClientFactory(settings).create()
    broadcaster = Broadcaster()

    ingestion_service = IngestionService(
        settings=settings,
        groww_client=groww_client,
        candle_repo=candle_repo,
        cache=redis_cache,
        rate_limiter=rate_limiter,
        retry_policy=retry_policy,
        watch_stock_repo=watch_stock_repo,
        watch_index_repo=watch_index_repo,
        ticker_index_repo=ticker_index_repo,
    )

    compute_service = ComputeService(
        settings=settings,
        candle_repo=candle_repo,
        snapshot_repo=snapshot_repo,
        benchmark_repo=benchmark_repo,
        cache=redis_cache,
        broadcaster=broadcaster,
        watch_stock_repo=watch_stock_repo,
        watch_index_repo=watch_index_repo,
        ticker_index_repo=ticker_index_repo,
    )

    scheduler = Scheduler(
        settings=settings,
        ingestion=ingestion_service,
        compute=compute_service,
    )

    return Container(
        settings=settings,
        db=db,
        candle_repo=candle_repo,
        snapshot_repo=snapshot_repo,
        benchmark_repo=benchmark_repo,
        watch_stock_repo=watch_stock_repo,
        watch_index_repo=watch_index_repo,
        ticker_index_repo=ticker_index_repo,
        redis_cache=redis_cache,
        rate_limiter=rate_limiter,
        retry_policy=retry_policy,
        groww_client=groww_client,
        broadcaster=broadcaster,
        ingestion_service=ingestion_service,
        compute_service=compute_service,
        scheduler=scheduler,
    )


def get_container() -> Container:
    global _container
    if _container is None:
        _container = build_container()
    return _container
