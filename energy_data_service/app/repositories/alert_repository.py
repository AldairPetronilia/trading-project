from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.config.database import Database
from app.exceptions.repository_exceptions import DataAccessError
from app.models.alert import Alert
from app.models.alert_enums import AlertDeliveryStatus, AlertSeverity
from app.repositories.base_repository import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    """
    Repository for alert management with specialized alert monitoring and delivery queries.

    Provides comprehensive data access operations for tracking alert instances,
    delivery status management, and correlation-based deduplication. Supports
    time-based queries, delivery status filtering, and alert resolution tracking
    for effective alert processing and monitoring.

    Key capabilities:
    - Alert filtering by delivery status, time range, and correlation keys
    - Delivery status updates and retry candidate identification
    - Alert resolution tracking and management
    - Rule-based alert retrieval for monitoring specific rules
    - Maintenance operations for alert cleanup and retention
    - Recent alert retrieval for real-time monitoring
    """

    def __init__(self, database: Database) -> None:
        """Initialize alert repository with database dependency.

        Args:
            database: Database instance for session management
        """
        super().__init__(database)

    async def get_by_id(self, item_id: Any) -> Alert | None:
        """Retrieve an alert record by ID.

        Args:
            item_id: The alert ID

        Returns:
            Alert instance if found, None otherwise

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(Alert).where(Alert.id == item_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                error_msg = f"Failed to retrieve Alert with ID {item_id}"
                raise DataAccessError(
                    error_msg,
                    model_type="Alert",
                    operation="get_by_id",
                    context={"id": item_id},
                ) from e

    async def get_all(self) -> list[Alert]:
        """Retrieve all alert records.

        Returns:
            List of all Alert instances ordered by triggered_at desc

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(Alert).order_by(desc(Alert.triggered_at))
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve all Alert records"
                raise DataAccessError(
                    error_msg,
                    model_type="Alert",
                    operation="get_all",
                ) from e

    async def delete(self, item_id: Any) -> bool:
        """Delete an alert record by ID.

        Args:
            item_id: The alert ID

        Returns:
            True if record was deleted, False if not found

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(Alert).where(Alert.id == item_id)
                result = await session.execute(stmt)
                alert = result.scalar_one_or_none()

                if alert is None:
                    return False

                await session.delete(alert)
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                error_msg = f"Failed to delete Alert with ID {item_id}"
                raise DataAccessError(
                    error_msg,
                    model_type="Alert",
                    operation="delete",
                    context={"id": item_id},
                ) from e
            else:
                return True

    async def get_pending_alerts(self) -> list[Alert]:
        """Get all alerts with PENDING delivery status.

        Returns:
            List of alerts with pending delivery status, ordered by triggered_at

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(Alert)
                    .where(Alert.delivery_status == AlertDeliveryStatus.PENDING)
                    .order_by(Alert.triggered_at)
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve pending alerts"
                raise DataAccessError(
                    error_msg,
                    model_type="Alert",
                    operation="get_pending_alerts",
                ) from e

    async def get_alerts_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        severity: AlertSeverity | None = None,
        rule_ids: list[int] | None = None,
        area_code: str | None = None,
        data_type: str | None = None,
    ) -> list[Alert]:
        """Get alerts within time range with optional filtering.

        Args:
            start_time: Start of the time range (inclusive)
            end_time: End of the time range (inclusive)
            severity: Optional severity level to filter by
            rule_ids: Optional list of alert rule IDs to filter by
            area_code: Optional area code to filter by
            data_type: Optional data type to filter by

        Returns:
            List of alerts matching the criteria, ordered by triggered_at desc

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                conditions = [
                    Alert.triggered_at >= start_time,
                    Alert.triggered_at <= end_time,
                ]

                if severity:
                    conditions.append(Alert.severity == severity)
                if rule_ids:
                    conditions.append(Alert.alert_rule_id.in_(rule_ids))
                if area_code:
                    conditions.append(Alert.area_code == area_code)
                if data_type:
                    conditions.append(Alert.data_type == data_type)

                stmt = (
                    select(Alert)
                    .where(and_(*conditions))
                    .order_by(desc(Alert.triggered_at))
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve alerts by time range"
                raise DataAccessError(
                    error_msg,
                    model_type="Alert",
                    operation="get_alerts_by_time_range",
                    context={
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "severity": severity.value if severity else None,
                        "rule_ids_count": len(rule_ids) if rule_ids else 0,
                        "area_code": area_code,
                        "data_type": data_type,
                    },
                ) from e

    async def get_alerts_by_correlation_key(self, correlation_key: str) -> list[Alert]:
        """Get alerts with the same correlation key for deduplication.

        Args:
            correlation_key: The correlation key to search for

        Returns:
            List of alerts with matching correlation key, ordered by triggered_at desc

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(Alert)
                    .where(Alert.correlation_key == correlation_key)
                    .order_by(desc(Alert.triggered_at))
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = (
                    f"Failed to retrieve alerts with correlation key {correlation_key}"
                )
                raise DataAccessError(
                    error_msg,
                    model_type="Alert",
                    operation="get_alerts_by_correlation_key",
                    context={"correlation_key": correlation_key},
                ) from e

    async def get_unresolved_alerts(self) -> list[Alert]:
        """Get alerts where resolved_at is None.

        Returns:
            List of unresolved alerts ordered by triggered_at desc

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(Alert)
                    .where(Alert.resolved_at.is_(None))
                    .order_by(desc(Alert.triggered_at))
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve unresolved alerts"
                raise DataAccessError(
                    error_msg,
                    model_type="Alert",
                    operation="get_unresolved_alerts",
                ) from e

    async def get_alerts_by_delivery_status(
        self, delivery_status: AlertDeliveryStatus
    ) -> list[Alert]:
        """Get alerts by delivery status.

        Args:
            delivery_status: The delivery status to filter by

        Returns:
            List of alerts with matching delivery status, ordered by triggered_at desc

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(Alert)
                    .where(Alert.delivery_status == delivery_status)
                    .order_by(desc(Alert.triggered_at))
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = f"Failed to retrieve alerts with delivery status {delivery_status.value}"
                raise DataAccessError(
                    error_msg,
                    model_type="Alert",
                    operation="get_alerts_by_delivery_status",
                    context={"delivery_status": delivery_status.value},
                ) from e

    async def update_delivery_status(
        self,
        alert_id: int,
        status: AlertDeliveryStatus,
        delivery_details: dict[str, Any] | None = None,
    ) -> Alert | None:
        """Update alert delivery status and attempts.

        Args:
            alert_id: ID of the alert to update
            status: New delivery status
            delivery_details: Optional delivery details to merge

        Returns:
            Updated Alert instance if found, None otherwise

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(Alert).where(Alert.id == alert_id)
                result = await session.execute(stmt)
                alert = result.scalar_one_or_none()

                if alert is None:
                    return None

                alert.delivery_status = status
                alert.delivery_attempts += 1
                alert.last_delivery_attempt = datetime.now(UTC)

                if delivery_details:
                    alert.delivery_details.update(delivery_details)

                await session.commit()
                await session.refresh(alert)
            except SQLAlchemyError as e:
                await session.rollback()
                error_msg = f"Failed to update delivery status for alert {alert_id}"
                raise DataAccessError(
                    error_msg,
                    model_type="Alert",
                    operation="update_delivery_status",
                    context={
                        "alert_id": alert_id,
                        "status": status.value,
                    },
                ) from e
            else:
                return alert

    async def get_recent_alerts(self, minutes: int) -> list[Alert]:
        """Get alerts from last N minutes.

        Args:
            minutes: Number of minutes back to retrieve alerts from

        Returns:
            List of recent alerts ordered by triggered_at desc

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                cutoff_time = datetime.now(UTC) - timedelta(minutes=minutes)

                stmt = (
                    select(Alert)
                    .where(Alert.triggered_at >= cutoff_time)
                    .order_by(desc(Alert.triggered_at))
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = f"Failed to retrieve alerts from last {minutes} minutes"
                raise DataAccessError(
                    error_msg,
                    model_type="Alert",
                    operation="get_recent_alerts",
                    context={"minutes": minutes},
                ) from e

    async def get_alerts_for_rule(self, rule_id: int) -> list[Alert]:
        """Get all alerts for a specific rule ID.

        Args:
            rule_id: The alert rule ID

        Returns:
            List of alerts for the rule, ordered by triggered_at desc

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(Alert)
                    .where(Alert.alert_rule_id == rule_id)
                    .order_by(desc(Alert.triggered_at))
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = f"Failed to retrieve alerts for rule ID {rule_id}"
                raise DataAccessError(
                    error_msg,
                    model_type="Alert",
                    operation="get_alerts_for_rule",
                    context={"rule_id": rule_id},
                ) from e

    async def mark_alert_resolved(
        self,
        alert_id: int,
        resolved_by: str | None = None,
        notes: str | None = None,
    ) -> Alert | None:
        """Mark alert as resolved with timestamp and notes.

        Args:
            alert_id: ID of the alert to resolve
            resolved_by: Identifier of who resolved the alert
            notes: Optional resolution notes

        Returns:
            Updated Alert instance if found, None otherwise

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(Alert).where(Alert.id == alert_id)
                result = await session.execute(stmt)
                alert = result.scalar_one_or_none()

                if alert is None:
                    return None

                alert.resolved_at = datetime.now(UTC)
                alert.resolved_by = resolved_by
                alert.resolution_notes = notes

                await session.commit()
                await session.refresh(alert)
            except SQLAlchemyError as e:
                await session.rollback()
                error_msg = f"Failed to mark alert {alert_id} as resolved"
                raise DataAccessError(
                    error_msg,
                    model_type="Alert",
                    operation="mark_alert_resolved",
                    context={
                        "alert_id": alert_id,
                        "resolved_by": resolved_by,
                    },
                ) from e
            else:
                return alert

    async def get_delivery_retry_candidates(
        self,
        max_attempts: int = 3,
        retry_delay_minutes: int = 15,
    ) -> list[Alert]:
        """Get alerts that should be retried for delivery.

        Args:
            max_attempts: Maximum number of delivery attempts before giving up
            retry_delay_minutes: Minimum minutes between retry attempts

        Returns:
            List of alerts eligible for delivery retry, ordered by last_delivery_attempt

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                retry_cutoff = datetime.now(UTC) - timedelta(
                    minutes=retry_delay_minutes
                )

                conditions = [
                    Alert.delivery_status.in_(
                        [
                            AlertDeliveryStatus.FAILED,
                            AlertDeliveryStatus.RETRYING,
                        ]
                    ),
                    Alert.delivery_attempts < max_attempts,
                    Alert.last_delivery_attempt < retry_cutoff,
                ]

                stmt = (
                    select(Alert)
                    .where(and_(*conditions))
                    .order_by(Alert.last_delivery_attempt)
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve delivery retry candidates"
                raise DataAccessError(
                    error_msg,
                    model_type="Alert",
                    operation="get_delivery_retry_candidates",
                    context={
                        "max_attempts": max_attempts,
                        "retry_delay_minutes": retry_delay_minutes,
                    },
                ) from e

    async def cleanup_resolved_alerts(self, retention_days: int) -> int:
        """Remove old resolved alerts for maintenance.

        Args:
            retention_days: Number of days to retain resolved alerts

        Returns:
            Number of deleted alert records

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

                # Get count of records to be deleted for logging
                count_stmt = select(func.count(Alert.id)).where(
                    and_(
                        Alert.resolved_at.is_not(None),
                        Alert.resolved_at < cutoff_date,
                    )
                )
                count_result = await session.execute(count_stmt)
                delete_count = count_result.scalar() or 0

                if delete_count == 0:
                    return 0

                # Delete old resolved alerts
                delete_stmt = select(Alert).where(
                    and_(
                        Alert.resolved_at.is_not(None),
                        Alert.resolved_at < cutoff_date,
                    )
                )
                result = await session.execute(delete_stmt)
                old_alerts = result.scalars().all()

                for alert in old_alerts:
                    await session.delete(alert)

                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                error_msg = f"Failed to cleanup resolved alerts older than {retention_days} days"
                raise DataAccessError(
                    error_msg,
                    model_type="Alert",
                    operation="cleanup_resolved_alerts",
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
        return "Alert"
