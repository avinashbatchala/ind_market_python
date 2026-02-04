"""
RRS/RRV/RVE indicators with numerical stability utilities.

Enhancements:
- Safe division with denominator floors.
- Power clipping to avoid blow-ups in quiet benchmarks.
- RMS variance proxy option for RRV/RVE.
- Optional winsorization of diffs for robustness.
- Optional percent-ATR normalization for RRS/RVE.

Recommended defaults for NIFTY50 (daily):
- length=20..30, atr_period=14, power_clip=10
- log_volume=True, var_mode="rms"
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Dict, Tuple

import numpy as np

# -----------------------------
# Numerical stability utilities
# -----------------------------

def safe_div(num: np.ndarray, den: np.ndarray, den_floor: np.ndarray | float | None = None) -> np.ndarray:
    num = np.asarray(num, dtype=float)
    den = np.asarray(den, dtype=float)

    if den_floor is None:
        den_floor = rolling_floor(den)

    if np.isscalar(den_floor):
        den_floor_arr = np.full_like(den, float(den_floor))
    else:
        den_floor_arr = np.asarray(den_floor, dtype=float)
        if den_floor_arr.shape != den.shape:
            den_floor_arr = np.full_like(den, float(np.nanmedian(den_floor_arr)))

    den_safe = np.maximum(den, den_floor_arr)
    out = np.full_like(num, np.nan, dtype=float)
    np.divide(num, den_safe, out=out, where=np.isfinite(num) & np.isfinite(den_safe))
    return out


def rolling_floor(
    series: np.ndarray,
    method: str = "quantile",
    window: int = 252,
    q: float = 0.05,
    frac: float = 0.05,
) -> np.ndarray:
    s = np.asarray(series, dtype=float)
    n = s.size
    if n == 0:
        return s

    abs_s = np.abs(s)

    # Fallback for short series
    if n < window:
        base = np.nanmedian(abs_s)
        if not np.isfinite(base) or base == 0:
            base = np.nanmean(abs_s)
        if not np.isfinite(base) or base == 0:
            base = 1e-6
        floor_val = base * (frac if method != "quantile" else frac)
        return np.full_like(s, floor_val, dtype=float)

    try:
        from numpy.lib.stride_tricks import sliding_window_view

        windows = sliding_window_view(abs_s, window_shape=window)
        if method == "quantile":
            qvals = np.nanquantile(windows, q, axis=-1)
            pad = np.full(window - 1, qvals[0])
            return np.concatenate([pad, qvals])
        # median fallback
        med = np.nanmedian(windows, axis=-1)
        pad = np.full(window - 1, med[0] * frac)
        return np.concatenate([pad, med * frac])
    except Exception:
        # conservative fallback
        base = np.nanmedian(abs_s)
        if not np.isfinite(base) or base == 0:
            base = np.nanmean(abs_s)
        if not np.isfinite(base) or base == 0:
            base = 1e-6
        return np.full_like(s, base * frac, dtype=float)


def clip_power(power: np.ndarray, pmax: float = 10.0) -> np.ndarray:
    return np.clip(power, -pmax, pmax)


def winsorize_diff(diff: np.ndarray, q_low: float = 0.01, q_high: float = 0.99) -> np.ndarray:
    d = np.asarray(diff, dtype=float)
    finite = d[np.isfinite(d)]
    if finite.size == 0:
        return d
    low, high = np.quantile(finite, [q_low, q_high])
    return np.clip(d, low, high)


# -----------------------------
# Core indicator math (RRS/RRV/RVE)
# -----------------------------

def wilders_rma(x: np.ndarray, length: int) -> np.ndarray:
    """Wilder's RMA (ta.rma)."""
    out = np.empty_like(x, dtype=float)
    alpha = 1.0 / length
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = out[i - 1] + alpha * (x[i] - out[i - 1])
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


def rolling_log_return(x: np.ndarray, length: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=float)
    out[length:] = np.log(x[length:] / x[:-length])
    return out


def _align_arrays(*arrays: np.ndarray) -> Tuple[np.ndarray, ...]:
    min_len = min(arr.size for arr in arrays)
    return tuple(np.asarray(arr, dtype=float)[:min_len] for arr in arrays)


def _variance_proxy(
    series: np.ndarray,
    length: int,
    var_mode: str,
    winsorize: bool,
    winsor_q: Tuple[float, float],
) -> np.ndarray:
    diff = np.diff(series, prepend=series[0])
    if winsorize:
        diff = winsorize_diff(diff, q_low=winsor_q[0], q_high=winsor_q[1])
    if var_mode == "abs":
        return wilders_rma(np.abs(diff), length)
    if var_mode == "rms":
        return np.sqrt(wilders_rma(diff * diff, length))
    raise ValueError(f"Unsupported var_mode: {var_mode}")


