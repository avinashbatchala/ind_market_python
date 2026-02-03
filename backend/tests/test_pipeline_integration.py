from datetime import datetime, timedelta, timezone

from app.core.config import Settings
from app.services.ingestion import IngestionService
from app.services.compute import ComputeService
from app.services.rate_limit import RateLimiter
from app.services.retries import RetryPolicy


class FakeGrowwClient:
    def fetch_candles(self, trading_symbol, timeframe, start_time, end_time, exchange, segment):
        minutes = {"5m": 5, "15m": 15, "1h": 60, "1d": 1440}[timeframe]
        total = int((end_time - start_time).total_seconds() / (minutes * 60))
        candles = []
        for i in range(total):
            ts = start_time + timedelta(minutes=i * minutes)
            base = 100 + i
            candles.append(
                {
                    "ts": ts,
                    "open": base,
                    "high": base + 1,
                    "low": base - 1,
                    "close": base + 0.5,
                    "volume": 1000 + i,
                    "source": "fake",
                }
            )
        return candles


class MemoryCache:
    def __init__(self):
        self.store = {}

    def connect(self):
        pass

    def close(self):
        pass

    def get_json(self, key):
        return self.store.get(key)

    def set_json(self, key, value, ttl=None):
        self.store[key] = value


class MemoryCandleRepo:
    def __init__(self):
        self.store = {}

    def upsert_candles(self, symbol, timeframe, candles):
        self.store[(symbol, timeframe)] = candles

    def get_latest_candles(self, symbol, timeframe, limit):
        return []


class MemorySnapshotRepo:
    def __init__(self):
        self.last = None

    def save_snapshot(self, timeframe, ts, rows):
        self.last = {"timeframe": timeframe, "ts": ts, "rows": rows}

    def get_latest_snapshot(self, timeframe):
        return None


class MemoryBenchmarkRepo:
    def __init__(self):
        self.last = None

    def save_states(self, timeframe, ts, states):
        self.last = {"timeframe": timeframe, "ts": ts, "states": states}

    def get_latest_states(self, timeframe):
        return None


def test_pipeline_end_to_end():
    settings = Settings()
    settings.ingest_bars = 50
    settings.compute_bars = 40

    ingestion = IngestionService(
        settings=settings,
        groww_client=FakeGrowwClient(),
        candle_repo=MemoryCandleRepo(),
        cache=MemoryCache(),
        rate_limiter=RateLimiter(1000, 1000),
        retry_policy=RetryPolicy(1, 0.01, 0.01),
    )

    cache = ingestion.cache
    compute = ComputeService(
        settings=settings,
        candle_repo=ingestion.candle_repo,
        snapshot_repo=MemorySnapshotRepo(),
        benchmark_repo=MemoryBenchmarkRepo(),
        cache=cache,
        broadcaster=None,
    )

    ingestion.run_once("5m")
    compute.compute_timeframe("5m")

    payload = cache.get_json("scanner:5m")
    assert payload is not None
    assert payload["rows"]
