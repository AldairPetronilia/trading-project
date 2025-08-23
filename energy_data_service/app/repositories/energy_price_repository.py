"""Repository for energy price data operations with TimescaleDB optimization."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from app.exceptions.repository_exceptions import (
    DataAccessError,
    DuplicateDataError,
)
from app.models.price_data import EnergyPricePoint
from app.repositories.base_repository import BaseRepository
from sqlalchemy import and_, delete, desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

if TYPE_CHECKING:
    from datetime import datetime

    from app.config.database import Database
    from app.models.load_data import EnergyDataType

# Composite primary key length: (timestamp, area_code, data_type, business_type)
COMPOSITE_KEY_LENGTH = 4


class EnergyPriceRepository(BaseRepository[EnergyPricePoint]):
    """Repository for time-series energy price data operations with TimescaleDB optimization.

    Provides specialized methods for:
    - Price-specific queries with currency and auction type filtering
    - Time-range queries optimized for time-series price data
    - Latest price retrieval for trading signals
    - Batch upsert operations with financial precision conflict resolution
    - Composite primary key handling (timestamp, area_code, data_type, business_type)
    """

    def __init__(self, database: Database) -> None:
        """Initialize energy price repository with database dependency.

        Args:
            database: Database instance for session management
        """
        super().__init__(database)

    async def get_by_id(self, item_id: Any) -> EnergyPricePoint | None:
        """Retrieve energy price point by composite primary key.

        Args:
            item_id: Tuple of (timestamp, area_code, data_type, business_type)

        Returns:
            The energy price point if found, None otherwise

        Raises:
            DataAccessError: If the database operation fails
        """
        if not isinstance(item_id, tuple) or len(item_id) != COMPOSITE_KEY_LENGTH:
            msg = "item_id must be a tuple of (timestamp, area_code, data_type, business_type)"
            raise ValueError(msg)

        timestamp, area_code, data_type, business_type = item_id

        async with self.database.session_factory() as session:
            try:
                stmt = select(EnergyPricePoint).where(
                    and_(
                        EnergyPricePoint.timestamp == timestamp,
                        EnergyPricePoint.area_code == area_code,
                        EnergyPricePoint.data_type == data_type,
                        EnergyPricePoint.business_type == business_type,
                    ),
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve energy price point by composite key"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyPricePoint",
                    operation="get_by_id",
                    context={
                        "timestamp": timestamp.isoformat(),
                        "area_code": area_code,
                        "data_type": data_type.value,
                        "business_type": business_type,
                    },
                ) from e

    async def get_all(self) -> list[EnergyPricePoint]:
        """Retrieve all energy price points.

        Returns:
            List of all energy price points ordered by timestamp desc

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(EnergyPricePoint).order_by(
                    desc(EnergyPricePoint.timestamp)
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve all energy price points"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyPricePoint",
                    operation="get_all",
                ) from e

    async def delete(self, item_id: Any) -> bool:
        """Delete energy price point by composite primary key.

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
                stmt = delete(EnergyPricePoint).where(
                    and_(
                        EnergyPricePoint.timestamp == timestamp,
                        EnergyPricePoint.area_code == area_code,
                        EnergyPricePoint.data_type == data_type,
                        EnergyPricePoint.business_type == business_type,
                    ),
                )
                result = await session.execute(stmt)
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                error_msg = "Failed to delete energy price point by composite key"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyPricePoint",
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
    ) -> EnergyPricePoint | None:
        """Convenience method to retrieve energy price point by composite primary key.

        Args:
            timestamp: The timestamp for the price point
            area_code: The area code identifier
            data_type: The energy data type enum value
            business_type: The business type code

        Returns:
            The energy price point if found, None otherwise

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
        """Convenience method to delete energy price point by composite primary key.

        Args:
            timestamp: The timestamp for the price point
            area_code: The area code identifier
            data_type: The energy data type enum value
            business_type: The business type code

        Returns:
            True if the record was deleted, False if not found

        Raises:
            DataAccessError: If the database operation fails
        """
        return await self.delete((timestamp, area_code, data_type, business_type))

    async def get_prices_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        area_codes: list[str] | None = None,
        data_types: list[EnergyDataType] | None = None,
        currency_units: list[str] | None = None,
        auction_types: list[str] | None = None,
        business_types: list[str] | None = None,
    ) -> list[EnergyPricePoint]:
        """Retrieve energy price points within a time range with optional filtering.

        Args:
            start_time: Start of the time range (inclusive)
            end_time: End of the time range (inclusive)
            area_codes: Optional list of area codes to filter by
            data_types: Optional list of data types to filter by
            currency_units: Optional list of currency units to filter by
            auction_types: Optional list of auction types to filter by
            business_types: Optional list of business types to filter by

        Returns:
            List of energy price points matching the criteria, ordered by timestamp

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                conditions = [
                    EnergyPricePoint.timestamp >= start_time,
                    EnergyPricePoint.timestamp <= end_time,
                ]

                if area_codes:
                    conditions.append(EnergyPricePoint.area_code.in_(area_codes))
                if data_types:
                    conditions.append(EnergyPricePoint.data_type.in_(data_types))
                if currency_units:
                    conditions.append(
                        EnergyPricePoint.currency_unit_name.in_(currency_units)
                    )
                if auction_types:
                    conditions.append(EnergyPricePoint.auction_type.in_(auction_types))
                if business_types:
                    conditions.append(
                        EnergyPricePoint.business_type.in_(business_types)
                    )

                stmt = (
                    select(EnergyPricePoint)
                    .where(and_(*conditions))
                    .order_by(EnergyPricePoint.timestamp)
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve energy price points by time range"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyPricePoint",
                    operation="get_prices_by_time_range",
                    context={
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "area_codes_count": len(area_codes) if area_codes else 0,
                        "data_types_count": len(data_types) if data_types else 0,
                        "currency_units_count": len(currency_units)
                        if currency_units
                        else 0,
                        "auction_types_count": len(auction_types)
                        if auction_types
                        else 0,
                        "business_types_count": len(business_types)
                        if business_types
                        else 0,
                    },
                ) from e

    async def get_latest_price_for_area(
        self,
        area_code: str,
        data_type: EnergyDataType,
        business_type: str,
    ) -> EnergyPricePoint | None:
        """Retrieve the most recent energy price point for an area and type combination.

        Args:
            area_code: The area code to filter by
            data_type: The energy data type to filter by
            business_type: The business type to filter by

        Returns:
            The most recent energy price point if found, None otherwise

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(EnergyPricePoint)
                    .where(
                        and_(
                            EnergyPricePoint.area_code == area_code,
                            EnergyPricePoint.data_type == data_type,
                            EnergyPricePoint.business_type == business_type,
                        ),
                    )
                    .order_by(desc(EnergyPricePoint.timestamp))
                    .limit(1)
                )

                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve latest energy price point for area"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyPricePoint",
                    operation="get_latest_price_for_area",
                    context={
                        "area_code": area_code,
                        "data_type": data_type.value,
                        "business_type": business_type,
                    },
                ) from e

    async def get_latest_price_for_area_and_type(
        self,
        area_code: str,
        data_type: EnergyDataType,
    ) -> EnergyPricePoint | None:
        """Retrieve the most recent energy price point for an area and data type combination.

        This method queries only by area_code and data_type, ignoring business_type.
        This is useful for gap detection where we want the latest price regardless
        of the specific business type returned by the ENTSO-E API.

        Args:
            area_code: The area code to filter by
            data_type: The energy data type to filter by

        Returns:
            The most recent energy price point if found, None otherwise

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(EnergyPricePoint)
                    .where(
                        and_(
                            EnergyPricePoint.area_code == area_code,
                            EnergyPricePoint.data_type == data_type,
                        ),
                    )
                    .order_by(desc(EnergyPricePoint.timestamp))
                    .limit(1)
                )

                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                error_msg = (
                    "Failed to retrieve latest energy price point for area and type"
                )
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyPricePoint",
                    operation="get_latest_price_for_area_and_type",
                    context={
                        "area_code": area_code,
                        "data_type": data_type.value,
                    },
                ) from e

    async def get_prices_by_currency(
        self,
        currency_unit: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[EnergyPricePoint]:
        """Retrieve energy price points filtered by currency unit.

        Args:
            currency_unit: The currency unit to filter by (e.g., "EUR", "USD")
            start_time: Optional start of time range filter
            end_time: Optional end of time range filter
            limit: Maximum number of records to return

        Returns:
            List of energy price points with the specified currency, ordered by timestamp desc

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                conditions = [EnergyPricePoint.currency_unit_name == currency_unit]

                if start_time:
                    conditions.append(EnergyPricePoint.timestamp >= start_time)
                if end_time:
                    conditions.append(EnergyPricePoint.timestamp <= end_time)

                stmt = (
                    select(EnergyPricePoint)
                    .where(and_(*conditions))
                    .order_by(desc(EnergyPricePoint.timestamp))
                    .limit(limit)
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve energy price points by currency"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyPricePoint",
                    operation="get_prices_by_currency",
                    context={
                        "currency_unit": currency_unit,
                        "start_time": start_time.isoformat() if start_time else None,
                        "end_time": end_time.isoformat() if end_time else None,
                        "limit": limit,
                    },
                ) from e

    async def get_prices_by_auction_type(
        self,
        auction_type: str,
        area_codes: list[str] | None = None,
        limit: int = 100,
    ) -> list[EnergyPricePoint]:
        """Retrieve energy price points filtered by auction type.

        Args:
            auction_type: The auction type code to filter by (e.g., "A01" for day-ahead)
            area_codes: Optional list of area codes to filter by
            limit: Maximum number of records to return

        Returns:
            List of energy price points with the specified auction type, ordered by timestamp desc

        Raises:
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                conditions = [EnergyPricePoint.auction_type == auction_type]

                if area_codes:
                    conditions.append(EnergyPricePoint.area_code.in_(area_codes))

                stmt = (
                    select(EnergyPricePoint)
                    .where(and_(*conditions))
                    .order_by(desc(EnergyPricePoint.timestamp))
                    .limit(limit)
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve energy price points by auction type"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyPricePoint",
                    operation="get_prices_by_auction_type",
                    context={
                        "auction_type": auction_type,
                        "area_codes_count": len(area_codes) if area_codes else 0,
                        "limit": limit,
                    },
                ) from e

    async def upsert_batch(
        self,
        models: list[EnergyPricePoint],
    ) -> list[EnergyPricePoint]:
        """Upsert multiple energy price points with conflict resolution.

        Uses PostgreSQL's ON CONFLICT DO UPDATE to handle duplicate primary keys
        by updating the existing record with new price data.

        Args:
            models: List of energy price point instances to upsert

        Returns:
            List of upserted energy price point instances

        Raises:
            DataAccessError: If the database operation fails
        """
        if not models:
            return []

        async with self.database.session_factory() as session:
            try:
                stmt = insert(EnergyPricePoint)
                values = []
                for model in models:
                    model_dict = {
                        "timestamp": model.timestamp,
                        "area_code": model.area_code,
                        "data_type": model.data_type,
                        "business_type": model.business_type,
                        "price_amount": model.price_amount,
                        "currency_unit_name": model.currency_unit_name,
                        "price_measure_unit_name": model.price_measure_unit_name,
                        "auction_type": model.auction_type,
                        "contract_market_agreement_type": model.contract_market_agreement_type,
                        "data_source": model.data_source,
                        "document_mrid": model.document_mrid,
                        "revision_number": model.revision_number,
                        "document_created_at": model.document_created_at,
                        "time_series_mrid": model.time_series_mrid,
                        "resolution": model.resolution,
                        "curve_type": model.curve_type,
                        "position": model.position,
                        "period_start": model.period_start,
                        "period_end": model.period_end,
                    }
                    values.append(model_dict)

                update_columns = {
                    "price_amount": stmt.excluded.price_amount,
                    "currency_unit_name": stmt.excluded.currency_unit_name,
                    "price_measure_unit_name": stmt.excluded.price_measure_unit_name,
                    "auction_type": stmt.excluded.auction_type,
                    "contract_market_agreement_type": stmt.excluded.contract_market_agreement_type,
                    "data_source": stmt.excluded.data_source,
                    "document_mrid": stmt.excluded.document_mrid,
                    "revision_number": stmt.excluded.revision_number,
                    "document_created_at": stmt.excluded.document_created_at,
                    "time_series_mrid": stmt.excluded.time_series_mrid,
                    "resolution": stmt.excluded.resolution,
                    "curve_type": stmt.excluded.curve_type,
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
                error_msg = "Failed to upsert batch of energy price points"
                raise DataAccessError(
                    error_msg,
                    model_type="EnergyPricePoint",
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
        return "EnergyPricePoint"
