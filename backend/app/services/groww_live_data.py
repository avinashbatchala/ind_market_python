from __future__ import annotations

from typing import Any, Optional
import inspect

from app.core.config import Settings
from app.infra.groww.client import GrowwClient, RealGrowwClient


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
            if not trading_symbol or not expiry:
                errors["greeks"] = "Missing trading_symbol or expiry for greeks"
            else:
                greeks = _safe_call(
                    lambda: _call_supported(
                        client.get_greeks,
                        exchange=exchange_const,
                        underlying=underlying or symbol,
                        trading_symbol=trading_symbol,
                        expiry=expiry,
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
        expiries = None
        if hasattr(client, "get_expiries"):
            expiries = _safe_call(
                lambda: _call_supported(
                    client.get_expiries,
                    exchange=exchange_const,
                    underlying_symbol=underlying_symbol,
                    year=year,
                    month=month,
                ),
                errors,
                "expiries",
            )
        else:
            errors["expiries"] = "SDK missing get_expiries"

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
