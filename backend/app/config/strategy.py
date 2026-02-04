from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IntradayStrategyConfig:
    timeframe: str = "5m"
    lookback: int = 200

    gate_start: str = "09:25"
    gate_end: str = "14:45"

    min_dte_days: int = 2

    rrs_market_threshold: float = 0.5
    rrs_sector_threshold: float = 0.0
    rve_buy_threshold: float = 0.3
    rve_sell_threshold: float = -0.3

    oi_min: float = 1000
    vol_min: float = 100
    ltp_min: float = 5.0
    spread_max: float = 0.05
    theta_ratio_max: float = 0.06

    allow_illiquid_fallback: bool = True

    delta_long_call: tuple[float, float] = (0.45, 0.60)
    delta_long_put: tuple[float, float] = (-0.60, -0.45)
    delta_short_abs: tuple[float, float] = (0.15, 0.30)

    delta_target_long_call: float = 0.52
    delta_target_long_put: float = -0.52
    delta_target_short: float = 0.20

    max_risk_pct: float = 0.003
    time_stop_min: int = 75
    profit_target_long: float = 0.3
    stop_loss_long: float = 0.25
    profit_target_spread: float = 0.5
    stop_loss_spread: float = 1.7

    iv_ref_window_min: int = 60
