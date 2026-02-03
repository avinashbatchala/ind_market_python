from __future__ import annotations

from typing import Dict
import numpy as np

from app.domain.indicators.rrs_rrv_rve import rolling_move, true_range, wilders_rma


def compute_benchmark_state(benchmark: str, data: Dict[str, np.ndarray]) -> dict:
    close = data["close"]
    high = data["high"]
    low = data["low"]
    volume = data["volume"]

    length = 12
    trend_series = rolling_move(close, length)
    atr_series = wilders_rma(true_range(high, low, close), length)
    vol_expansion_series = rolling_move(atr_series, length)
    participation_series = rolling_move(volume, length)

    trend = float(trend_series[-1]) if len(trend_series) else 0.0
    vol_expansion = float(vol_expansion_series[-1]) if len(vol_expansion_series) else 0.0
    participation = float(participation_series[-1]) if len(participation_series) else 0.0

    if trend > 0 and vol_expansion > 0:
        regime = "BULLISH"
    elif trend < 0 and vol_expansion > 0:
        regime = "BEARISH"
    else:
        regime = "NEUTRAL"

    return {
        "benchmark": benchmark,
        "regime": regime,
        "trend": trend,
        "vol_expansion": vol_expansion,
        "participation": participation,
    }
