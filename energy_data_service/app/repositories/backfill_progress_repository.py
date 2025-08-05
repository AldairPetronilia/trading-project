"""
BackfillProgress repository implementation with specialized queries for backfill operations.

This repository resolves technical debt by replacing direct database operations
in the BackfillService with proper repository pattern implementation, eliminating
the need for session.merge() workarounds and cross-session object issues.
"""

from datetime import datetime
from typing import Any

from app.config.database import Database
from app.exceptions.repository_exceptions import DataAccessError
from app.models.backfill_progress import BackfillProgress, BackfillStatus
from app.repositories.base_repository import BaseRepository
from sqlalchemy import and_, desc, select
from sqlalchemy.exc import SQLAlchemyError


class BackfillProgressRepository(BaseRepository[BackfillProgress]):
    """
    Repository for BackfillProgress with specialized queries for backfill operations.

    This repository eliminates the session.merge() technical debt by providing
    proper session management and fresh object queries, resolving cross-session
    object attachment issues present in the service layer.

    Key improvements over service-level database operations:
    - No session.merge() workarounds needed
    - Fresh object queries in current session context
    - Specialized methods for common backfill queries
    - Proper error handling with repository exceptions
    - Type-safe operations with BackfillProgress model
    """

    def __init__(self, database: Database) -> None:
        """Initialize repository with database dependency.

        Args:
            database: Database instance for session management
        """
        super().__init__(database)

    async def get_by_id(self, item_id: Any) -> BackfillProgress | None:
        """Retrieve a backfill progress record by ID.

        Args:
            item_id: The backfill progress ID

        Returns:
            BackfillProgress instance if found, None otherwise

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(BackfillProgress).where(BackfillProgress.id == item_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                msg = f"Failed to retrieve BackfillProgress with ID {item_id}"
                raise DataAccessError(
                    msg,
                    model_type="BackfillProgress",
                    operation="get_by_id",
                    context={"id": item_id},
                ) from e

    async def get_all(self) -> list[BackfillProgress]:
        """Retrieve all backfill progress records.

        Returns:
            List of all BackfillProgress instances

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(BackfillProgress).order_by(
                    desc(BackfillProgress.created_at)
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                msg = "Failed to retrieve all BackfillProgress records"
                raise DataAccessError(
                    msg, model_type="BackfillProgress", operation="get_all"
                ) from e

    async def delete(self, item_id: Any) -> bool:
        """Delete a backfill progress record by ID.

        Args:
            item_id: The backfill progress ID

        Returns:
            True if record was deleted, False if not found

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                # First check if record exists
                stmt = select(BackfillProgress).where(BackfillProgress.id == item_id)
                result = await session.execute(stmt)
                progress = result.scalar_one_or_none()

                if progress is None:
                    return False

                await session.delete(progress)
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                msg = f"Failed to delete BackfillProgress with ID {item_id}"
                raise DataAccessError(
                    msg,
                    model_type="BackfillProgress",
                    operation="delete",
                    context={"id": item_id},
                ) from e
            else:
                return True

    async def get_active_backfills(self) -> list[BackfillProgress]:
        """Get all pending or in-progress backfill operations.

        Returns:
            List of active BackfillProgress instances

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(BackfillProgress)
                    .where(
                        BackfillProgress.status.in_(
                            [BackfillStatus.PENDING, BackfillStatus.IN_PROGRESS]
                        )
                    )
                    .order_by(desc(BackfillProgress.created_at))
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                msg = "Failed to retrieve active backfill operations"
                raise DataAccessError(
                    msg, model_type="BackfillProgress", operation="get_active_backfills"
                ) from e

    async def get_resumable_backfills(self) -> list[BackfillProgress]:
        """Get backfill operations that can be resumed (failed/pending with progress).

        Returns:
            List of resumable BackfillProgress instances

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(BackfillProgress)
                    .where(
                        and_(
                            BackfillProgress.status.in_(
                                [BackfillStatus.FAILED, BackfillStatus.PENDING]
                            ),
                            BackfillProgress.completed_chunks > 0,
                        )
                    )
                    .order_by(desc(BackfillProgress.created_at))
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                msg = "Failed to retrieve resumable backfill operations"
                raise DataAccessError(
                    msg,
                    model_type="BackfillProgress",
                    operation="get_resumable_backfills",
                ) from e

    async def get_by_area_endpoint(
        self, area_code: str, endpoint_name: str
    ) -> list[BackfillProgress]:
        """Get backfill operations for specific area/endpoint combination.

        Args:
            area_code: Geographic area code (e.g., 'DE', 'FR')
            endpoint_name: ENTSO-E endpoint name

        Returns:
            List of BackfillProgress instances for the area/endpoint

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(BackfillProgress)
                    .where(
                        and_(
                            BackfillProgress.area_code == area_code,
                            BackfillProgress.endpoint_name == endpoint_name,
                        )
                    )
                    .order_by(desc(BackfillProgress.created_at))
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                msg = f"Failed to retrieve backfill operations for {area_code}/{endpoint_name}"
                raise DataAccessError(
                    msg,
                    model_type="BackfillProgress",
                    operation="get_by_area_endpoint",
                    context={"area_code": area_code, "endpoint_name": endpoint_name},
                ) from e

    async def update_progress_by_id(
        self, backfill_id: int, **updates: Any
    ) -> BackfillProgress | None:
        """Update backfill progress by ID using fresh session object.

        This method resolves the session.merge() technical debt by querying
        a fresh object in the current session context before updating fields.

        Args:
            backfill_id: ID of the backfill progress to update
            **updates: Field updates to apply

        Returns:
            Updated BackfillProgress instance or None if not found

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                # Query fresh object in current session - eliminates session.merge() need
                stmt = select(BackfillProgress).where(
                    BackfillProgress.id == backfill_id
                )
                result = await session.execute(stmt)
                progress = result.scalar_one_or_none()

                if progress is None:
                    return None

                # Update fields directly on session-attached object
                for field, value in updates.items():
                    if hasattr(progress, field):
                        setattr(progress, field, value)

                await session.commit()
                await session.refresh(progress)
            except SQLAlchemyError as e:
                await session.rollback()
                msg = f"Failed to update BackfillProgress with ID {backfill_id}"
                raise DataAccessError(
                    msg,
                    model_type="BackfillProgress",
                    operation="update_progress_by_id",
                    context={"id": backfill_id, "updates": updates},
                ) from e
            else:
                return progress

    async def get_by_area_endpoint_period(
        self,
        area_code: str,
        endpoint_name: str,
        period_start: datetime,
        period_end: datetime,
    ) -> BackfillProgress | None:
        """Get backfill progress for specific area/endpoint/period combination.

        Args:
            area_code: Geographic area code
            endpoint_name: ENTSO-E endpoint name
            period_start: Start of the backfill period
            period_end: End of the backfill period

        Returns:
            BackfillProgress instance if found, None otherwise

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(BackfillProgress).where(
                    and_(
                        BackfillProgress.area_code == area_code,
                        BackfillProgress.endpoint_name == endpoint_name,
                        BackfillProgress.period_start == period_start,
                        BackfillProgress.period_end == period_end,
                    )
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                msg = (
                    f"Failed to retrieve backfill for {area_code}/{endpoint_name} "
                    f"from {period_start} to {period_end}"
                )
                raise DataAccessError(
                    msg,
                    model_type="BackfillProgress",
                    operation="get_by_area_endpoint_period",
                    context={
                        "area_code": area_code,
                        "endpoint_name": endpoint_name,
                        "period_start": period_start,
                        "period_end": period_end,
                    },
                ) from e

    def _get_model_name(self) -> str:
        """Get the model type name for error reporting.

        Returns:
            String representation of the model type
        """
        return "BackfillProgress"
