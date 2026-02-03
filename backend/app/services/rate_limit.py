from __future__ import annotations

import time
from collections import deque
from threading import Lock


class RateLimiter:
    def __init__(self, max_per_sec: int, max_per_min: int) -> None:
        self.max_per_sec = max_per_sec
        self.max_per_min = max_per_min
        self._lock = Lock()
        self._calls_sec = deque()
        self._calls_min = deque()

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            self._cleanup(now)

            if len(self._calls_sec) >= self.max_per_sec:
                sleep_for = 1.0 - (now - self._calls_sec[0])
                if sleep_for > 0:
                    time.sleep(sleep_for)
                now = time.monotonic()
                self._cleanup(now)

            if len(self._calls_min) >= self.max_per_min:
                sleep_for = 60.0 - (now - self._calls_min[0])
                if sleep_for > 0:
                    time.sleep(sleep_for)
                now = time.monotonic()
                self._cleanup(now)

            self._calls_sec.append(now)
            self._calls_min.append(now)

    def _cleanup(self, now: float) -> None:
        while self._calls_sec and (now - self._calls_sec[0]) > 1.0:
            self._calls_sec.popleft()
        while self._calls_min and (now - self._calls_min[0]) > 60.0:
            self._calls_min.popleft()
