from __future__ import annotations

from typing import List, Optional, Tuple

import math

from app.config.strategy import IntradayStrategyConfig
from app.domain.strategy.models import OptionContract, OptionLeg, OptionType, Side


def _passes_liquidity(contract: OptionContract, cfg: IntradayStrategyConfig) -> bool:
    if contract.ltp is None or contract.ltp < cfg.ltp_min:
        return False
    if contract.open_interest is not None and contract.open_interest < cfg.oi_min:
        return False
    if contract.volume is not None and contract.volume < cfg.vol_min:
        return False
    spread = contract.spread_pct
    if spread is not None and spread > cfg.spread_max:
        return False
    theta_ratio = contract.theta_ratio
    if theta_ratio is not None and theta_ratio > cfg.theta_ratio_max:
        return False
    return True


def _score_contract(
    contract: OptionContract,
    target_delta: float,
    delta_band: Tuple[float, float],
    iv_ref: Optional[float],
    is_buy: bool,
) -> float:
    delta = contract.delta or 0.0
    delta_span = delta_band[1] - delta_band[0]
    if delta_span <= 0:
        delta_span = 0.1
    delta_score = -abs(delta - target_delta) / delta_span

    oi_score = math.log1p(contract.open_interest or 0.0)
    vol_score = math.log1p(contract.volume or 0.0)
    theta_penalty = contract.theta_ratio or 0.0
    spread_penalty = contract.spread_pct or 0.0

    iv_penalty = 0.0
    if is_buy and iv_ref and contract.iv:
        iv_penalty = max(0.0, (contract.iv - iv_ref) / iv_ref)

    return delta_score + 0.2 * oi_score + 0.1 * vol_score - 1.5 * theta_penalty - 0.5 * spread_penalty - iv_penalty


def _filter_by_delta(contracts: List[OptionContract], delta_min: float, delta_max: float) -> List[OptionContract]:
    out = []
    for c in contracts:
        if c.delta is None:
            continue
        if delta_min <= c.delta <= delta_max:
            out.append(c)
    return out


def select_long_call(contracts: List[OptionContract], cfg: IntradayStrategyConfig, iv_ref: Optional[float]) -> Optional[OptionLeg]:
    calls = [c for c in contracts if c.option_type == OptionType.CALL and _passes_liquidity(c, cfg)]
    calls = _filter_by_delta(calls, *cfg.delta_long_call)
    if not calls:
        return None
    best = max(calls, key=lambda c: _score_contract(c, cfg.delta_target_long_call, cfg.delta_long_call, iv_ref, True))
    return OptionLeg(contract=best, side=Side.BUY)


def select_long_put(contracts: List[OptionContract], cfg: IntradayStrategyConfig, iv_ref: Optional[float]) -> Optional[OptionLeg]:
    puts = [c for c in contracts if c.option_type == OptionType.PUT and _passes_liquidity(c, cfg)]
    puts = _filter_by_delta(puts, *cfg.delta_long_put)
    if not puts:
        return None
    best = max(puts, key=lambda c: _score_contract(c, cfg.delta_target_long_put, cfg.delta_long_put, iv_ref, True))
    return OptionLeg(contract=best, side=Side.BUY)


def select_credit_spread(
    contracts: List[OptionContract],
    cfg: IntradayStrategyConfig,
    option_type: OptionType,
) -> Optional[List[OptionLeg]]:
    pool = [c for c in contracts if c.option_type == option_type and _passes_liquidity(c, cfg)]
    if not pool:
        return None
    deltas = [c for c in pool if c.delta is not None and cfg.delta_short_abs[0] <= abs(c.delta) <= cfg.delta_short_abs[1]]
    if not deltas:
        return None

    short_leg = max(deltas, key=lambda c: _score_contract(c, cfg.delta_target_short * (1 if option_type == OptionType.CALL else -1), cfg.delta_short_abs, None, False))

    # Hedge leg: further OTM
    if option_type == OptionType.CALL:
        candidates = [c for c in pool if c.strike > short_leg.strike]
        candidates.sort(key=lambda c: c.strike)
    else:
        candidates = [c for c in pool if c.strike < short_leg.strike]
        candidates.sort(key=lambda c: -c.strike)

    if not candidates:
        return None

    hedge_leg = candidates[0]
    return [
        OptionLeg(contract=short_leg, side=Side.SELL),
        OptionLeg(contract=hedge_leg, side=Side.BUY),
    ]


def select_debit_spread(
    contracts: List[OptionContract],
    cfg: IntradayStrategyConfig,
    option_type: OptionType,
    iv_ref: Optional[float],
) -> Optional[List[OptionLeg]]:
    # Long near ATM, sell further OTM
    if option_type == OptionType.CALL:
        long_leg = select_long_call(contracts, cfg, iv_ref)
        if long_leg is None:
            return None
        pool = [c for c in contracts if c.option_type == OptionType.CALL]
        candidates = [c for c in pool if c.strike > long_leg.contract.strike]
        candidates.sort(key=lambda c: c.strike)
    else:
        long_leg = select_long_put(contracts, cfg, iv_ref)
        if long_leg is None:
            return None
        pool = [c for c in contracts if c.option_type == OptionType.PUT]
        candidates = [c for c in pool if c.strike < long_leg.contract.strike]
        candidates.sort(key=lambda c: -c.strike)

    if not candidates:
        return None

    short_leg = candidates[0]
    return [
        long_leg,
        OptionLeg(contract=short_leg, side=Side.SELL),
    ]
