import math
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

# -----------------------------
# Core indicator math (RRS/RRV/RVE)
# -----------------------------

def wilders_rma(x: np.ndarray, length: int) -> np.ndarray:
    """Wilder's RMA (ta.rma)."""
    out = np.empty_like(x, dtype=float)
    alpha = 1.0 / length
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = out[i-1] + alpha * (x[i] - out[i-1])
    return out

def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    return tr

def rolling_move(x: np.ndarray, length: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=float)
    out[length:] = x[length:] - x[:-length]
    return out

def rrs(symbol_ohlc, bench_ohlc, length: int) -> np.ndarray:
    sh, sl, sc = symbol_ohlc["high"], symbol_ohlc["low"], symbol_ohlc["close"]
    bh, bl, bc = bench_ohlc["high"], bench_ohlc["low"], bench_ohlc["close"]

    sym_move = rolling_move(sc, length)
    ben_move = rolling_move(bc, length)

    sym_atr = wilders_rma(true_range(sh, sl, sc), length)
    ben_atr = wilders_rma(true_range(bh, bl, bc), length)

    power = np.where(ben_atr != 0, ben_move / ben_atr, 0.0)
    expected = power * sym_atr
    diff = sym_move - expected
    out = np.where(sym_atr != 0, diff / sym_atr, 0.0)
    return out

def rrv(symbol_vol: np.ndarray, bench_vol: np.ndarray, length: int, smooth: int = 3, use_log: bool = True) -> np.ndarray:
    def sma(x, n):
        if n <= 1: return x.astype(float)
        w = np.ones(n) / n
        return np.convolve(x, w, mode="same")

    v_sym = sma(symbol_vol.astype(float), smooth)
    v_ben = sma(bench_vol.astype(float), smooth)

    if use_log:
        v_sym = np.log(np.maximum(v_sym, 1.0))
        v_ben = np.log(np.maximum(v_ben, 1.0))

    sym_move = rolling_move(v_sym, length)
    ben_move = rolling_move(v_ben, length)

    sym_var = wilders_rma(np.abs(np.diff(v_sym, prepend=v_sym[0])), length)
    ben_var = wilders_rma(np.abs(np.diff(v_ben, prepend=v_ben[0])), length)

    power = np.where(ben_var != 0, ben_move / ben_var, 0.0)
    expected = power * sym_var
    diff = sym_move - expected
    out = np.where(sym_var != 0, diff / sym_var, 0.0)
    return out

def rve(symbol_ohlc, bench_ohlc, length: int, atr_period: int = 14, smooth_atr: int = 1) -> np.ndarray:
    sh, sl, sc = symbol_ohlc["high"], symbol_ohlc["low"], symbol_ohlc["close"]
    bh, bl, bc = bench_ohlc["high"], bench_ohlc["low"], bench_ohlc["close"]

    sym_atr_raw = wilders_rma(true_range(sh, sl, sc), atr_period)
    ben_atr_raw = wilders_rma(true_range(bh, bl, bc), atr_period)

    # optional smoothing
    if smooth_atr > 1:
        def sma(x, n):
            w = np.ones(n) / n
            return np.convolve(x, w, mode="same")
        sym_atr = sma(sym_atr_raw, smooth_atr)
        ben_atr = sma(ben_atr_raw, smooth_atr)
    else:
        sym_atr, ben_atr = sym_atr_raw, ben_atr_raw

    sym_move = rolling_move(sym_atr, length)
    ben_move = rolling_move(ben_atr, length)

    sym_var = wilders_rma(np.abs(np.diff(sym_atr, prepend=sym_atr[0])), length)
    ben_var = wilders_rma(np.abs(np.diff(ben_atr, prepend=ben_atr[0])), length)

    power = np.where(ben_var != 0, ben_move / ben_var, 0.0)
    expected = power * sym_var
    diff = sym_move - expected
    out = np.where(sym_var != 0, diff / sym_var, 0.0)
    return out

# -----------------------------
# Signals
# -----------------------------

def crosses_up(x: np.ndarray, level: float = 0.0) -> bool:
    return len(x) > 1 and (x[-2] <= level) and (x[-1] > level)

def crosses_down(x: np.ndarray, level: float = 0.0) -> bool:
    return len(x) > 1 and (x[-2] >= level) and (x[-1] < level)

@dataclass
class ScreenResult:
    symbol: str
    rrs: float
    rrv: float
    rve: float
    signal: str

def classify(rrs_val, rrv_val, rve_val, rrs_series) -> str:
    if crosses_up(rrs_series, 0.0) and rrv_val > 0 and rve_val > 0:
        return "TRIGGER_LONG"
    if crosses_down(rrs_series, 0.0) and rrv_val < 0 and rve_val < 0:
        return "TRIGGER_SHORT"
    if rve_val > 0 and rrv_val > 0 and rrs_val < 0 and (rrs_series[-1] > rrs_series[-2]):
        return "WATCH"
    if crosses_down(rrs_series, 0.0) or rve_val < 0 or rrv_val < 0:
        return "EXIT/AVOID"
    return "NEUTRAL"

# -----------------------------
# You plug in Groww historical fetch here
# -----------------------------

def fetch_ohlcv(symbol: str, timeframe: str, bars: int) -> Dict[str, np.ndarray]:
    """
    TODO: Implement using Groww historical endpoints.
    Must return dict with 'open','high','low','close','volume' arrays aligned in time.
    """
    raise NotImplementedError

def run_screener(universe: List[str], bench: str, timeframe: str = "5m", bars: int = 200,
                 length: int = 12, atr_period: int = 14) -> List[ScreenResult]:

    bench_data = fetch_ohlcv(bench, timeframe, bars)
    bench_ohlc = {k: bench_data[k] for k in ["high","low","close"]}
    bench_vol  = bench_data["volume"]

    results = []
    for sym in universe:
        d = fetch_ohlcv(sym, timeframe, bars)
        sym_ohlc = {k: d[k] for k in ["high","low","close"]}
        sym_vol  = d["volume"]

        rrs_series = rrs(sym_ohlc, bench_ohlc, length)
        rrv_series = rrv(sym_vol, bench_vol, length, smooth=3, use_log=True)
        rve_series = rve(sym_ohlc, bench_ohlc, length, atr_period=atr_period, smooth_atr=1)

        rrs_val = float(rrs_series[-1])
        rrv_val = float(rrv_series[-1])
        rve_val = float(rve_series[-1])

        sig = classify(rrs_val, rrv_val, rve_val, rrs_series)

        results.append(ScreenResult(sym, rrs_val, rrv_val, rve_val, sig))

    # rank: signal first, then strength of move
    sig_rank = {
        "TRIGGER_LONG": 0,
        "TRIGGER_SHORT": 1,
        "WATCH": 2,
        "NEUTRAL": 3,
        "EXIT/AVOID": 4,
    }
    results.sort(key=lambda r: (sig_rank.get(r.signal, 9), -abs(r.rrs), -abs(r.rve)))
    return results
