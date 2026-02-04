from __future__ import annotations

from typing import List

from app.core.config import Settings
from app.infra.db.repositories import TickerIndexRepository


def get_associated_indices(
    symbol: str,
    settings: Settings,
    ticker_index_repo: TickerIndexRepository,
) -> List[str]:
    """
    Always include NIFTY first, then any additional indices from ticker_index.
    Deduplicate and keep stable ordering (NIFTY first, others sorted).
    """
    cleaned_symbol = symbol.strip().upper()
    default_symbol = settings.nifty_symbol
    extra = [s.strip().upper() for s in ticker_index_repo.get_indices_for_stock(cleaned_symbol) if s]

    dedup = []
    seen = set()

    if default_symbol:
        dedup.append(default_symbol)
        seen.add(default_symbol)

    for item in sorted(extra):
        if item in seen:
            continue
        dedup.append(item)
        seen.add(item)

    return dedup
