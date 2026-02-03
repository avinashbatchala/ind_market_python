from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Optional


class InstrumentStore:
    """
    Loads the official Groww instruments CSV to map trading symbols.

    TODO: Wire this into ingestion for symbol-to-groww_symbol lookups.
    """

    def __init__(self, csv_path: str | None = None) -> None:
        self.csv_path = csv_path
        self._map: Dict[str, dict] = {}

    def load(self) -> None:
        if not self.csv_path:
            return
        path = Path(self.csv_path)
        if not path.exists():
            return

        with path.open("r", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                symbol = row.get("trading_symbol") or row.get("symbol") or ""
                if symbol:
                    self._map[symbol] = row

    def get(self, trading_symbol: str) -> Optional[dict]:
        return self._map.get(trading_symbol)
