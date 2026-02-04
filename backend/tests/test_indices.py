from app.core.config import Settings
from app.services.indices import get_associated_indices


class FakeTickerIndexRepo:
    def __init__(self, mapping):
        self.mapping = mapping

    def get_indices_for_stock(self, symbol: str):
        return self.mapping.get(symbol, [])


def test_get_associated_indices_includes_nifty_and_dedupes():
    settings = Settings(NIFTY_SYMBOL="NIFTY")
    repo = FakeTickerIndexRepo({"SBIN": ["BANKNIFTY", "NIFTY", "AUTO"]})
    indices = get_associated_indices("sbin", settings, repo)
    assert indices[0] == "NIFTY"
    assert indices == ["NIFTY", "AUTO", "BANKNIFTY"]
