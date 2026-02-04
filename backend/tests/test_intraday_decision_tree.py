import datetime as dt

from app.config.strategy import IntradayStrategyConfig
from app.domain.strategy.intraday_options_decision_tree import IntradayOptionsEngine, IndicatorSet
from app.domain.strategy.models import Direction, Regime
from app.domain.options.iv_tracker import IvTracker


class DummySettings:
    market_tz = "Asia/Kolkata"
    nifty_symbol = "NIFTY"
    groww_exchange = "NSE"
    groww_segment = "CASH"


class DummyRepo:
    pass


class DummyCache:
    pass


class DummyLive:
    pass


def build_engine():
    return IntradayOptionsEngine(
        settings=DummySettings(),
        candle_repo=DummyRepo(),
        ticker_index_repo=DummyRepo(),
        watch_index_repo=DummyRepo(),
        cache=DummyCache(),
        live_data=DummyLive(),
        iv_tracker=IvTracker(),
        config=IntradayStrategyConfig(),
    )


def test_direction_gate_bull_bear_no_trade():
    engine = build_engine()

    ind = IndicatorSet(rrs_mkt=0.6, rrs_sec=0.1, rrs_sector_vs_mkt=0.1, rrv=0.2, rve=0.2)
    assert engine._direction_gate(ind) == Direction.BULL

    ind = IndicatorSet(rrs_mkt=-0.6, rrs_sec=-0.2, rrs_sector_vs_mkt=-0.1, rrv=-0.2, rve=-0.2)
    assert engine._direction_gate(ind) == Direction.BEAR

    ind = IndicatorSet(rrs_mkt=0.1, rrs_sec=0.1, rrs_sector_vs_mkt=0.1, rrv=0.2, rve=0.2)
    assert engine._direction_gate(ind) == Direction.NONE


def test_vol_regime_gate():
    engine = build_engine()
    assert engine._vol_regime(0.4, iv_atm=10.0, iv_ref=12.0) == Regime.BUY_PREMIUM
    assert engine._vol_regime(-0.4, iv_atm=12.0, iv_ref=10.0) == Regime.SELL_PREMIUM
    assert engine._vol_regime(0.1, iv_atm=10.0, iv_ref=12.0) == Regime.NONE


def test_time_gate():
    engine = build_engine()
    # 10:00 IST should pass
    now = dt.datetime(2026, 2, 4, 4, 30, tzinfo=dt.timezone.utc)
    assert engine._within_gate(now) is True
    # 08:00 IST should fail
    early = dt.datetime(2026, 2, 4, 2, 30, tzinfo=dt.timezone.utc)
    assert engine._within_gate(early) is False
