"""
Collection metrics repository implementation with specialized monitoring queries.

This repository provides comprehensive data access operations for CollectionMetrics
with specialized methods for monitoring data collection performance, success rates,
and operational health across different energy areas and data types.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from app.config.database import Database
from app.exceptions.repository_exceptions import DataAccessError
from app.models.collection_metrics import CollectionMetrics
from app.models.load_data import EnergyDataType
from app.repositories.base_repository import BaseRepository
from sqlalchemy import and_, desc, func, select
from sqlalchemy.exc import SQLAlchemyError


class CollectionMetricsRepository(BaseRepository[CollectionMetrics]):
    """
    Repository for collection metrics with specialized monitoring and analytics queries.

    Provides comprehensive data access operations for tracking collection performance,
    success rates, and operational health across different energy areas and data types.
    Supports time-based queries, performance analytics, and maintenance operations
    for effective monitoring of the data collection pipeline.

    Key capabilities:
    - Time-range filtering with area and data type specificity
    - Success rate calculations for operational monitoring
    - Performance metrics aggregation (response times, processing times)
    - Job correlation for scheduler integration
    - Maintenance operations for data retention management
    - Recent metrics retrieval for real-time monitoring
    """

    def __init__(self, database: Database) -> None:
        """Initialize collection metrics repository with database dependency.

        Args:
            database: Database instance for session management
        """
        super().__init__(database)

    async def get_by_id(self, item_id: Any) -> CollectionMetrics | None:
        """Retrieve a collection metrics record by ID.

        Args:
            item_id: The collection metrics ID

        Returns:
            CollectionMetrics instance if found, None otherwise

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(CollectionMetrics).where(CollectionMetrics.id == item_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                error_msg = f"Failed to retrieve CollectionMetrics with ID {item_id}"
                raise DataAccessError(
                    error_msg,
                    model_type="CollectionMetrics",
                    operation="get_by_id",
                    context={"id": item_id},
                ) from e

    async def get_all(self) -> list[CollectionMetrics]:
        """Retrieve all collection metrics records.

        Returns:
            List of all CollectionMetrics instances ordered by collection_start desc

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(CollectionMetrics).order_by(
                    desc(CollectionMetrics.collection_start)
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve all CollectionMetrics records"
                raise DataAccessError(
                    error_msg,
                    model_type="CollectionMetrics",
                    operation="get_all",
                ) from e

    async def delete(self, item_id: Any) -> bool:
        """Delete a collection metrics record by ID.

        Args:
            item_id: The collection metrics ID

        Returns:
            True if record was deleted, False if not found

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(CollectionMetrics).where(CollectionMetrics.id == item_id)
                result = await session.execute(stmt)
                metrics = result.scalar_one_or_none()

                if metrics is None:
                    return False

                await session.delete(metrics)
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                error_msg = f"Failed to delete CollectionMetrics with ID {item_id}"
                raise DataAccessError(
                    error_msg,
                    model_type="CollectionMetrics",
                    operation="delete",
                    context={"id": item_id},
                ) from e
            else:
                return True

    async def get_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        area_codes: list[str] | None = None,
        data_types: list[EnergyDataType] | None = None,
    ) -> list[CollectionMetrics]:
        """Retrieve collection metrics within a time range with optional filtering.

        Args:
            start_time: Start of the time range (inclusive)
            end_time: End of the time range (inclusive)
            area_codes: Optional list of area codes to filter by
            data_types: Optional list of data types to filter by

        Returns:
            List of collection metrics matching the criteria, ordered by collection_start

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                conditions = [
                    CollectionMetrics.collection_start >= start_time,
                    CollectionMetrics.collection_start <= end_time,
                ]

                if area_codes:
                    conditions.append(CollectionMetrics.area_code.in_(area_codes))
                if data_types:
                    conditions.append(CollectionMetrics.data_type.in_(data_types))

                stmt = (
                    select(CollectionMetrics)
                    .where(and_(*conditions))
                    .order_by(CollectionMetrics.collection_start)
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve collection metrics by time range"
                raise DataAccessError(
                    error_msg,
                    model_type="CollectionMetrics",
                    operation="get_by_time_range",
                    context={
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "area_codes_count": len(area_codes) if area_codes else 0,
                        "data_types_count": len(data_types) if data_types else 0,
                    },
                ) from e

    async def get_recent_metrics(self, minutes: int) -> list[CollectionMetrics]:
        """Retrieve collection metrics from the last N minutes.

        Args:
            minutes: Number of minutes back to retrieve metrics from

        Returns:
            List of recent collection metrics ordered by collection_start desc

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                cutoff_time = datetime.now(UTC) - timedelta(minutes=minutes)

                stmt = (
                    select(CollectionMetrics)
                    .where(CollectionMetrics.collection_start >= cutoff_time)
                    .order_by(desc(CollectionMetrics.collection_start))
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = (
                    f"Failed to retrieve collection metrics from last {minutes} minutes"
                )
                raise DataAccessError(
                    error_msg,
                    model_type="CollectionMetrics",
                    operation="get_recent_metrics",
                    context={"minutes": minutes},
                ) from e

    async def calculate_success_rate(
        self,
        start_time: datetime,
        end_time: datetime,
        area_code: str | None = None,
        data_type: EnergyDataType | None = None,
    ) -> float:
        """Calculate success rate for collection operations within a time range.

        Args:
            start_time: Start of the time range (inclusive)
            end_time: End of the time range (inclusive)
            area_code: Optional area code to filter by
            data_type: Optional data type to filter by

        Returns:
            Success rate as a float between 0.0 and 1.0

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                conditions = [
                    CollectionMetrics.collection_start >= start_time,
                    CollectionMetrics.collection_start <= end_time,
                ]

                if area_code:
                    conditions.append(CollectionMetrics.area_code == area_code)
                if data_type:
                    conditions.append(CollectionMetrics.data_type == data_type)

                # Count total operations
                total_stmt = select(func.count(CollectionMetrics.id)).where(
                    and_(*conditions)
                )
                total_result = await session.execute(total_stmt)
                total_count = total_result.scalar() or 0

                if total_count == 0:
                    return 0.0

                # Count successful operations
                success_conditions = [*conditions, CollectionMetrics.success]
                success_stmt = select(func.count(CollectionMetrics.id)).where(
                    and_(*success_conditions)
                )
                success_result = await session.execute(success_stmt)
                success_count = success_result.scalar() or 0

                return success_count / total_count
            except SQLAlchemyError as e:
                error_msg = "Failed to calculate success rate for collection metrics"
                raise DataAccessError(
                    error_msg,
                    model_type="CollectionMetrics",
                    operation="calculate_success_rate",
                    context={
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "area_code": area_code,
                        "data_type": data_type.value if data_type else None,
                    },
                ) from e

    async def get_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, float | None]:
        """Get aggregated performance metrics for a time range.

        Calculates average, minimum, and maximum response and processing times
        for collection operations within the specified time range.

        Args:
            start_time: Start of the time range (inclusive)
            end_time: End of the time range (inclusive)

        Returns:
            Dictionary containing performance metrics with keys:
            - avg_api_response_time: Average API response time in milliseconds
            - min_api_response_time: Minimum API response time in milliseconds
            - max_api_response_time: Maximum API response time in milliseconds
            - avg_processing_time: Average processing time in milliseconds
            - min_processing_time: Minimum processing time in milliseconds
            - max_processing_time: Maximum processing time in milliseconds

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                conditions = [
                    CollectionMetrics.collection_start >= start_time,
                    CollectionMetrics.collection_start <= end_time,
                ]

                stmt = select(
                    func.avg(CollectionMetrics.api_response_time).label(
                        "avg_api_response_time"
                    ),
                    func.min(CollectionMetrics.api_response_time).label(
                        "min_api_response_time"
                    ),
                    func.max(CollectionMetrics.api_response_time).label(
                        "max_api_response_time"
                    ),
                    func.avg(CollectionMetrics.processing_time).label(
                        "avg_processing_time"
                    ),
                    func.min(CollectionMetrics.processing_time).label(
                        "min_processing_time"
                    ),
                    func.max(CollectionMetrics.processing_time).label(
                        "max_processing_time"
                    ),
                ).where(and_(*conditions))

                result = await session.execute(stmt)
                row = result.first()

                if row is None:
                    return {
                        "avg_api_response_time": None,
                        "min_api_response_time": None,
                        "max_api_response_time": None,
                        "avg_processing_time": None,
                        "min_processing_time": None,
                        "max_processing_time": None,
                    }
                return {  # noqa: TRY300
                    "avg_api_response_time": row.avg_api_response_time,
                    "min_api_response_time": row.min_api_response_time,
                    "max_api_response_time": row.max_api_response_time,
                    "avg_processing_time": row.avg_processing_time,
                    "min_processing_time": row.min_processing_time,
                    "max_processing_time": row.max_processing_time,
                }
            except SQLAlchemyError as e:
                error_msg = (
                    "Failed to get performance metrics for collection operations"
                )
                raise DataAccessError(
                    error_msg,
                    model_type="CollectionMetrics",
                    operation="get_performance_metrics",
                    context={
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                    },
                ) from e

    async def get_metrics_by_job_id(self, job_id: str) -> list[CollectionMetrics]:
        """Retrieve all collection metrics for a specific job ID.

        Args:
            job_id: The scheduler job identifier

        Returns:
            List of collection metrics for the job, ordered by collection_start desc

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(CollectionMetrics)
                    .where(CollectionMetrics.job_id == job_id)
                    .order_by(desc(CollectionMetrics.collection_start))
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = f"Failed to retrieve collection metrics for job ID {job_id}"
                raise DataAccessError(
                    error_msg,
                    model_type="CollectionMetrics",
                    operation="get_metrics_by_job_id",
                    context={"job_id": job_id},
                ) from e

    async def cleanup_old_metrics(self, retention_days: int) -> int:
        """Remove collection metrics older than the specified retention period.

        Args:
            retention_days: Number of days to retain metrics (older records are deleted)

        Returns:
            Number of deleted records

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

                # Get count of records to be deleted for logging
                count_stmt = select(func.count(CollectionMetrics.id)).where(
                    CollectionMetrics.collection_start < cutoff_date
                )
                count_result = await session.execute(count_stmt)
                delete_count = count_result.scalar() or 0

                if delete_count == 0:
                    return 0

                # Delete old records
                delete_stmt = select(CollectionMetrics).where(
                    CollectionMetrics.collection_start < cutoff_date
                )
                result = await session.execute(delete_stmt)
                old_metrics = result.scalars().all()

                for metrics in old_metrics:
                    await session.delete(metrics)

                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                error_msg = f"Failed to cleanup collection metrics older than {retention_days} days"
                raise DataAccessError(
                    error_msg,
                    model_type="CollectionMetrics",
                    operation="cleanup_old_metrics",
                    context={
                        "retention_days": retention_days,
                        "cutoff_date": cutoff_date.isoformat(),
                    },
                ) from e
            else:
                return delete_count

    def _get_model_name(self) -> str:
        """Get the model type name for error reporting.

        Returns:
            String representation of the model type
        """
        return "CollectionMetrics"
