import numpy as np
import numpy.testing as npt

from app.domain.indicators.rrs_rrv_rve import (
    safe_div,
    rolling_floor,
    clip_power,
    rrs,
    rrv,
    rve,
)


def test_safe_div_with_floor_scalar():
    num = np.array([1.0, 2.0, 3.0])
    den = np.array([0.0, 0.5, 2.0])
    out = safe_div(num, den, den_floor=1.0)
    npt.assert_allclose(out, np.array([1.0, 2.0, 1.5]), rtol=1e-6)


def test_safe_div_with_floor_array():
    num = np.array([1.0, 2.0, 3.0])
    den = np.array([0.0, 0.5, 2.0])
    floor = np.array([0.2, 0.6, 0.1])
    out = safe_div(num, den, den_floor=floor)
    npt.assert_allclose(out, np.array([5.0, 3.3333333, 1.5]), rtol=1e-6)


def test_rolling_floor_length_and_positive():
    series = np.linspace(1, 10, 100)
    floor = rolling_floor(series, window=20)
    assert floor.shape == series.shape
    assert np.all(floor >= 0)


def test_clip_power():
    power = np.array([-100.0, -5.0, 0.0, 5.0, 100.0])
    clipped = clip_power(power, pmax=10.0)
    npt.assert_allclose(clipped, np.array([-10.0, -5.0, 0.0, 5.0, 10.0]))


def test_rrs_rrv_rve_warmup_nan():
    n = 40
    sym = {
        "high": np.linspace(101, 140, n),
        "low": np.linspace(99, 138, n),
        "close": np.linspace(100, 139, n),
    }
    ben = {
        "high": np.linspace(201, 240, n),
        "low": np.linspace(199, 238, n),
        "close": np.linspace(200, 239, n),
    }
    vol_sym = np.linspace(1000, 2000, n)
    vol_ben = np.linspace(1500, 2500, n)

    rrs_series = rrs(sym, ben, length=12)
    rrv_series = rrv(vol_sym, vol_ben, length=12)
    rve_series = rve(sym, ben, length=12)

    assert np.isnan(rrs_series[:12]).any()
    assert np.isnan(rrv_series[:12]).any()
    assert np.isnan(rve_series[:12]).any()


def test_rrv_var_mode_switch_changes_output():
    n = 80
    vol_sym = np.concatenate([np.ones(40) * 1000, np.ones(40) * 5000])
    vol_ben = np.concatenate([np.ones(40) * 1200, np.ones(40) * 5200])

    rrv_abs = rrv(vol_sym, vol_ben, length=12, var_mode="abs", winsorize=False)
    rrv_rms = rrv(vol_sym, vol_ben, length=12, var_mode="rms", winsorize=False)

    # Ensure the series differ for non-trivial inputs
    assert not np.allclose(rrv_abs, rrv_rms, equal_nan=True)
