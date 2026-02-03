from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas import BenchmarksResponse, ScannerResponse
from app.core.container import get_container, Container

router = APIRouter()


def container_dep() -> Container:
    return get_container()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/scanner", response_model=ScannerResponse)
def get_scanner(
    timeframe: str = Query("5m"),
    container: Container = Depends(container_dep),
) -> ScannerResponse:
    payload = container.redis_cache.get_json(f"scanner:{timeframe}")
    if payload is None:
        payload = container.snapshot_repo.get_latest_snapshot(timeframe)

    if payload is None:
        raise HTTPException(status_code=404, detail="Scanner data not available")

    return ScannerResponse(**payload)


@router.get("/symbol/{symbol}", response_model=ScannerResponse)
def get_symbol(
    symbol: str,
    timeframe: str = Query("5m"),
    container: Container = Depends(container_dep),
) -> ScannerResponse:
    payload = container.redis_cache.get_json(f"scanner:{timeframe}")
    if payload is None:
        payload = container.snapshot_repo.get_latest_snapshot(timeframe)

    if payload is None:
        raise HTTPException(status_code=404, detail="Scanner data not available")

    rows = [row for row in payload.get("rows", []) if row.get("symbol") == symbol]
    if not rows:
        raise HTTPException(status_code=404, detail="Symbol not found")

    return ScannerResponse(timeframe=payload["timeframe"], ts=payload["ts"], rows=rows)


@router.get("/benchmarks", response_model=BenchmarksResponse)
def get_benchmarks(
    timeframe: str = Query("5m"),
    container: Container = Depends(container_dep),
) -> BenchmarksResponse:
    payload = container.redis_cache.get_json(f"benchmarks:{timeframe}")
    if payload is None:
        payload = container.benchmark_repo.get_latest_states(timeframe)

    if payload is None:
        raise HTTPException(status_code=404, detail="Benchmark data not available")

    return BenchmarksResponse(**payload)
