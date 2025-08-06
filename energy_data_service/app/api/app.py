"""FastAPI application factory for Energy Data Service.

This module provides the application factory function that creates and configures
the FastAPI application with dependency injection integration and proper middleware setup.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.api.v1 import router as v1_router
from app.container import Container
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan manager for startup and shutdown events.

    Args:
        _app: FastAPI application instance (unused in current implementation)

    Yields:
        None: Control to the application during its lifetime
    """
    # Startup - container is initialized during app creation, no additional startup needed
    # Container available at: app.state.container

    yield

    # Shutdown - cleanup if needed
    # Database connections are handled per-request, no global cleanup needed


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance.

    This factory function creates a FastAPI application with:
    - Dependency injection container integration
    - CORS middleware configuration
    - API versioning with modular router structure
    - Proper lifespan management for database connections

    Returns:
        FastAPI: Configured application instance ready for deployment
    """
    app = FastAPI(
        title="Energy Data Service API",
        version="1.0.0",
        description="REST API for energy data collection, processing, and retrieval",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Initialize dependency injection container
    container = Container()
    app.state.container = container

    # Add CORS middleware for cross-service communication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(v1_router, prefix="/api/v1")

    return app
