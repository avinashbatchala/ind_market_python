from __future__ import annotations

from typing import List
from pydantic import BaseModel


class ScannerRow(BaseModel):
    symbol: str
    timeframe: str
    rrs_vs_nifty: float
    rrv_vs_nifty: float
    rve_vs_nifty: float
    score_vs_nifty: int
    signal_vs_nifty: str
    rrs_vs_bank: float
    rrv_vs_bank: float
    rve_vs_bank: float
    score_vs_bank: int
    signal_vs_bank: str
    best_signal: str


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
