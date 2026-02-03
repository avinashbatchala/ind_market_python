from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Dict, Optional, Set

from fastapi import WebSocket


class Broadcaster:
    def __init__(self) -> None:
        self._connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def register(self, timeframe: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections[timeframe].add(websocket)

    async def unregister(self, timeframe: str, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._connections.get(timeframe, set()):
                self._connections[timeframe].remove(websocket)

    async def publish(self, timeframe: str, payload: dict) -> None:
        async with self._lock:
            connections = list(self._connections.get(timeframe, set()))

        if not connections:
            return

        for ws in connections:
            try:
                await ws.send_json(payload)
            except Exception:
                await self.unregister(timeframe, ws)

    def publish_threadsafe(self, timeframe: str, payload: dict) -> None:
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self.publish(timeframe, payload), self._loop)
