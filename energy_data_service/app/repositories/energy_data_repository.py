from datetime import datetime
from typing import Any, Optional

from app.config.database import Database
from app.exceptions.repository_exceptions import DataAccessError
from app.models.load_data import EnergyDataPoint, EnergyDataType
from app.repositories.base_repository import BaseRepository
from sqlalchemy import and_, delete, desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

COMPOSITE_KEY_LENGTH = 4


class EnergyDataRepository(BaseRepository[EnergyDataPoint]):
    """Repository for time-series energy data operations with TimescaleDB optimization.

    Provides specialized methods for:
    - Time-range queries optimized for time-series data
    - Area and data type filtering
    - Batch upsert operations with conflict resolution
    - Latest data retrieval for trading signals
    - Composite primary key handling (timestamp, area_code, data_type, business_type)
    """

    def __init__(self, database: Database) -> None:
        """Initialize energy data repository with database dependency.

        Args:
            database: Database instance for session management
        """
        super().__init__(database)

    async def get_by_id(self, item_id: Any) -> EnergyDataPoint | None:
        """Retrieve energy data point by composite primary key.

        Args:
            item_id: Tuple of (timestamp, area_code, data_type, business_type)

        Returns:
            The energy data point if found, None otherwise

        Raises:
            DataAccessError: If the database operation fails
        """
        if not isinstance(item_id, tuple) or len(item_id) != COMPOSITE_KEY_LENGTH:
            msg = "item_id must be a tuple of (timestamp, area_code, data_type, business_type)"
            raise ValueError(msg)

        timestamp, area_code, data_type, business_type = item_id

        async with self.database.session_factory() as session:
            try:
                stmt = select(EnergyDataPoint).where(
                    and_(
                        EnergyDataPoint.timestamp == timestamp,
                        EnergyDataPoint.area_code == area_code,
                        EnergyDataPoint.data_type == data_type,
                        EnergyDataPoint.business_type == business_type,
                    ),
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve energy data point by composite key"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyDataPoint",
                    operation="get_by_id",
                    context={
                        "timestamp": timestamp.isoformat(),
                        "area_code": area_code,
                        "data_type": data_type.value,
                        "business_type": business_type,
                    },
                ) from e

    async def get_all(self) -> list[EnergyDataPoint]:
        """Retrieve all energy data points.

        Returns:
            List of all energy data points ordered by timestamp desc

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(EnergyDataPoint).order_by(desc(EnergyDataPoint.timestamp))
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve all energy data points"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyDataPoint",
                    operation="get_all",
                ) from e

    async def delete(self, item_id: Any) -> bool:
        """Delete energy data point by composite primary key.

        Args:
            item_id: Tuple of (timestamp, area_code, data_type, business_type)

        Returns:
            True if the record was deleted, False if not found

        Raises:
            DataAccessError: If the database operation fails
        """
        if not isinstance(item_id, tuple) or len(item_id) != COMPOSITE_KEY_LENGTH:
            msg = "item_id must be a tuple of (timestamp, area_code, data_type, business_type)"
            raise ValueError(msg)

        timestamp, area_code, data_type, business_type = item_id

        async with self.database.session_factory() as session:
            try:
                stmt = delete(EnergyDataPoint).where(
                    and_(
                        EnergyDataPoint.timestamp == timestamp,
                        EnergyDataPoint.area_code == area_code,
                        EnergyDataPoint.data_type == data_type,
                        EnergyDataPoint.business_type == business_type,
                    ),
                )
                result = await session.execute(stmt)
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                error_msg = "Failed to delete energy data point by composite key"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyDataPoint",
                    operation="delete",
                    context={
                        "timestamp": timestamp.isoformat(),
                        "area_code": area_code,
                        "data_type": data_type.value,
                        "business_type": business_type,
                    },
                ) from e
            else:
                return result.rowcount > 0

    async def get_by_composite_key(
        self,
        timestamp: datetime,
        area_code: str,
        data_type: EnergyDataType,
        business_type: str,
    ) -> EnergyDataPoint | None:
        """Convenience method to retrieve energy data point by composite primary key.

        Args:
            timestamp: The timestamp for the data point
            area_code: The area code identifier
            data_type: The energy data type enum value
            business_type: The business type code

        Returns:
            The energy data point if found, None otherwise

        Raises:
            DataAccessError: If the database operation fails
        """
        return await self.get_by_id((timestamp, area_code, data_type, business_type))

    async def delete_by_composite_key(
        self,
        timestamp: datetime,
        area_code: str,
        data_type: EnergyDataType,
        business_type: str,
    ) -> bool:
        """Convenience method to delete energy data point by composite primary key.

        Args:
            timestamp: The timestamp for the data point
            area_code: The area code identifier
            data_type: The energy data type enum value
            business_type: The business type code

        Returns:
            True if the record was deleted, False if not found

        Raises:
            DataAccessError: If the database operation fails
        """
        return await self.delete((timestamp, area_code, data_type, business_type))

    async def get_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        area_codes: list[str] | None = None,
        data_types: list[EnergyDataType] | None = None,
        business_types: list[str] | None = None,
    ) -> list[EnergyDataPoint]:
        """Retrieve energy data points within a time range with optional filtering.

        Args:
            start_time: Start of the time range (inclusive)
            end_time: End of the time range (inclusive)
            area_codes: Optional list of area codes to filter by
            data_types: Optional list of data types to filter by
            business_types: Optional list of business types to filter by

        Returns:
            List of energy data points matching the criteria, ordered by timestamp

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                conditions = [
                    EnergyDataPoint.timestamp >= start_time,
                    EnergyDataPoint.timestamp <= end_time,
                ]

                if area_codes:
                    conditions.append(EnergyDataPoint.area_code.in_(area_codes))
                if data_types:
                    conditions.append(EnergyDataPoint.data_type.in_(data_types))
                if business_types:
                    conditions.append(EnergyDataPoint.business_type.in_(business_types))

                stmt = (
                    select(EnergyDataPoint)
                    .where(and_(*conditions))
                    .order_by(EnergyDataPoint.timestamp)
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve energy data points by time range"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyDataPoint",
                    operation="get_by_time_range",
                    context={
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "area_codes_count": len(area_codes) if area_codes else 0,
                        "data_types_count": len(data_types) if data_types else 0,
                        "business_types_count": (
                            len(business_types) if business_types else 0
                        ),
                    },
                ) from e

    async def get_by_area(
        self,
        area_code: str,
        data_type: EnergyDataType | None = None,
        limit: int | None = None,
    ) -> list[EnergyDataPoint]:
        """Retrieve energy data points for a specific area.

        Args:
            area_code: The area code to filter by
            data_type: Optional data type to filter by
            limit: Optional limit on the number of results

        Returns:
            List of energy data points for the area, ordered by timestamp desc

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                conditions = [EnergyDataPoint.area_code == area_code]

                if data_type:
                    conditions.append(EnergyDataPoint.data_type == data_type)

                stmt = (
                    select(EnergyDataPoint)
                    .where(and_(*conditions))
                    .order_by(desc(EnergyDataPoint.timestamp))
                )

                if limit:
                    stmt = stmt.limit(limit)

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve energy data points by area"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyDataPoint",
                    operation="get_by_area",
                    context={
                        "area_code": area_code,
                        "data_type": data_type.value if data_type else None,
                        "limit": limit,
                    },
                ) from e

    async def get_latest_for_area(
        self,
        area_code: str,
        data_type: EnergyDataType,
        business_type: str,
    ) -> EnergyDataPoint | None:
        """Retrieve the most recent energy data point for an area and type combination.

        Args:
            area_code: The area code to filter by
            data_type: The energy data type to filter by
            business_type: The business type to filter by

        Returns:
            The most recent energy data point if found, None otherwise

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(EnergyDataPoint)
                    .where(
                        and_(
                            EnergyDataPoint.area_code == area_code,
                            EnergyDataPoint.data_type == data_type,
                            EnergyDataPoint.business_type == business_type,
                        ),
                    )
                    .order_by(desc(EnergyDataPoint.timestamp))
                    .limit(1)
                )

                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve latest energy data point for area"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyDataPoint",
                    operation="get_latest_for_area",
                    context={
                        "area_code": area_code,
                        "data_type": data_type.value,
                        "business_type": business_type,
                    },
                ) from e

    async def get_latest_for_area_and_type(
        self,
        area_code: str,
        data_type: EnergyDataType,
    ) -> EnergyDataPoint | None:
        """Retrieve the most recent energy data point for an area and data type combination.

        This method queries only by area_code and data_type, ignoring business_type.
        This is useful for gap detection where we want the latest data regardless
        of the specific business type returned by the ENTSO-E API.

        Args:
            area_code: The area code to filter by
            data_type: The energy data type to filter by

        Returns:
            The most recent energy data point if found, None otherwise

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(EnergyDataPoint)
                    .where(
                        and_(
                            EnergyDataPoint.area_code == area_code,
                            EnergyDataPoint.data_type == data_type,
                        ),
                    )
                    .order_by(desc(EnergyDataPoint.timestamp))
                    .limit(1)
                )

                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                error_msg = (
                    "Failed to retrieve latest energy data point for area and type"
                )
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyDataPoint",
                    operation="get_latest_for_area_and_type",
                    context={
                        "area_code": area_code,
                        "data_type": data_type.value,
                    },
                ) from e

    async def get_latest_by_area(
        self,
        area_code: str,
        limit: int = 100,
    ) -> list[EnergyDataPoint]:
        """Retrieve the most recent energy data points for an area.

        Args:
            area_code: The area code to filter by
            limit: Maximum number of records to return

        Returns:
            List of most recent energy data points, ordered by timestamp descending

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(EnergyDataPoint)
                    .where(EnergyDataPoint.area_code == area_code)
                    .order_by(desc(EnergyDataPoint.timestamp))
                    .limit(limit)
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve latest energy data points for area"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyDataPoint",
                    operation="get_latest_by_area",
                    context={
                        "area_code": area_code,
                        "limit": limit,
                    },
                ) from e

    async def upsert_batch(
        self,
        models: list[EnergyDataPoint],
    ) -> list[EnergyDataPoint]:
        """Upsert multiple energy data points with conflict resolution.

        Uses PostgreSQL's ON CONFLICT DO UPDATE to handle duplicate primary keys
        by updating the existing record with new data.

        Args:
            models: List of energy data point instances to upsert

        Returns:
            List of upserted energy data point instances

        Raises:
            DataAccessError: If the database operation fails
        """
        if not models:
            return []

        async with self.database.session_factory() as session:
            try:
                stmt = insert(EnergyDataPoint)
                values = []
                for model in models:
                    model_dict = {
                        "timestamp": model.timestamp,
                        "area_code": model.area_code,
                        "data_type": model.data_type,
                        "business_type": model.business_type,
                        "quantity": model.quantity,
                        "unit": model.unit,
                        "data_source": model.data_source,
                        "document_mrid": model.document_mrid,
                        "revision_number": model.revision_number,
                        "document_created_at": model.document_created_at,
                        "time_series_mrid": model.time_series_mrid,
                        "resolution": model.resolution,
                        "curve_type": model.curve_type,
                        "object_aggregation": model.object_aggregation,
                        "position": model.position,
                        "period_start": model.period_start,
                        "period_end": model.period_end,
                    }
                    values.append(model_dict)
                update_columns = {
                    "quantity": stmt.excluded.quantity,
                    "unit": stmt.excluded.unit,
                    "data_source": stmt.excluded.data_source,
                    "document_mrid": stmt.excluded.document_mrid,
                    "revision_number": stmt.excluded.revision_number,
                    "document_created_at": stmt.excluded.document_created_at,
                    "time_series_mrid": stmt.excluded.time_series_mrid,
                    "resolution": stmt.excluded.resolution,
                    "curve_type": stmt.excluded.curve_type,
                    "object_aggregation": stmt.excluded.object_aggregation,
                    "position": stmt.excluded.position,
                    "period_start": stmt.excluded.period_start,
                    "period_end": stmt.excluded.period_end,
                    "updated_at": stmt.excluded.updated_at,
                }

                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=[
                        "timestamp",
                        "area_code",
                        "data_type",
                        "business_type",
                    ],
                    set_=update_columns,
                )

                await session.execute(upsert_stmt, values)
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                error_msg = "Failed to upsert batch of energy data points"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyDataPoint",
                    operation="upsert_batch",
                    context={"batch_size": len(models)},
                ) from e
            else:
                return models

    def _get_model_name(self) -> str:
        """Get the model type name for error reporting.

        Returns:
            String representation of the model type
        """
        return "EnergyDataPoint"
