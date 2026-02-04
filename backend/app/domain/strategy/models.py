from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Direction(str, Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    NONE = "NONE"


class Regime(str, Enum):
    BUY_PREMIUM = "BUY_PREMIUM"
    SELL_PREMIUM = "SELL_PREMIUM"
    NONE = "NONE"


class StrategyType(str, Enum):
    BUY_CALL = "BUY_CALL"
    BUY_PUT = "BUY_PUT"
    BULL_PUT_SPREAD = "BULL_PUT_SPREAD"
    BEAR_CALL_SPREAD = "BEAR_CALL_SPREAD"
    BULL_CALL_SPREAD = "BULL_CALL_SPREAD"
    BEAR_PUT_SPREAD = "BEAR_PUT_SPREAD"
    NONE = "NONE"


class OptionType(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class EntryType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


@dataclass
class OptionContract:
    symbol: str
    underlying: str
    expiry: str
    strike: float
    option_type: OptionType
    ltp: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    iv: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    open_interest: Optional[float] = None
    volume: Optional[float] = None

    @property
    def spread_pct(self) -> Optional[float]:
        if self.bid is None or self.ask is None or self.ltp in (None, 0):
            return None
        return max(self.ask - self.bid, 0) / self.ltp

    @property
    def theta_ratio(self) -> Optional[float]:
        if self.theta is None or self.ltp in (None, 0):
            return None
        return abs(self.theta) / self.ltp


@dataclass
class OptionLeg:
    contract: OptionContract
    side: Side
    quantity: int = 1


@dataclass
class TradePlan:
    symbol: str
    direction: Direction
    regime: Regime
    strategy: StrategyType
    legs: List[OptionLeg]
    dte: int
    max_risk_pct: float
    entry_type: EntryType
    exits: dict
    timestamp: str
    notes: List[str] = field(default_factory=list)
