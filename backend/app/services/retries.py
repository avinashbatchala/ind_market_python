from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")


class RetryPolicy:
    def __init__(self, max_attempts: int, base_delay: float, max_delay: float) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    def run(self, func: Callable[..., T], *args, **kwargs) -> T:
        attempt = 0
        while True:
            try:
                return func(*args, **kwargs)
            except Exception:
                attempt += 1
                if attempt >= self.max_attempts:
                    raise
                delay = min(self.max_delay, self.base_delay * (2 ** (attempt - 1)))
                time.sleep(delay)
