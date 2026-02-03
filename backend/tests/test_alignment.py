import numpy as np

from app.domain.alignment import align_ohlcv


def test_align_ohlcv_intersection():
    sym = {
        "ts": np.array([1, 2, 3, 4]),
        "open": np.array([1, 1, 1, 1]),
        "high": np.array([2, 2, 2, 2]),
        "low": np.array([0, 0, 0, 0]),
        "close": np.array([1, 1, 1, 1]),
        "volume": np.array([10, 10, 10, 10]),
    }
    ben = {
        "ts": np.array([3, 4, 5]),
        "open": np.array([2, 2, 2]),
        "high": np.array([3, 3, 3]),
        "low": np.array([1, 1, 1]),
        "close": np.array([2, 2, 2]),
        "volume": np.array([20, 20, 20]),
    }
    sym_a, ben_a, common = align_ohlcv(sym, ben)
    assert common.tolist() == [3, 4]
    assert sym_a["close"].shape[0] == 2
    assert ben_a["close"].shape[0] == 2
