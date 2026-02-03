from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas import (
    BenchmarksResponse,
    ScannerResponse,
    WatchStock,
    WatchStockCreate,
    WatchStockUpdate,
    WatchIndex,
    WatchIndexCreate,
    WatchIndexUpdate,
)
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


@router.get("/admin/stocks", response_model=List[WatchStock])
def list_stocks(container: Container = Depends(container_dep)) -> List[WatchStock]:
    rows = container.watch_stock_repo.list()
    return [WatchStock(**row) for row in rows]


@router.post("/admin/stocks", response_model=WatchStock)
def create_stock(payload: WatchStockCreate, container: Container = Depends(container_dep)) -> WatchStock:
    symbol = payload.symbol.strip().upper()
    industry_symbol = payload.industry_index_symbol.strip().upper() if payload.industry_index_symbol else None

    if industry_symbol:
        if not container.watch_index_repo.exists(industry_symbol):
            raise HTTPException(status_code=400, detail="Industry index not found")
    stock = container.watch_stock_repo.create(symbol, payload.name, payload.active)
    if industry_symbol:
        container.ticker_index_repo.set_mapping(stock.symbol, industry_symbol)
    return WatchStock(
        id=stock.id,
        symbol=stock.symbol,
        name=stock.name,
        active=stock.active,
        industry_index_symbol=industry_symbol,
    )


@router.patch("/admin/stocks/{stock_id}", response_model=WatchStock)
def update_stock(
    stock_id: int,
    payload: WatchStockUpdate,
    container: Container = Depends(container_dep),
) -> WatchStock:
    existing_fields = container.watch_stock_repo.get_fields(stock_id)
    if existing_fields is None:
        raise HTTPException(status_code=404, detail="Stock not found")

    industry_symbol = payload.industry_index_symbol.strip().upper() if payload.industry_index_symbol else None
    symbol = payload.symbol.strip().upper() if payload.symbol else None

    if industry_symbol:
        if not container.watch_index_repo.exists(industry_symbol):
            raise HTTPException(status_code=400, detail="Industry index not found")

    old_symbol = existing_fields["symbol"]
    existing_index = container.ticker_index_repo.get_index_for_stock(old_symbol)
    stock = container.watch_stock_repo.update(stock_id, symbol, payload.name, payload.active)

    if symbol and symbol != old_symbol:
        container.ticker_index_repo.clear_mapping(old_symbol)

    if payload.industry_index_symbol is not None:
        if industry_symbol:
            container.ticker_index_repo.set_mapping(stock.symbol, industry_symbol)
        else:
            container.ticker_index_repo.clear_mapping(stock.symbol)
    elif symbol and symbol != old_symbol and existing_index:
        container.ticker_index_repo.set_mapping(stock.symbol, existing_index)

    current_index = container.ticker_index_repo.get_index_for_stock(stock.symbol)
    return WatchStock(
        id=stock.id,
        symbol=stock.symbol,
        name=stock.name,
        active=stock.active,
        industry_index_symbol=current_index,
    )


@router.delete("/admin/stocks/{stock_id}")
def delete_stock(stock_id: int, container: Container = Depends(container_dep)) -> dict:
    try:
        stock = container.watch_stock_repo.get(stock_id)
        if stock is None:
            raise HTTPException(status_code=404, detail="Stock not found")
        container.ticker_index_repo.clear_mapping(stock.symbol)
        container.watch_stock_repo.delete(stock_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Stock not found")
    return {"status": "ok"}


@router.get("/admin/indices", response_model=List[WatchIndex])
def list_indices(container: Container = Depends(container_dep)) -> List[WatchIndex]:
    rows = container.watch_index_repo.list()
    return [WatchIndex(**row) for row in rows]


@router.post("/admin/indices", response_model=WatchIndex)
def create_index(payload: WatchIndexCreate, container: Container = Depends(container_dep)) -> WatchIndex:
    symbol = payload.symbol.strip().upper()
    index = container.watch_index_repo.create(symbol, payload.name, payload.active)
    return WatchIndex(id=index.id, symbol=index.symbol, name=index.name, active=index.active)


@router.patch("/admin/indices/{index_id}", response_model=WatchIndex)
def update_index(
    index_id: int,
    payload: WatchIndexUpdate,
    container: Container = Depends(container_dep),
) -> WatchIndex:
    existing = container.watch_index_repo.get(index_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Index not found")
    old_symbol = existing.symbol
    symbol = payload.symbol.strip().upper() if payload.symbol else None
    index = container.watch_index_repo.update(index_id, symbol, payload.name, payload.active)
    if symbol and symbol != old_symbol:
        container.ticker_index_repo.move_index_symbol(old_symbol, symbol)
    return WatchIndex(id=index.id, symbol=index.symbol, name=index.name, active=index.active)


@router.delete("/admin/indices/{index_id}")
def delete_index(index_id: int, container: Container = Depends(container_dep)) -> dict:
    try:
        container.watch_index_repo.delete(index_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Index not found")
    return {"status": "ok"}
