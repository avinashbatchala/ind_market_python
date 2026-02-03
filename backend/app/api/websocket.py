from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.container import get_container

router = APIRouter()


@router.websocket("/ws/scanner")
async def ws_scanner(websocket: WebSocket, timeframe: str = Query("5m")) -> None:
    await websocket.accept()
    container = get_container()
    broadcaster = container.broadcaster
    await broadcaster.register(timeframe, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await broadcaster.unregister(timeframe, websocket)
    except Exception:
        await broadcaster.unregister(timeframe, websocket)
        raise
