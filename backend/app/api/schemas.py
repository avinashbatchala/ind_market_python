from __future__ import annotations

from typing import List
from pydantic import BaseModel


class ScannerRow(BaseModel):
    symbol: str
    timeframe: str
    benchmark_symbol: str
    rrs: float
    rrv: float
    rve: float
    signal: str


class ScannerResponse(BaseModel):
    timeframe: str
    ts: str
    rows: List[ScannerRow]


class BenchmarkState(BaseModel):
    benchmark: str
    timeframe: str
    ts: str
    regime: str
    trend: float
    vol_expansion: float
    participation: float


class BenchmarksResponse(BaseModel):
    timeframe: str
    ts: str
    states: List[BenchmarkState]


class WatchStockBase(BaseModel):
    symbol: str
    name: str | None = None
    active: bool = True
    industry_index_symbols: List[str] = []


class WatchStockCreate(WatchStockBase):
    pass


class WatchStockUpdate(BaseModel):
    symbol: str | None = None
    name: str | None = None
    active: bool | None = None
    industry_index_symbols: List[str] | None = None


class WatchStock(WatchStockBase):
    id: int


class WatchIndexBase(BaseModel):
    symbol: str
    data_symbol: str | None = None
    name: str | None = None
    active: bool = True


class WatchIndexCreate(WatchIndexBase):
    pass


class WatchIndexUpdate(BaseModel):
    symbol: str | None = None
    data_symbol: str | None = None
    name: str | None = None
    active: bool | None = None


class WatchIndex(WatchIndexBase):
    id: int
