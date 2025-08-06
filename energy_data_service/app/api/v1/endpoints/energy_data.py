"""Energy data API endpoints."""

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional

from app.api.dependencies import get_energy_data_repository
from app.api.schemas.energy_data import EnergyDataQuery, EnergyDataResponse
from app.exceptions.repository_exceptions import RepositoryError
from app.models.load_data import EnergyDataPoint
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
                point
                for point in data_points
                if (
                    hasattr(point.data_type, "value")
                    and point.data_type.value == data_type
                )
                or (isinstance(point.data_type, str) and point.data_type == data_type)
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


@router.get("/latest", response_model=list[EnergyDataResponse])  # type: ignore[misc]
async def get_latest_energy_data(
    area_code: Annotated[
        str,
        Query(
            ...,
            description="Geographic area code (e.g., 'DE', 'FR', 'NL')",
            min_length=2,
            max_length=10,
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
            le=1000,
            description="Maximum number of recent records to return",
        ),
    ] = 100,
    repository: EnergyDataRepository = Depends(get_energy_data_repository),  # noqa: B008
) -> list[EnergyDataResponse]:
    """Get the most recent energy data points for real-time access.

    Retrieves the latest energy data points for a given area code,
    ordered by timestamp descending (most recent first).

    Args:
        area_code: Geographic area code (e.g., 'DE' for Germany)
        data_type: Optional filter for energy data type
        business_type: Optional filter for business type
        limit: Maximum number of records to return (default: 100, max: 1000)
        repository: Energy data repository instance (injected)

    Returns:
        List of most recent energy data points, ordered by timestamp descending

    Raises:
        HTTPException: 500 for database errors
    """
    # Normalize area code
    area_code = area_code.upper().strip()

    try:
        # Get recent data from repository
        data_points = await repository.get_latest_by_area(
            area_code=area_code,
            limit=limit,
        )

        # Filter by data_type if provided
        if data_type:
            data_points = [
                point
                for point in data_points
                if (
                    hasattr(point.data_type, "value")
                    and point.data_type.value == data_type
                )
                or (isinstance(point.data_type, str) and point.data_type == data_type)
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


@router.get("/aggregated", response_model=list[EnergyDataResponse])  # type: ignore[misc]
async def get_aggregated_energy_data(
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
            description="Start time for aggregation period (ISO 8601 format)",
        ),
    ],
    end_time: Annotated[
        datetime,
        Query(
            ...,
            description="End time for aggregation period (ISO 8601 format)",
        ),
    ],
    aggregation: Annotated[
        str,
        Query(
            ...,
            description="Aggregation method: 'hourly', 'daily', 'weekly'",
            pattern="^(hourly|daily|weekly)$",
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
            le=5000,
            description="Maximum number of aggregated records to return",
        ),
    ] = 1000,
    repository: EnergyDataRepository = Depends(get_energy_data_repository),  # noqa: B008
) -> list[EnergyDataResponse]:
    """Get aggregated energy data for analysis and reporting.

    Retrieves energy data points aggregated by the specified time period
    (hourly, daily, or weekly) within the given time range.

    Args:
        area_code: Geographic area code (e.g., 'DE' for Germany)
        start_time: Start of the aggregation period (inclusive)
        end_time: End of the aggregation period (inclusive)
        aggregation: Time period for aggregation ('hourly', 'daily', 'weekly')
        data_type: Optional filter for energy data type
        business_type: Optional filter for business type
        limit: Maximum number of records to return (default: 1000, max: 5000)
        repository: Energy data repository instance (injected)

    Returns:
        List of aggregated energy data points

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
        # Query data from repository with time range
        data_points = await repository.get_by_time_range(
            area_codes=[area_code],
            start_time=start_time,
            end_time=end_time,
        )

        # Filter by data_type if provided
        if data_type:
            data_points = [
                point
                for point in data_points
                if (
                    hasattr(point.data_type, "value")
                    and point.data_type.value == data_type
                )
                or (isinstance(point.data_type, str) and point.data_type == data_type)
            ]

        # Filter by business_type if provided
        if business_type:
            data_points = [
                point for point in data_points if point.business_type == business_type
            ]

        # Aggregate data based on requested aggregation
        aggregated_points = _aggregate_data_points(data_points, aggregation)

        # Apply limit and convert to response models
        limited_points = aggregated_points[:limit]
        return [EnergyDataResponse.from_model(point) for point in limited_points]

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


def _aggregate_data_points(
    data_points: list[EnergyDataPoint],
    aggregation: str,
) -> list[EnergyDataPoint]:
    """Aggregate energy data points by the specified time period.

    Args:
        data_points: Raw energy data points to aggregate
        aggregation: Aggregation method ('hourly', 'daily', 'weekly')

    Returns:
        List of aggregated energy data points
    """
    if not data_points:
        return []

    # Group data points by aggregation period
    groups: dict[str, list[EnergyDataPoint]] = defaultdict(list)

    for point in data_points:
        # Create aggregation key based on timestamp
        if aggregation == "hourly":
            key = point.timestamp.strftime("%Y-%m-%d-%H")
        elif aggregation == "daily":
            key = point.timestamp.strftime("%Y-%m-%d")
        elif aggregation == "weekly":
            # ISO week format
            year, week, _ = point.timestamp.isocalendar()
            key = f"{year}-W{week:02d}"
        else:
            key = point.timestamp.strftime("%Y-%m-%d")  # Default to daily

        groups[key].append(point)

    # Create aggregated data points
    aggregated = []
    for group_points in groups.values():
        if not group_points:
            continue

        # Use first point as template
        template = group_points[0]

        # Calculate aggregated values
        total_value = sum(Decimal(str(point.quantity)) for point in group_points)
        avg_value = total_value / len(group_points)

        # Create aggregated point with all required fields
        aggregated_point = EnergyDataPoint(
            timestamp=group_points[0].timestamp,  # Use earliest timestamp in group
            area_code=template.area_code,
            data_type=template.data_type,
            business_type=template.business_type,
            quantity=avg_value,
            unit=template.unit,
            data_source=template.data_source,
            document_mrid=f"{template.document_mrid}_agg_{len(group_points)}",
            document_created_at=template.document_created_at,
            time_series_mrid=template.time_series_mrid,
            curve_type=template.curve_type,
            object_aggregation=template.object_aggregation,
            position=template.position,
            period_start=template.period_start,
            period_end=template.period_end,
        )
        # Set additional fields not in constructor
        aggregated_point.resolution = f"AGG_{aggregation.upper()}"
        aggregated_point.revision_number = template.revision_number

        aggregated.append(aggregated_point)

    # Sort by timestamp
    aggregated.sort(key=lambda x: x.timestamp)
    return aggregated
