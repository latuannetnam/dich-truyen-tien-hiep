"""FastAPI application factory."""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dich_truyen import __version__
from dich_truyen.api import websocket
from dich_truyen.api.routes import books, glossary, pipeline, settings, styles
from dich_truyen.services.style_service import StyleService
from dich_truyen.services.config_service import ConfigService
from dich_truyen.services.events import EventBus
from dich_truyen.services.pipeline_service import PipelineService


def create_app(
    books_dir: Optional[Path] = None,
    env_file: Optional[Path] = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Dịch Truyện API",
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configure books directory
    if books_dir:
        books.set_books_dir(books_dir)

    app.include_router(books.router)

    # Pipeline services
    event_bus = EventBus()
    pipeline_service = PipelineService(event_bus)
    pipeline.set_services(event_bus, pipeline_service)
    app.include_router(pipeline.router)

    # Settings service
    config_service = ConfigService(env_file=env_file)
    settings.set_config_service(config_service)
    app.include_router(settings.router)

    # Glossary routes
    glossary.set_books_dir(books_dir or Path("books"))
    app.include_router(glossary.router)

    # Style routes
    style_service = StyleService()
    styles.set_style_service(style_service)
    app.include_router(styles.router)

    # Store on app.state for WebSocket access
    app.state.event_bus = event_bus
    app.state.pipeline_service = pipeline_service

    # WebSocket
    app.include_router(websocket.router)

    @app.get("/api/v1/health")
    async def health() -> dict:
        return {"status": "ok", "version": __version__}

    return app