def rrs(
    symbol_ohlc,
    bench_ohlc,
    length: int,
    *,
    use_pct_atr: bool = False,
    pmax: float = 10.0,
    floor_window: int = 252,
    floor_method: str = "quantile",
    floor_q: float = 0.05,
    floor_frac: float = 0.05,
) -> np.ndarray:
    sh, sl, sc = _align_arrays(symbol_ohlc["high"], symbol_ohlc["low"], symbol_ohlc["close"])
    bh, bl, bc = _align_arrays(bench_ohlc["high"], bench_ohlc["low"], bench_ohlc["close"])

    if use_pct_atr:
        sym_move = rolling_log_return(sc, length)
        ben_move = rolling_log_return(bc, length)
    else:
        sym_move = rolling_move(sc, length)
        ben_move = rolling_move(bc, length)

    sym_atr = wilders_rma(true_range(sh, sl, sc), length)
    ben_atr = wilders_rma(true_range(bh, bl, bc), length)

    if use_pct_atr:
        sym_atr = safe_div(sym_atr, sc, rolling_floor(sc, window=floor_window, method=floor_method, q=floor_q, frac=floor_frac))
        ben_atr = safe_div(ben_atr, bc, rolling_floor(bc, window=floor_window, method=floor_method, q=floor_q, frac=floor_frac))

    ben_floor = rolling_floor(ben_atr, window=floor_window, method=floor_method, q=floor_q, frac=floor_frac)
    sym_floor = rolling_floor(sym_atr, window=floor_window, method=floor_method, q=floor_q, frac=floor_frac)

    power = clip_power(safe_div(ben_move, ben_atr, ben_floor), pmax=pmax)
    expected = power * sym_atr
    diff = sym_move - expected
    out = safe_div(diff, sym_atr, sym_floor)
    return out


def rrv(
    symbol_vol: np.ndarray,
    bench_vol: np.ndarray,
    length: int,
    smooth: int = 3,
    use_log: bool = True,
    *,
    var_mode: str = "rms",
    winsorize: bool = True,
    winsor_q: Tuple[float, float] = (0.01, 0.99),
    pmax: float = 10.0,
    floor_window: int = 252,
    floor_method: str = "quantile",
    floor_q: float = 0.05,
    floor_frac: float = 0.05,
) -> np.ndarray:
    def sma(x, n):
        if n <= 1:
            return x.astype(float)
        w = np.ones(n) / n
        return np.convolve(x, w, mode="same")

    v_sym = sma(symbol_vol.astype(float), smooth)
    v_ben = sma(bench_vol.astype(float), smooth)

    if use_log:
        v_sym = np.log(np.maximum(v_sym, 1.0))
        v_ben = np.log(np.maximum(v_ben, 1.0))

    v_sym, v_ben = _align_arrays(v_sym, v_ben)

    sym_move = rolling_move(v_sym, length)
    ben_move = rolling_move(v_ben, length)

    sym_var = _variance_proxy(v_sym, length, var_mode, winsorize, winsor_q)
    ben_var = _variance_proxy(v_ben, length, var_mode, winsorize, winsor_q)

    ben_floor = rolling_floor(ben_var, window=floor_window, method=floor_method, q=floor_q, frac=floor_frac)
    sym_floor = rolling_floor(sym_var, window=floor_window, method=floor_method, q=floor_q, frac=floor_frac)

    power = clip_power(safe_div(ben_move, ben_var, ben_floor), pmax=pmax)
    expected = power * sym_var
    diff = sym_move - expected
    out = safe_div(diff, sym_var, sym_floor)
    return out


def rve(
    symbol_ohlc,
    bench_ohlc,
    length: int,
    atr_period: int = 14,
    smooth_atr: int = 1,
    *,
    use_pct_atr: bool = False,
    var_mode: str = "rms",
    winsorize: bool = True,
    winsor_q: Tuple[float, float] = (0.01, 0.99),
    pmax: float = 10.0,
    floor_window: int = 252,
    floor_method: str = "quantile",
    floor_q: float = 0.05,
    floor_frac: float = 0.05,
) -> np.ndarray:
    sh, sl, sc = _align_arrays(symbol_ohlc["high"], symbol_ohlc["low"], symbol_ohlc["close"])
    bh, bl, bc = _align_arrays(bench_ohlc["high"], bench_ohlc["low"], bench_ohlc["close"])

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

    if use_pct_atr:
        sym_atr = safe_div(sym_atr, sc, rolling_floor(sc, window=floor_window, method=floor_method, q=floor_q, frac=floor_frac))
        ben_atr = safe_div(ben_atr, bc, rolling_floor(bc, window=floor_window, method=floor_method, q=floor_q, frac=floor_frac))

    sym_move = rolling_move(sym_atr, length)
    ben_move = rolling_move(ben_atr, length)

    sym_var = _variance_proxy(sym_atr, length, var_mode, winsorize, winsor_q)
    ben_var = _variance_proxy(ben_atr, length, var_mode, winsorize, winsor_q)

    ben_floor = rolling_floor(ben_var, window=floor_window, method=floor_method, q=floor_q, frac=floor_frac)
    sym_floor = rolling_floor(sym_var, window=floor_window, method=floor_method, q=floor_q, frac=floor_frac)

    power = clip_power(safe_div(ben_move, ben_var, ben_floor), pmax=pmax)
    expected = power * sym_var
    diff = sym_move - expected
    out = safe_div(diff, sym_var, sym_floor)
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
    bench_ohlc = {k: bench_data[k] for k in ["high", "low", "close"]}
    bench_vol = bench_data["volume"]

    results = []
    for sym in universe:
        d = fetch_ohlcv(sym, timeframe, bars)
        sym_ohlc = {k: d[k] for k in ["high", "low", "close"]}
        sym_vol = d["volume"]

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
