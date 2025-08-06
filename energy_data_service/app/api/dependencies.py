"""FastAPI dependency injection bridge.

This module provides dependency provider functions that bridge FastAPI's
dependency injection system with our existing dependency-injector container.
"""

from typing import Annotated

from app.container import Container
from app.repositories.backfill_progress_repository import BackfillProgressRepository
from app.repositories.energy_data_repository import EnergyDataRepository
from app.services.backfill_service import BackfillService
from app.services.entsoe_data_service import EntsoEDataService
from fastapi import Depends, Request


def get_container(request: Request) -> Container:
    """Get the dependency injection container from application state.

    Args:
        request: FastAPI request object containing application state

    Returns:
        Container: Main dependency injection container instance
    """
    return request.app.state.container


def get_energy_data_repository(
    container: Annotated[Container, Depends(get_container)],
) -> EnergyDataRepository:
    """Get EnergyDataRepository dependency from container.

    Args:
        container: Dependency injection container

    Returns:
        EnergyDataRepository: Repository for energy data operations
    """
    return container.energy_data_repository()


def get_backfill_progress_repository(
    container: Annotated[Container, Depends(get_container)],
) -> BackfillProgressRepository:
    """Get BackfillProgressRepository dependency from container.

    Args:
        container: Dependency injection container

    Returns:
        BackfillProgressRepository: Repository for backfill progress operations
    """
    return container.backfill_progress_repository()


def get_entsoe_data_service(
    container: Annotated[Container, Depends(get_container)],
) -> EntsoEDataService:
    """Get EntsoEDataService dependency from container.

    Args:
        container: Dependency injection container

    Returns:
        EntsoEDataService: Service for ENTSO-E data operations
    """
    return container.entsoe_data_service()


def get_backfill_service(
    container: Annotated[Container, Depends(get_container)],
) -> BackfillService:
    """Get BackfillService dependency from container.

    Args:
        container: Dependency injection container

    Returns:
        BackfillService: Service for backfill operations
    """
    return container.backfill_service()
