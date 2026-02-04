import numpy as np

from app.services.relative_metrics import compute_relative_metrics


def test_compute_relative_metrics_pipeline():
    ts = np.arange(50)
    stock = {
        "ts": ts,
        "open": np.linspace(100, 150, 50),
        "high": np.linspace(101, 151, 50),
        "low": np.linspace(99, 149, 50),
        "close": np.linspace(100, 150, 50),
        "volume": np.linspace(1000, 2000, 50),
    }
    bench = {
        "ts": ts,
        "open": np.linspace(200, 250, 50),
        "high": np.linspace(201, 251, 50),
        "low": np.linspace(199, 249, 50),
        "close": np.linspace(200, 250, 50),
        "volume": np.linspace(1500, 2500, 50),
    }

    metrics = compute_relative_metrics(stock, bench)
    assert metrics is not None
    assert "rrs" in metrics
    assert "rrv" in metrics
    assert "rve" in metrics
    assert "signal" in metrics
    assert "updated_at" in metrics
