import numpy as np
import numpy.testing as npt

from app.domain.indicators.rrs_rrv_rve import (
    wilders_rma,
    true_range,
    rolling_move,
    rrs,
    rrv,
    rve,
    crosses_up,
    crosses_down,
    classify,
)


def test_wilders_rma_basic():
    x = np.array([1.0, 2.0, 3.0])
    out = wilders_rma(x, length=2)
    npt.assert_allclose(out, np.array([1.0, 1.5, 2.25]), rtol=1e-6)


def test_true_range_basic():
    high = np.array([10.0, 12.0, 11.0])
    low = np.array([8.0, 9.0, 9.5])
    close = np.array([9.0, 10.0, 10.5])
    tr = true_range(high, low, close)
    # prev_close for index 0 is close[0]
    expected = np.array([
        2.0,  # max(12-9=3, abs(12-9)=3, abs(9-9)=0) -> 3? wait compute properly below
        3.0,
        1.5,
    ])
    # compute expected carefully
    # i=0: max(high-low=2, abs(high-prev_close)=1, abs(low-prev_close)=1) = 2
    # i=1: prev_close=9, max(12-9=3, abs(12-9)=3, abs(9-9)=0)=3
    # i=2: prev_close=10, max(11-9.5=1.5, abs(11-10)=1, abs(9.5-10)=0.5)=1.5
    npt.assert_allclose(tr, expected, rtol=1e-6)


def test_rolling_move():
    x = np.array([1.0, 2.0, 4.0, 7.0])
    out = rolling_move(x, length=2)
    assert np.isnan(out[0])
    assert np.isnan(out[1])
    npt.assert_allclose(out[2:], np.array([3.0, 5.0]), rtol=1e-6)


def test_rrs_rrv_rve_shapes_and_finite():
    n = 60
    sym = {
        "high": np.linspace(101, 160, n),
        "low": np.linspace(99, 158, n),
        "close": np.linspace(100, 159, n),
        "volume": np.linspace(1000, 2000, n),
    }
    ben = {
        "high": np.linspace(201, 260, n),
        "low": np.linspace(199, 258, n),
        "close": np.linspace(200, 259, n),
        "volume": np.linspace(1500, 2500, n),
    }

    rrs_series = rrs({k: sym[k] for k in ["high", "low", "close"]}, {k: ben[k] for k in ["high", "low", "close"]}, length=12)
    rrv_series = rrv(sym["volume"], ben["volume"], length=12, smooth=3, use_log=True)
    rve_series = rve({k: sym[k] for k in ["high", "low", "close"]}, {k: ben[k] for k in ["high", "low", "close"]}, length=12, atr_period=14, smooth_atr=1)

    assert rrs_series.shape[0] == n
    assert rrv_series.shape[0] == n
    assert rve_series.shape[0] == n

    # last values should be finite for monotonic series
    assert np.isfinite(rrs_series[-1])
    assert np.isfinite(rrv_series[-1])
    assert np.isfinite(rve_series[-1])


def test_crosses_up_down_and_classify():
    series = np.array([-0.5, -0.1, 0.2])
    assert crosses_up(series, 0.0) is True
    assert crosses_down(series, 0.0) is False

    series2 = np.array([0.5, 0.1, -0.2])
    assert crosses_down(series2, 0.0) is True
    assert crosses_up(series2, 0.0) is False

    # classify scenarios
    rrs_series = np.array([-0.1, 0.2])
    assert classify(0.2, 1.0, 1.0, rrs_series) == "TRIGGER_LONG"

    rrs_series = np.array([0.2, -0.2])
    assert classify(-0.2, -1.0, -1.0, rrs_series) == "TRIGGER_SHORT"

    rrs_series = np.array([-0.5, -0.2])
    assert classify(-0.2, 1.0, 1.0, rrs_series) == "WATCH"

    rrs_series = np.array([0.1, -0.1])
    assert classify(-0.1, -0.1, 0.1, rrs_series) == "EXIT/AVOID"

    rrs_series = np.array([0.1, 0.1])
    assert classify(0.1, 0.0, 0.0, rrs_series) == "NEUTRAL"
