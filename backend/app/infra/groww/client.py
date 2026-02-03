from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, List, Optional, Protocol

import pyotp

from app.core.config import Settings
from app.core.logging import get_logger


class GrowwClient(Protocol):
    def fetch_candles(
        self,
        trading_symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        exchange: str,
        segment: str,
    ) -> List[dict]:
        ...


@dataclass
class CandleInterval:
    name: str
    minutes: int
    max_days: int


TIMEFRAME_INTERVALS = {
    "5m": CandleInterval("CANDLE_INTERVAL_MIN_5", 5, 30),
    "15m": CandleInterval("CANDLE_INTERVAL_MIN_15", 15, 90),
    "1h": CandleInterval("CANDLE_INTERVAL_HOUR_1", 60, 180),
    "1d": CandleInterval("CANDLE_INTERVAL_DAY_1", 1440, 180),
}


class GrowwClientFactory:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create(self) -> GrowwClient:
        return RealGrowwClient(self.settings)


class RealGrowwClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(self.__class__.__name__)

        try:
            from growwapi import GrowwAPI  # type: ignore
        except ImportError as exc:  # pragma: no cover - dependency missing at runtime
            raise RuntimeError("growwapi SDK not installed") from exc

        access_token = settings.groww_access_token
        if not access_token:
            access_token = self._generate_access_token(GrowwAPI)

        self.client = GrowwAPI(access_token)
        self.groww_module = __import__("growwapi")

    def _generate_access_token(self, GrowwAPI) -> str:
        if self.settings.groww_api_key and self.settings.groww_api_secret:
            try:
                return GrowwAPI.get_access_token(
                    api_key=self.settings.groww_api_key,
                    secret=self.settings.groww_api_secret,
                )
            except Exception as exc:
                self.logger.warning(
                    "API secret auth failed; trying TOTP",
                    extra={"error": str(exc)},
                )

        if self.settings.groww_api_key and self.settings.groww_totp_secret:
            totp = pyotp.TOTP(self.settings.groww_totp_secret).now()
            return GrowwAPI.get_access_token(
                api_key=self.settings.groww_api_key,
                totp=totp,
            )

        if self.settings.groww_api_key and self.settings.groww_api_secret:
            totp = pyotp.TOTP(self.settings.groww_api_secret).now()
            return GrowwAPI.get_access_token(
                api_key=self.settings.groww_api_key,
                totp=totp,
            )

        if self.settings.groww_totp_token and self.settings.groww_totp_secret:
            totp = pyotp.TOTP(self.settings.groww_totp_secret).now()
            return GrowwAPI.get_access_token(
                api_key=self.settings.groww_totp_token,
                totp=totp,
            )

        raise RuntimeError("Missing Groww credentials. Provide GROWW_ACCESS_TOKEN or TOTP/API key flow.")

    def fetch_candles(
        self,
        trading_symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        exchange: str,
        segment: str,
    ) -> List[dict]:
        interval = TIMEFRAME_INTERVALS.get(timeframe)
        if interval is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        self.logger.info(
            "Fetch candles",
            extra={
                "symbol": trading_symbol,
                "timeframe": timeframe,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )

        chunk_delta = timedelta(days=interval.max_days)

        candles: List[dict] = []
        cursor = start_time
        while cursor < end_time:
            chunk_end = min(cursor + chunk_delta, end_time)
            response = self._fetch_chunk(
                trading_symbol=trading_symbol,
                exchange=exchange,
                segment=segment,
                interval=interval,
                start_time=cursor,
                end_time=chunk_end,
            )
            candles.extend(response)
            cursor = chunk_end

        self.logger.info(
            "Fetch complete",
            extra={"symbol": trading_symbol, "timeframe": timeframe, "candles": len(candles)},
        )
        return candles

    def fetch_candles_raw(
        self,
        trading_symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        exchange: str,
        segment: str,
    ) -> dict:
        interval = TIMEFRAME_INTERVALS.get(timeframe)
        if interval is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)
        return self.client.get_historical_candle_data(
            trading_symbol=trading_symbol,
            exchange=getattr(self.groww_module, f"EXCHANGE_{exchange}", exchange),
            segment=getattr(self.groww_module, f"SEGMENT_{segment}", segment),
            start_time=start_time_ms,
            end_time=end_time_ms,
            interval_in_minutes=interval.minutes,
        )

    def _fetch_chunk(
        self,
        trading_symbol: str,
        exchange: str,
        segment: str,
        interval: CandleInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> List[dict]:
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)
        response = self.client.get_historical_candle_data(
            trading_symbol=trading_symbol,
            exchange=getattr(self.groww_module, f"EXCHANGE_{exchange}", exchange),
            segment=getattr(self.groww_module, f"SEGMENT_{segment}", segment),
            start_time=start_time_ms,
            end_time=end_time_ms,
            interval_in_minutes=interval.minutes,
        )

        return self._normalize_candles(response)

    @staticmethod
    def _normalize_candles(response: dict) -> List[dict]:
        payload = response.get("payload", response)
        raw_candles = payload.get("candles", []) if payload else []

        candles: List[dict] = []
        for row in raw_candles:
            if len(row) < 6:
                continue
            if row[0] is None:
                continue
            try:
                ts_epoch = int(row[0])
            except (TypeError, ValueError):
                continue
            open_v = RealGrowwClient._safe_float(row[1])
            high_v = RealGrowwClient._safe_float(row[2])
            low_v = RealGrowwClient._safe_float(row[3])
            close_v = RealGrowwClient._safe_float(row[4])
            if None in (open_v, high_v, low_v, close_v):
                continue
            candles.append(
                {
                    "ts": datetime.fromtimestamp(ts_epoch, tz=timezone.utc),
                    "open": open_v,
                    "high": high_v,
                    "low": low_v,
                    "close": close_v,
                    "volume": RealGrowwClient._safe_float(row[5], default=0.0),
                    "source": "groww",
                }
            )
        return candles

    @staticmethod
    def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
