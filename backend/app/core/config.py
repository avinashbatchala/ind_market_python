from __future__ import annotations

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = Field("dev", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    database_url: str = Field("postgresql+psycopg2://postgres:postgres@db:5432/groww_scanner", alias="DATABASE_URL")
    redis_url: str = Field("redis://redis:6379/0", alias="REDIS_URL")

    groww_api_key: str | None = Field(default=None, alias="GROWW_API_KEY")
    groww_api_secret: str | None = Field(default=None, alias="GROWW_API_SECRET")
    groww_access_token: str | None = Field(default=None, alias="GROWW_ACCESS_TOKEN")
    groww_totp_secret: str | None = Field(default=None, alias="GROWW_TOTP_SECRET")
    groww_totp_token: str | None = Field(default=None, alias="GROWW_TOTP_TOKEN")

    groww_exchange: str = Field("NSE", alias="GROWW_EXCHANGE")
    groww_segment: str = Field("CASH", alias="GROWW_SEGMENT")

    ingest_bars: int = Field(220, alias="INGEST_BARS")
    compute_bars: int = Field(200, alias="COMPUTE_BARS")

    scheduler_ingest_interval_sec: int = Field(45, alias="SCHEDULER_INGEST_INTERVAL_SEC")
    scheduler_compute_interval_sec: int = Field(60, alias="SCHEDULER_COMPUTE_INTERVAL_SEC")
    scheduler_timeframes: str = Field("5m,15m,1h,1d", alias="SCHEDULER_TIMEFRAMES")

    market_tz: str = Field("Asia/Kolkata", alias="MARKET_TZ")
    market_open_time: str = Field("09:15", alias="MARKET_OPEN_TIME")
    market_close_time: str = Field("15:30", alias="MARKET_CLOSE_TIME")
    market_days: str = Field("MON,TUE,WED,THU,FRI", alias="MARKET_DAYS")
    market_allow_after_hours: bool = Field(False, alias="MARKET_ALLOW_AFTER_HOURS")

    nifty_symbol: str = Field("NIFTY", alias="NIFTY_SYMBOL")
    banknifty_symbol: str = Field("BANKNIFTY", alias="BANKNIFTY_SYMBOL")

    rate_limit_per_sec: int = Field(10, alias="RATE_LIMIT_PER_SEC")
    rate_limit_per_min: int = Field(300, alias="RATE_LIMIT_PER_MIN")

    def timeframes(self) -> List[str]:
        return [t.strip() for t in self.scheduler_timeframes.split(",") if t.strip()]

    def market_days_list(self) -> List[str]:
        return [d.strip().upper() for d in self.market_days.split(",") if d.strip()]
