"""Health check endpoints for service monitoring and status validation."""

from typing import Annotated

from app.api.dependencies import get_container, get_energy_data_repository
from app.container import Container
from app.exceptions.repository_exceptions import DataAccessError
from app.repositories.energy_data_repository import EnergyDataRepository
from dependency_injector.errors import Error as DIError
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model.

    Attributes:
        status: Service health status
        message: Human-readable status message
    """

    status: str
    message: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model.

    Attributes:
        status: Overall service health status
        message: Human-readable status message
        database: Database connection status
        components: Individual component status details
    """

    status: str
    message: str
    database: str
    components: dict[str, str]


router = APIRouter()


@router.get("/", response_model=HealthResponse)  # type: ignore[misc]
async def health_check() -> HealthResponse:
    """Basic health check endpoint.

    Returns a simple health status without dependency checks.
    Used for basic service availability monitoring.

    Returns:
        HealthResponse: Basic health status information
    """
    return HealthResponse(
        status="healthy", message="Energy Data Service API is operational"
    )


@router.get("/detailed", response_model=DetailedHealthResponse)  # type: ignore[misc]
async def detailed_health_check(
    container: Annotated[Container, Depends(get_container)],
    energy_repo: Annotated[EnergyDataRepository, Depends(get_energy_data_repository)],
) -> DetailedHealthResponse:
    """Detailed health check with dependency validation.

    Validates database connectivity and core service components.
    Used for comprehensive service health monitoring.

    Args:
        container: Dependency injection container
        energy_repo: Energy data repository for database connectivity test

    Returns:
        DetailedHealthResponse: Detailed health status information

    Raises:
        HTTPException: If critical dependencies are unavailable
    """
    components = {}
    database_status = "healthy"

    try:
        # Test database connectivity
        await energy_repo.test_connection()
        components["energy_data_repository"] = "healthy"
        components["database"] = "connected"
    except DataAccessError as e:
        database_status = "unhealthy"
        components["energy_data_repository"] = f"error: {e!s}"
        components["database"] = "disconnected"

    # Test container initialization
    try:
        container.config()
        components["dependency_container"] = "healthy"
    except DIError as e:
        components["dependency_container"] = f"error: {e!s}"

    # Determine overall status
    overall_status = "healthy" if database_status == "healthy" else "unhealthy"

    if overall_status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is unhealthy - critical dependencies unavailable",
        )

    return DetailedHealthResponse(
        status=overall_status,
        message="Energy Data Service API components are operational",
        database=database_status,
        components=components,
    )
