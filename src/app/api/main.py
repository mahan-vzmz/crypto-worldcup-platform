import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager

from app.api.dependencies import get_container
from app.api.routers import crypto, dashboard, football
from app.utils.exceptions import ConfigError
from app.utils.logger import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the FastAPI application."""
    container = get_container()
    await container.repository.initialize()
    yield

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    setup_logging()

    app = FastAPI(
        title="Crypto & World Cup API",
        description="REST API for cryptocurrency prices and World Cup data.",
        version="4.0.0",
        lifespan=lifespan,
    )

    # Mount static assets
    app.mount("/static", StaticFiles(directory="src/app/static"), name="static")

    app.include_router(dashboard.router)
    app.include_router(crypto.router)
    app.include_router(football.router)

    @app.exception_handler(ConfigError)
    async def config_error_handler(request: Request, exc: ConfigError) -> JSONResponse:
        logger.error(f"Configuration error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server configuration error."},
        )

    return app


app = create_app()


def run() -> None:
    """Entry point for the API server."""
    uvicorn.run("app.api.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    run()
