from __future__ import annotations

from typing import Any, Iterable, Optional, Tuple

import numpy as np

from app.domain.strategy.models import OptionContract, OptionType


def _get_first(data: dict, keys: Iterable[str]) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_option_type(value: Any) -> OptionType | None:
    if value is None:
        return None
    val = str(value).upper()
    if val in ("CALL", "CE", "C"):
        return OptionType.CALL
    if val in ("PUT", "PE", "P"):
        return OptionType.PUT
    return None


def extract_underlying_price(raw: dict) -> Optional[float]:
    if not isinstance(raw, dict):
        return None
    candidates = [
        raw.get("underlyingValue"),
        raw.get("underlying_price"),
        raw.get("spotPrice"),
        raw.get("spot"),
    ]
    for item in candidates:
        val = _to_float(item)
        if val is not None:
            return val
    data = raw.get("data") if isinstance(raw.get("data"), dict) else None
    if data:
        return extract_underlying_price(data)
    return None


def iter_chain_rows(raw: dict) -> Iterable[dict]:
    if not isinstance(raw, dict):
        return []
    candidates = [
        raw.get("options"),
        raw.get("optionChain"),
        raw.get("option_chain"),
    ]
    data = raw.get("data") if isinstance(raw.get("data"), dict) else None
    if data:
        candidates.extend([
            data.get("options"),
            data.get("optionChain"),
            data.get("option_chain"),
        ])
    for cand in candidates:
        if isinstance(cand, list):
            return cand
    return []


def normalize_chain(raw: dict, underlying_symbol: str) -> Tuple[list[OptionContract], Optional[float]]:
    rows = iter_chain_rows(raw)
    underlying_price = extract_underlying_price(raw)
    contracts: list[OptionContract] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        greeks = row.get("greeks") if isinstance(row.get("greeks"), dict) else {}
        option_type = _normalize_option_type(_get_first(row, ["optionType", "type", "right", "option_type"]))
        if option_type is None:
            continue

        contract = OptionContract(
            symbol=str(_get_first(row, ["tradingSymbol", "symbol"]) or ""),
            underlying=underlying_symbol,
            expiry=str(_get_first(row, ["expiryDate", "expiry", "expiry_date"]) or ""),
            strike=_to_float(_get_first(row, ["strikePrice", "strike", "strike_price"])) or 0.0,
            option_type=option_type,
            ltp=_to_float(_get_first(row, ["ltp", "lastTradedPrice", "last_price"])) or 0.0,
            bid=_to_float(_get_first(row, ["bid", "bidPrice", "bid_price"])),
            ask=_to_float(_get_first(row, ["ask", "askPrice", "ask_price"])),
            iv=_to_float(_get_first(row, ["iv", "impliedVolatility", "implied_volatility"]) or greeks.get("iv")),
            delta=_to_float(_get_first(row, ["delta"]) or greeks.get("delta")),
            gamma=_to_float(_get_first(row, ["gamma"]) or greeks.get("gamma")),
            theta=_to_float(_get_first(row, ["theta"]) or greeks.get("theta")),
            vega=_to_float(_get_first(row, ["vega"]) or greeks.get("vega")),
            rho=_to_float(_get_first(row, ["rho"]) or greeks.get("rho")),
            open_interest=_to_float(_get_first(row, ["openInterest", "open_interest", "oi"])),
            volume=_to_float(_get_first(row, ["volume", "vol"])),
        )
        contracts.append(contract)

    return contracts, underlying_price


def compute_atm_iv(contracts: list[OptionContract], underlying_price: Optional[float]) -> Optional[float]:
    if not contracts:
        return None
    if underlying_price is None:
        ivs = [c.iv for c in contracts if c.iv is not None]
        return float(np.median(ivs)) if ivs else None
    strikes = sorted({c.strike for c in contracts if c.strike})
    if not strikes:
        return None
    atm_strike = min(strikes, key=lambda s: abs(s - underlying_price))
    ivs = [c.iv for c in contracts if c.strike == atm_strike and c.iv is not None]
    if not ivs:
        return None
    return float(np.mean(ivs))
