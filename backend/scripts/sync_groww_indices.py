import csv
import io
import os
import re
import sys
import urllib.request
from typing import Dict, Iterable, List, Optional, Tuple

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.config import Settings
from app.infra.db.session import Database
from app.infra.db.repositories import WatchIndexRepository

INSTRUMENTS_URL = "https://growwapi-assets.groww.in/instruments/instrument.csv"


def _normalize(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _pick_field(fieldnames: List[str], candidates: List[str]) -> Optional[str]:
    lower_map = {name.lower(): name for name in fieldnames}
    for candidate in candidates:
        if candidate in fieldnames:
            return candidate
        lower = candidate.lower()
        if lower in lower_map:
            return lower_map[lower]
    return None


def _iter_instruments(url: str) -> Iterable[Dict[str, str]]:
    with urllib.request.urlopen(url) as response:
        wrapper = io.TextIOWrapper(response, encoding="utf-8", errors="ignore")
        reader = csv.DictReader(wrapper)
        fieldnames = reader.fieldnames or []
        trading_field = _pick_field(fieldnames, ["trading_symbol", "tradingsymbol", "symbol"])
        name_field = _pick_field(fieldnames, ["name", "instrument_name"])
        exchange_field = _pick_field(fieldnames, ["exchange"])
        segment_field = _pick_field(fieldnames, ["segment"])
        type_field = _pick_field(fieldnames, ["instrument_type", "instrumenttype", "type"])

        if not trading_field:
            raise RuntimeError("Could not find trading symbol column in instruments CSV")

        for row in reader:
            trading_symbol = (row.get(trading_field) or "").strip()
            if not trading_symbol:
                continue
            yield {
                "trading_symbol": trading_symbol,
                "name": (row.get(name_field) or "").strip() if name_field else "",
                "exchange": (row.get(exchange_field) or "").strip() if exchange_field else "",
                "segment": (row.get(segment_field) or "").strip() if segment_field else "",
                "instrument_type": (row.get(type_field) or "").strip() if type_field else "",
            }


def _is_index_row(row: Dict[str, str]) -> bool:
    exchange = row.get("exchange", "").upper()
    segment = row.get("segment", "").upper()
    instrument_type = row.get("instrument_type", "").upper()
    name = row.get("name", "").upper()
    trading = row.get("trading_symbol", "").upper()

    if exchange and exchange != "NSE":
        return False
    if segment and segment != "CASH":
        return False
    if instrument_type:
        return "INDEX" in instrument_type
    return "NIFTY" in name or "NIFTY" in trading


def _score_match(target: str, candidate: str) -> int:
    if not target or not candidate:
        return 0
    if target == candidate:
        return 100
    if candidate.startswith(target) or target.startswith(candidate):
        return 90
    if target in candidate or candidate in target:
        return 70
    return 0


def _best_match(
    symbol: str,
    name: Optional[str],
    rows: List[Dict[str, str]],
) -> Optional[str]:
    symbol_norm = _normalize(symbol)
    name_norm = _normalize(name or "")

    best: Tuple[int, str] | None = None

    for row in rows:
        trading = row["trading_symbol"]
        trading_norm = _normalize(trading)
        row_name_norm = _normalize(row.get("name", ""))

        score = max(
            _score_match(symbol_norm, trading_norm),
            _score_match(symbol_norm, row_name_norm),
            _score_match(name_norm, trading_norm),
            _score_match(name_norm, row_name_norm),
        )

        if score == 0:
            continue

        if best is None or score > best[0] or (score == best[0] and len(trading) < len(best[1])):
            best = (score, trading)

    return best[1] if best else None


def sync_indices(apply_changes: bool = True) -> None:
    settings = Settings()
    db = Database(settings.database_url)
    repo = WatchIndexRepository(db)

    indices = repo.list()
    if not indices:
        print("No indices found in watch_indices.")
        return

    try:
        rows = [row for row in _iter_instruments(INSTRUMENTS_URL) if _is_index_row(row)]
    except Exception as exc:
        raise RuntimeError(f"Failed to download instruments CSV: {exc}")

    updated = 0
    missing = []

    for index in indices:
        match = _best_match(index["symbol"], index.get("name"), rows)
        if not match:
            missing.append(index["symbol"])
            continue
        if index.get("data_symbol") == match:
            continue
        if apply_changes:
            repo.update(index["id"], None, None, None, data_symbol=match)
        updated += 1
        print(f"{index['symbol']}: data_symbol -> {match}")

    print(f"Updated {updated} indices.")
    if missing:
        print("No match for:", ", ".join(sorted(missing)))


if __name__ == "__main__":
    apply_flag = "--dry-run" not in sys.argv
    if not apply_flag:
        print("Running in dry-run mode (no DB updates). Use without --dry-run to apply changes.")
    sync_indices(apply_changes=apply_flag)
