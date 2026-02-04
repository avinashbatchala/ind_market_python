import datetime as dt

import numpy as np

from app.config.strategy import IntradayStrategyConfig
from app.domain.options.iv_tracker import IvTracker
from app.domain.strategy.contract_selector import select_long_call, select_credit_spread
from app.domain.strategy.models import OptionContract, OptionType
from app.domain.strategy.intraday_options_decision_tree import IntradayOptionsEngine, IndicatorSet


class DummyLiveData:
    def __init__(self, chain):
        self.chain = chain

    def fetch_expiries(self, **kwargs):
        return {"expiries": ["2026-02-10"]}

    def fetch_live(self, **kwargs):
        return {"options_chain": self.chain}


class DummyRepo:
    def __init__(self, data):
        self.data = data

    def get_latest_candles_batch(self, symbols, timeframe, limit):
        return {}


class DummyCache:
    def get_json(self, key):
        return None

    def set_json(self, key, value, ttl=None):
        pass


class DummyIndexRepo:
    def get_indices_for_stock(self, symbol):
        return []


class DummyWatchIndexRepo:
    def get_active_mappings(self):
        return {}


class DummyCandleRepo:
    def __init__(self, payload):
        self.payload = payload

    def get_latest_candles_batch(self, symbols, timeframe, limit):
        return {}

    def get_latest_candles(self, symbol, timeframe, limit):
        return self.payload



def build_contracts():
    contracts = []
    for strike, delta in [(25500, 0.52), (25600, 0.2), (25700, 0.1)]:
        contracts.append(
            OptionContract(
                symbol=f"NIFTY{strike}CE",
                underlying="NIFTY",
                expiry="2026-02-10",
                strike=strike,
                option_type=OptionType.CALL,
                ltp=100.0,
                bid=99.0,
                ask=101.0,
                iv=12.0,
                delta=delta,
                theta=-3.0,
                open_interest=5000,
                volume=2000,
            )
        )
    return contracts


def test_contract_selector_long_call():
    cfg = IntradayStrategyConfig()
    contracts = build_contracts()
    leg = select_long_call(contracts, cfg, iv_ref=12.0)
    assert leg is not None
    assert leg.contract.delta is not None
    assert 0.45 <= leg.contract.delta <= 0.60


def test_contract_selector_credit_spread():
    cfg = IntradayStrategyConfig()
    contracts = build_contracts()
    legs = select_credit_spread(contracts, cfg, OptionType.CALL)
    assert legs is not None
    assert len(legs) == 2
    assert legs[0].contract.delta is not None
    # hedge leg should be further OTM for calls (higher strike)
    assert legs[1].contract.strike > legs[0].contract.strike


def test_iv_tracker_reference():
    tracker = IvTracker(window_minutes=60)
    now = dt.datetime(2026, 2, 4, 10, 0, tzinfo=dt.timezone.utc)
    tracker.update("NIFTY", now, 10.0)
    tracker.update("NIFTY", now + dt.timedelta(minutes=10), 12.0)
    ref = tracker.get_ref("NIFTY", now + dt.timedelta(minutes=10))
    assert ref == 11.0
