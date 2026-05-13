"""FastAPI application factory and server runner."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health, index, search
from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Talaash",
        description="Local, privacy-first AI-powered file search",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(index.router)
    app.include_router(search.router)

    return app


def start_server() -> None:
    """Start the uvicorn server on the configured port."""
    import uvicorn

    port = settings.TALAASH_API_PORT
    logger.info("Starting Talaash API server on port %d", port)
    print(f"[Talaash] API server running at http://localhost:{port}")
    uvicorn.run(
        "src.api.server:create_app",
        host="0.0.0.0",
        port=port,
        reload=False,
        factory=True,
    )


# Module-level app instance so uvicorn can import it directly
app = create_app()
