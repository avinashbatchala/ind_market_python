from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, Tuple, Optional

import numpy as np


class IvTracker:
    def __init__(self, window_minutes: int = 60) -> None:
        self.window = timedelta(minutes=window_minutes)
        self.data: Dict[str, Deque[Tuple[datetime, float]]] = {}

    def update(self, symbol: str, ts: datetime, iv: float) -> None:
        key = symbol.upper()
        dq = self.data.setdefault(key, deque())
        dq.append((ts, iv))
        self._prune(dq, ts)

    def get_ref(self, symbol: str, ts: datetime) -> Optional[float]:
        dq = self.data.get(symbol.upper())
        if not dq:
            return None
        self._prune(dq, ts)
        if not dq:
            return None
        values = np.array([v for _, v in dq], dtype=float)
        if values.size == 0:
            return None
        return float(np.median(values))

    def _prune(self, dq: Deque[Tuple[datetime, float]], ts: datetime) -> None:
        cutoff = ts - self.window
        while dq and dq[0][0] < cutoff:
            dq.popleft()
