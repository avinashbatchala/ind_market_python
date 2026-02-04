from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas import (
    BenchmarksResponse,
    ScannerResponse,
    LiveDataResponse,
    ExpiriesResponse,
    RelativeMetricsResponse,
    WatchStock,
    WatchStockCreate,
    WatchStockUpdate,
    WatchIndex,
    WatchIndexCreate,
    WatchIndexUpdate,
)
from app.core.container import get_container, Container
from app.services.groww_live_data import GrowwLiveDataService
from app.services.relative_metrics import RelativeMetricsService

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


@router.get("/stocks/{symbol}/live", response_model=LiveDataResponse)
def get_stock_live(
    symbol: str,
    exchange: str = Query(None),
    segment: str = Query(None),
    expiry: str | None = Query(None),
    option_type: str | None = Query(None),
    underlying: str | None = Query(None),
    trading_symbol: str | None = Query(None),
    expiry_date: str | None = Query(None),
    container: Container = Depends(container_dep),
) -> LiveDataResponse:
    service = GrowwLiveDataService(container.settings, container.groww_client)
    payload = service.fetch_live(
        symbol=symbol.strip().upper(),
        exchange=(exchange or container.settings.groww_exchange).upper(),
        segment=(segment or container.settings.groww_segment).upper(),
        expiry=expiry,
        option_type=option_type,
        underlying=underlying,
        trading_symbol=trading_symbol,
        expiry_date=expiry_date,
    )
    return LiveDataResponse(**payload)


@router.get("/stocks/{symbol}/relative-metrics", response_model=RelativeMetricsResponse)
def get_stock_relative_metrics(
    symbol: str,
    interval: str = Query("5m"),
    lookback: int = Query(None),
    container: Container = Depends(container_dep),
) -> RelativeMetricsResponse:
    if lookback is None:
        lookback = container.settings.compute_bars
    service = RelativeMetricsService(
        settings=container.settings,
        candle_repo=container.candle_repo,
        ticker_index_repo=container.ticker_index_repo,
        watch_index_repo=container.watch_index_repo,
        cache=container.redis_cache,
    )
    payload = service.get_metrics(symbol, interval, lookback)
    return RelativeMetricsResponse(**payload)


@router.get("/stocks/{symbol}/expiries", response_model=ExpiriesResponse)
def get_stock_expiries(
    symbol: str,
    exchange: str = Query(None),
    year: int | None = Query(None),
    month: int | None = Query(None),
    container: Container = Depends(container_dep),
) -> ExpiriesResponse:
    service = GrowwLiveDataService(container.settings, container.groww_client)
    payload = service.fetch_expiries(
        exchange=(exchange or container.settings.groww_exchange).upper(),
        underlying_symbol=symbol.strip().upper(),
        year=year,
        month=month,
    )
    return ExpiriesResponse(**payload)


@router.get("/admin/stocks", response_model=List[WatchStock])
def list_stocks(container: Container = Depends(container_dep)) -> List[WatchStock]:
    rows = container.watch_stock_repo.list()
    return [WatchStock(**row) for row in rows]

def _clean_index_symbols(values: List[str]) -> List[str]:
    cleaned: List[str] = []
    seen = set()
    for value in values:
        if value is None:
            continue
        symbol = value.strip().upper()
        if not symbol or symbol in seen:
            continue
        cleaned.append(symbol)
        seen.add(symbol)
    return cleaned


def _ensure_default_index(symbols: List[str], default_symbol: str) -> List[str]:
    if default_symbol not in symbols:
        return [default_symbol] + symbols
    return symbols


