"""Energy data API endpoints."""

from datetime import datetime
from typing import Annotated, Optional

from app.api.dependencies import get_energy_data_repository
from app.api.schemas.energy_data import EnergyDataQuery, EnergyDataResponse
from app.exceptions.repository_exceptions import RepositoryError
from app.repositories.energy_data_repository import EnergyDataRepository
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(prefix="/energy-data", tags=["Energy Data"])


@router.get("/", response_model=list[EnergyDataResponse])  # type: ignore[misc]
async def get_energy_data(
    area_code: Annotated[
        str,
        Query(
            ...,
            description="Geographic area code (e.g., 'DE', 'FR', 'NL')",
            min_length=2,
            max_length=10,
        ),
    ],
    start_time: Annotated[
        datetime,
        Query(
            ...,
            description="Start time for data query (ISO 8601 format)",
        ),
    ],
    end_time: Annotated[
        datetime,
        Query(
            ...,
            description="End time for data query (ISO 8601 format)",
        ),
    ],
    data_type: Annotated[
        str | None,
        Query(
            description="Filter by energy data type",
            max_length=50,
        ),
    ] = None,
    business_type: Annotated[
        str | None,
        Query(
            description="Filter by business type",
            max_length=50,
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=10000,
            description="Maximum number of records to return",
        ),
    ] = 1000,
    repository: EnergyDataRepository = Depends(get_energy_data_repository),  # noqa: B008
) -> list[EnergyDataResponse]:
    """Query energy data with flexible filtering options.

    Retrieves energy data points based on area code and time range,
    with optional filtering by data type and business type.

    Args:
        area_code: Geographic area code (e.g., 'DE' for Germany)
        start_time: Start of the time range (inclusive)
        end_time: End of the time range (inclusive)
        data_type: Optional filter for energy data type
        business_type: Optional filter for business type
        limit: Maximum number of records to return (default: 1000, max: 10000)
        repository: Energy data repository instance (injected)

    Returns:
        List of energy data points matching the query criteria

    Raises:
        HTTPException: 400 for invalid query parameters
        HTTPException: 500 for database errors
    """
    # Validate time range
    if end_time <= start_time:
        raise HTTPException(
            status_code=400,
            detail="end_time must be after start_time",
        )

    # Normalize area code
    area_code = area_code.upper().strip()

    try:
        # Query data from repository
        data_points = await repository.get_by_time_range(
            area_codes=[area_code],
            start_time=start_time,
            end_time=end_time,
        )

        # Filter by data_type if provided
        if data_type:
            data_points = [
                point for point in data_points if point.data_type == data_type
            ]

        # Filter by business_type if provided
        if business_type:
            data_points = [
                point for point in data_points if point.business_type == business_type
            ]

        # Convert to response models
        return [EnergyDataResponse.from_model(point) for point in data_points[:limit]]

    except RepositoryError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {e!s}",
        ) from e
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=500,
            detail="Internal database error occurred",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred",
        ) from e
