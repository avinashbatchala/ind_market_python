from __future__ import annotations

TIMEFRAME_MINUTES = {
    "5m": 5,
    "15m": 15,
    "1h": 60,
    "1d": 1440,
}


def timeframe_to_minutes(timeframe: str) -> int:
    if timeframe not in TIMEFRAME_MINUTES:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return TIMEFRAME_MINUTES[timeframe]