@router.post("/admin/stocks", response_model=WatchStock)
def create_stock(payload: WatchStockCreate, container: Container = Depends(container_dep)) -> WatchStock:
    symbol = payload.symbol.strip().upper()
    requested_indices = _clean_index_symbols(payload.industry_index_symbols)
    default_index = container.settings.nifty_symbol
    if not requested_indices:
        requested_indices = [default_index]
    else:
        requested_indices = _ensure_default_index(requested_indices, default_index)

    for industry_symbol in requested_indices:
        if not container.watch_index_repo.exists(industry_symbol):
            raise HTTPException(status_code=400, detail=f"Industry index not found: {industry_symbol}")

    stock = container.watch_stock_repo.create(symbol, payload.name, payload.active)
    container.ticker_index_repo.set_mappings(stock.symbol, requested_indices)
    return WatchStock(
        id=stock.id,
        symbol=stock.symbol,
        name=stock.name,
        active=stock.active,
        industry_index_symbols=requested_indices,
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

    default_index = container.settings.nifty_symbol
    requested_indices = None
    if payload.industry_index_symbols is not None:
        requested_indices = _clean_index_symbols(payload.industry_index_symbols)
        if not requested_indices:
            requested_indices = [default_index]
        else:
            requested_indices = _ensure_default_index(requested_indices, default_index)
    symbol = payload.symbol.strip().upper() if payload.symbol else None

    if requested_indices is not None:
        for industry_symbol in requested_indices:
            if not container.watch_index_repo.exists(industry_symbol):
                raise HTTPException(status_code=400, detail=f"Industry index not found: {industry_symbol}")

    old_symbol = existing_fields["symbol"]
    existing_indices = container.ticker_index_repo.get_indices_for_stock(old_symbol)
    container.watch_stock_repo.update(stock_id, symbol, payload.name, payload.active)
    new_symbol = symbol or old_symbol

    if symbol and symbol != old_symbol:
        container.ticker_index_repo.move_stock_symbol(old_symbol, new_symbol)

    if requested_indices is not None:
        container.ticker_index_repo.set_mappings(new_symbol, requested_indices)
    elif symbol and symbol != old_symbol and existing_indices:
        container.ticker_index_repo.set_mappings(
            new_symbol,
            _ensure_default_index(existing_indices, default_index),
        )

    current_indices = container.ticker_index_repo.get_indices_for_stock(new_symbol)
    updated_fields = container.watch_stock_repo.get_fields(stock_id)
    if updated_fields is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    return WatchStock(
        id=stock_id,
        symbol=updated_fields["symbol"],
        name=updated_fields["name"],
        active=updated_fields["active"],
        industry_index_symbols=current_indices,
    )


@router.delete("/admin/stocks/{stock_id}")
def delete_stock(stock_id: int, container: Container = Depends(container_dep)) -> dict:
    try:
        stock = container.watch_stock_repo.get(stock_id)
        if stock is None:
            raise HTTPException(status_code=404, detail="Stock not found")
        container.ticker_index_repo.clear_mappings(stock.symbol)
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
    data_symbol = payload.data_symbol.strip().upper() if payload.data_symbol else symbol
    index = container.watch_index_repo.create(symbol, payload.name, payload.active, data_symbol=data_symbol)
    return WatchIndex(
        id=index.id,
        symbol=index.symbol,
        data_symbol=index.data_symbol,
        name=index.name,
        active=index.active,
    )


@router.patch("/admin/indices/{index_id}", response_model=WatchIndex)
def update_index(
    index_id: int,
    payload: WatchIndexUpdate,
    container: Container = Depends(container_dep),
) -> WatchIndex:
    existing_fields = container.watch_index_repo.get_fields(index_id)
    if existing_fields is None:
        raise HTTPException(status_code=404, detail="Index not found")
    old_symbol = existing_fields["symbol"]
    symbol = payload.symbol.strip().upper() if payload.symbol else None
    data_symbol = payload.data_symbol.strip().upper() if payload.data_symbol else None
    index = container.watch_index_repo.update(index_id, symbol, payload.name, payload.active, data_symbol)
    if symbol and symbol != old_symbol:
        container.ticker_index_repo.move_index_symbol(old_symbol, symbol)
    return WatchIndex(
        id=index.id,
        symbol=index.symbol,
        data_symbol=index.data_symbol,
        name=index.name,
        active=index.active,
    )


@router.delete("/admin/indices/{index_id}")
def delete_index(index_id: int, container: Container = Depends(container_dep)) -> dict:
    try:
        container.watch_index_repo.delete(index_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Index not found")
    return {"status": "ok"}
