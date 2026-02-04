from __future__ import annotations

from typing import Any, Optional, Iterable
import inspect
from datetime import datetime, timezone, timedelta

from app.core.config import Settings
from app.infra.groww.client import GrowwClient, RealGrowwClient
from app.domain.options.groww_chain_adapter import normalize_chain


class GrowwLiveDataService:
    def __init__(self, settings: Settings, groww_client: GrowwClient) -> None:
        self.settings = settings
        self.groww_client = groww_client

    def fetch_live(
        self,
        symbol: str,
        exchange: str,
        segment: str,
        expiry: Optional[str] = None,
        option_type: Optional[str] = None,
        underlying: Optional[str] = None,
        trading_symbol: Optional[str] = None,
        expiry_date: Optional[str] = None,
    ) -> dict:
        if not isinstance(self.groww_client, RealGrowwClient):
            return {
                "symbol": symbol,
                "exchange": exchange,
                "segment": segment,
                "quote": None,
                "ltp": None,
                "options_chain": None,
                "greeks": None,
                "errors": {"client": "Live data not supported for this client"},
            }

        client = self.groww_client.client
        module = self.groww_client.groww_module
        exchange_const = getattr(module, f"EXCHANGE_{exchange}", exchange)
        segment_const = getattr(module, f"SEGMENT_{segment}", segment)

        errors: dict[str, str] = {}
        quote = _safe_call(
            lambda: client.get_quote(
                exchange=exchange_const,
                segment=segment_const,
                trading_symbol=symbol,
            ),
            errors,
            "quote",
        )

        options_chain = None
        chain_expiry = expiry_date or expiry
        if not chain_expiry:
            chain_expiry = _resolve_default_expiry(
                client=client,
                exchange_const=exchange_const,
                underlying_symbol=underlying or symbol,
            )
        if hasattr(client, "get_option_chain"):
            if not chain_expiry:
                errors["options_chain"] = "Missing expiry_date for option chain"
            else:
                options_chain = _safe_call(
                    lambda: _call_supported(
                        client.get_option_chain,
                        exchange=exchange_const,
                        underlying=underlying or symbol,
                        expiry_date=chain_expiry,
                    ),
                    errors,
                    "options_chain",
                )
        else:
            errors["options_chain"] = "SDK missing get_option_chain"

        greeks = None
        if hasattr(client, "get_greeks"):
            greeks_expiry = expiry or expiry_date or chain_expiry
            selected_symbol = trading_symbol
            if not selected_symbol and options_chain:
                contracts, underlying_price = normalize_chain(options_chain, underlying or symbol)
                selected_symbol = _pick_greeks_symbol(contracts, underlying_price)
                if not greeks_expiry and contracts:
                    greeks_expiry = contracts[0].expiry or greeks_expiry
            if not selected_symbol or not greeks_expiry:
                errors["greeks"] = "Missing trading_symbol or expiry for greeks"
            else:
                greeks = _safe_call(
                    lambda: _call_supported(
                        client.get_greeks,
                        exchange=exchange_const,
                        underlying=underlying or symbol,
                        trading_symbol=selected_symbol,
                        expiry=greeks_expiry,
                    ),
                    errors,
                    "greeks",
                )
        else:
            errors["greeks"] = "SDK missing get_greeks"

        ltp = _extract_ltp(quote)
        change = _extract_change(quote)
        ts = _extract_timestamp(quote)

        return {
            "symbol": symbol,
            "exchange": exchange,
            "segment": segment,
            "quote": quote,
            "ltp": ltp,
            "change": change,
            "timestamp": ts,
            "options_chain": options_chain,
            "greeks": greeks,
            "errors": errors or None,
        }

    def fetch_expiries(
        self,
        exchange: str,
        underlying_symbol: str,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> dict:
        if not isinstance(self.groww_client, RealGrowwClient):
            return {"expiries": [], "errors": {"client": "Live data not supported for this client"}}

        client = self.groww_client.client
        module = self.groww_client.groww_module
        exchange_const = getattr(module, f"EXCHANGE_{exchange}", exchange)

        errors: dict[str, str] = {}
        expiries: list[str] = []
        if hasattr(client, "get_expiries"):
            targets = _expiry_targets(year=year, month=month)
            for yr, mo in targets:
                response = _safe_call(
                    lambda: _call_supported(
                        client.get_expiries,
                        exchange=exchange_const,
                        underlying_symbol=underlying_symbol,
                        year=yr,
                        month=mo,
                    ),
                    errors,
                    "expiries",
                )
                expiries.extend(_extract_expiries(response))
        else:
            errors["expiries"] = "SDK missing get_expiries"

        expiries = _dedupe_expiries(expiries)
        return {"expiries": expiries, "errors": errors or None}


def _safe_call(fn, errors: dict[str, str], key: str) -> Any:
    try:
        return fn()
    except Exception as exc:  # pragma: no cover - SDK error
        errors[key] = str(exc)
        return None


def _call_supported(fn, **kwargs):
    sig = inspect.signature(fn)
    supported = {k: v for k, v in kwargs.items() if k in sig.parameters and v is not None}
    return fn(**supported)


def _expiry_targets(year: Optional[int], month: Optional[int]) -> list[tuple[int, int]]:
    if year and month:
        return [(year, month)]
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(timezone.utc).astimezone(ist)
    targets = [(now.year, now.month)]
    next_month = now.month + 1
    next_year = now.year
    if next_month == 13:
        next_month = 1
        next_year += 1
    targets.append((next_year, next_month))
    return targets


def _extract_expiries(response: Any) -> list[str]:
    if response is None:
        return []
    if isinstance(response, dict):
        for key in ("expiries", "expiryDates", "expiry_dates"):
            if key in response:
                return _extract_expiries(response[key])
        data = response.get("data")
        if data is not None:
            return _extract_expiries(data)
        return []
    if isinstance(response, list):
        expiries: list[str] = []
        for item in response:
            if isinstance(item, dict):
                val = item.get("expiry") or item.get("expiryDate") or item.get("date")
                if val:
                    expiries.append(str(val))
            else:
                expiries.append(str(item))
        return expiries
    return []


def _dedupe_expiries(expiries: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    seen = set()
    for item in expiries:
        if not item:
            continue
        value = str(item)
        if value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    cleaned.sort()
    return cleaned


def _resolve_default_expiry(client: Any, exchange_const: Any, underlying_symbol: str) -> Optional[str]:
    if not hasattr(client, "get_expiries"):
        return None
    targets = _expiry_targets(year=None, month=None)
    expiries: list[str] = []
    for yr, mo in targets:
        try:
            response = _call_supported(
                client.get_expiries,
                exchange=exchange_const,
                underlying_symbol=underlying_symbol,
                year=yr,
                month=mo,
            )
        except Exception:
            continue
        expiries.extend(_extract_expiries(response))
    expiries = _dedupe_expiries(expiries)
    return expiries[0] if expiries else None


def _pick_greeks_symbol(contracts: list[Any], underlying_price: Optional[float]) -> Optional[str]:
    if not contracts:
        return None
    if underlying_price is None:
        sorted_contracts = sorted(
            contracts,
            key=lambda c: (
                0 if getattr(c, "option_type", None) and c.option_type.value == "CALL" else 1,
                -(getattr(c, "open_interest", 0) or 0),
                -(getattr(c, "volume", 0) or 0),
            ),
        )
    else:
        sorted_contracts = sorted(
            contracts,
            key=lambda c: (
                abs((getattr(c, "strike", 0) or 0) - underlying_price),
                0 if getattr(c, "option_type", None) and c.option_type.value == "CALL" else 1,
            ),
        )
    for contract in sorted_contracts:
        symbol = getattr(contract, "symbol", None)
        if symbol:
            return symbol
    return None


def _extract_ltp(quote: Any) -> Optional[float]:
    if isinstance(quote, dict):
        for key in ("ltp", "lastTradedPrice", "last_price"):
            if key in quote:
                return _to_float(quote[key])
        if "data" in quote and isinstance(quote["data"], dict):
            return _extract_ltp(quote["data"])
    return None


def _extract_change(quote: Any) -> Optional[float]:
    if isinstance(quote, dict):
        for key in ("change", "netChange", "chg"):
            if key in quote:
                return _to_float(quote[key])
        if "data" in quote and isinstance(quote["data"], dict):
            return _extract_change(quote["data"])
    return None


def _extract_timestamp(quote: Any) -> Optional[str]:
    if isinstance(quote, dict):
        for key in ("timestamp", "ts", "lastTradedTime"):
            if key in quote and quote[key] is not None:
                return str(quote[key])
        if "data" in quote and isinstance(quote["data"], dict):
            return _extract_timestamp(quote["data"])
    return None


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
