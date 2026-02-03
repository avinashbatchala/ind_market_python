from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.api.websocket import router as ws_router
from app.core.container import get_container
from app.core.logging import configure_logging, get_logger


def create_app() -> FastAPI:
    app = FastAPI(title="Groww Scanner")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    app.include_router(ws_router)

    @app.on_event("startup")
    async def startup() -> None:
        container = get_container()
        configure_logging(container.settings.log_level)
        logger = get_logger(__name__)
        logger.info("Starting backend")
        app.state.container = container
        await container.start()
        logger.info("Backend started")

    @app.on_event("shutdown")
    async def shutdown() -> None:
        container = get_container()
        logger = get_logger(__name__)
        logger.info("Shutting down backend")
        await container.stop()
        logger.info("Backend shutdown complete")

    return app


app = create_app()
