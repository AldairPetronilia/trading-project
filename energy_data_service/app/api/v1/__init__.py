"""API v1 router module.

This module provides the main router for API version 1, including
health check endpoints and placeholder for future data endpoints.
"""

from app.api.v1.endpoints import health
from fastapi import APIRouter

router = APIRouter()

# Register endpoint routers
router.include_router(health.router, prefix="/health", tags=["Health"])
