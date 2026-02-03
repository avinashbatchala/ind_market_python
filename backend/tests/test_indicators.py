import numpy as np

from app.domain.indicators.rrs_rrv_rve import wilders_rma, true_range, rolling_move, classify


def test_wilders_rma_constant():
    x = np.array([2.0, 2.0, 2.0, 2.0])
    out = wilders_rma(x, 2)
    assert np.allclose(out, x)


def test_true_range_simple():
    high = np.array([10.0, 12.0])
    low = np.array([9.0, 11.0])
    close = np.array([9.5, 11.5])
    tr = true_range(high, low, close)
    assert tr.shape == high.shape
    assert tr[0] == 1.0


def test_rolling_move():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    out = rolling_move(x, 2)
    assert np.isnan(out[0])
    assert np.isnan(out[1])
    assert out[2] == 2.0


def test_classify_basic():
    score, signal = classify(1.0, 1.0, 1.0, np.array([-1.0, 1.0]))
    assert score == 3
    assert signal == "TRIGGER_LONG"
