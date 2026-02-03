from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import List

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.market_hours import is_market_open


class Scheduler:
    def __init__(self, settings: Settings, ingestion, compute) -> None:
        self.settings = settings
        self.ingestion = ingestion
        self.compute = compute
        self._tasks: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        self._ingest_lock = asyncio.Lock()
        self._compute_lock = asyncio.Lock()
        self.logger = get_logger(self.__class__.__name__)

    def start(self) -> None:
        if self._tasks:
            return
        self._stop_event.clear()

        for timeframe in self.settings.timeframes():
            self.logger.info("Scheduler loop start", extra={"timeframe": timeframe})
            self._tasks.append(asyncio.create_task(self._ingest_loop(timeframe)))
            self._tasks.append(asyncio.create_task(self._compute_loop(timeframe)))

    async def stop(self) -> None:
        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []

    async def _ingest_loop(self, timeframe: str) -> None:
        interval = self.settings.scheduler_ingest_interval_sec
        while not self._stop_event.is_set():
            now = datetime.now(timezone.utc)
            if is_market_open(now, self.settings):
                async with self._ingest_lock:
                    await asyncio.to_thread(self.ingestion.run_once, timeframe)
            else:
                self.logger.info("Market closed, skipping ingestion", extra={"timeframe": timeframe})
            await asyncio.sleep(interval)

    async def _compute_loop(self, timeframe: str) -> None:
        interval = self.settings.scheduler_compute_interval_sec
        while not self._stop_event.is_set():
            now = datetime.now(timezone.utc)
            if is_market_open(now, self.settings):
                async with self._compute_lock:
                    await asyncio.to_thread(self.compute.compute_timeframe, timeframe)
            else:
                self.logger.info("Market closed, skipping compute", extra={"timeframe": timeframe})
            await asyncio.sleep(interval)
