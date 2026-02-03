from __future__ import annotations

from typing import Dict, Tuple
import numpy as np


def align_ohlcv(
    symbol: Dict[str, np.ndarray],
    bench: Dict[str, np.ndarray],
) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray], np.ndarray]:
    """
    Align two OHLCV dicts by timestamp intersection.
    Returns aligned (symbol, bench, common_ts).
    """
    sym_ts = np.asarray(symbol["ts"], dtype="int64")
    ben_ts = np.asarray(bench["ts"], dtype="int64")

    common_ts = np.intersect1d(sym_ts, ben_ts, assume_unique=False)
    if common_ts.size == 0:
        return symbol, bench, common_ts

    sym_idx = np.searchsorted(sym_ts, common_ts)
    ben_idx = np.searchsorted(ben_ts, common_ts)

    def slice_dict(data: Dict[str, np.ndarray], idx: np.ndarray) -> Dict[str, np.ndarray]:
        return {k: np.asarray(v)[idx] for k, v in data.items() if k != "ts"}

    sym_aligned = slice_dict(symbol, sym_idx)
    ben_aligned = slice_dict(bench, ben_idx)

    return sym_aligned, ben_aligned, common_ts
