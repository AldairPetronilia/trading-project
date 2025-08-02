"""
Alert rule repository implementation with specialized rule management queries.

This repository provides comprehensive data access operations for AlertRule
with specialized methods for rule evaluation, management, and monitoring.
Supports complex querying for rule activation, targeting, and performance
analytics essential for effective alert system operation.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.config.database import Database
from app.exceptions.repository_exceptions import DataAccessError
from app.models.alert_enums import AlertRuleStatus, AlertSeverity, AlertType
from app.models.alert_rule import AlertRule
from app.models.load_data import EnergyDataType
from app.repositories.base_repository import BaseRepository


class AlertRuleRepository(BaseRepository[AlertRule]):
    """
    Repository for alert rules with specialized management and evaluation queries.

    Provides comprehensive data access operations for alert rule management,
    including rule evaluation queries, targeting operations, and performance
    analytics. Supports complex filtering for rule activation scenarios and
    maintenance operations for effective alert system governance.

    Key capabilities:
    - Active rule retrieval with type and targeting filters
    - Rule evaluation support for scheduler integration
    - Area and data type targeting queries
    - Rule lifecycle management and status operations
    - Performance metrics and usage analytics
    - Maintenance operations for rule cleanup and optimization
    """

    def __init__(self, database: Database) -> None:
        """Initialize alert rule repository with database dependency.

        Args:
            database: Database instance for session management
        """
        super().__init__(database)

    async def get_by_id(self, item_id: Any) -> AlertRule | None:
        """Retrieve an alert rule by ID.

        Args:
            item_id: The alert rule ID

        Returns:
            AlertRule instance if found, None otherwise

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(AlertRule).where(AlertRule.id == item_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                error_msg = f"Failed to retrieve AlertRule with ID {item_id}"
                raise DataAccessError(
                    error_msg,
                    model_type="AlertRule",
                    operation="get_by_id",
                    context={"id": item_id},
                ) from e

    async def get_all(self) -> list[AlertRule]:
        """Retrieve all alert rules.

        Returns:
            List of all AlertRule instances ordered by name

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(AlertRule).order_by(AlertRule.name)
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve all AlertRule records"
                raise DataAccessError(
                    error_msg,
                    model_type="AlertRule",
                    operation="get_all",
                ) from e

    async def delete(self, item_id: Any) -> bool:
        """Delete an alert rule by ID.

        Args:
            item_id: The alert rule ID

        Returns:
            True if rule was deleted, False if not found

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(AlertRule).where(AlertRule.id == item_id)
                result = await session.execute(stmt)
                rule = result.scalar_one_or_none()

                if rule is None:
                    return False

                await session.delete(rule)
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                error_msg = f"Failed to delete AlertRule with ID {item_id}"
                raise DataAccessError(
                    error_msg,
                    model_type="AlertRule",
                    operation="delete",
                    context={"id": item_id},
                ) from e
            else:
                return True

    async def get_by_name(self, name: str) -> AlertRule | None:
        """Retrieve an alert rule by name.

        Args:
            name: The unique alert rule name

        Returns:
            AlertRule instance if found, None otherwise

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = select(AlertRule).where(AlertRule.name == name)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                error_msg = f"Failed to retrieve AlertRule with name '{name}'"
                raise DataAccessError(
                    error_msg,
                    model_type="AlertRule",
                    operation="get_by_name",
                    context={"name": name},
                ) from e

    async def get_active_rules(
        self,
        alert_type: AlertType | None = None,
        severity: AlertSeverity | None = None,
    ) -> list[AlertRule]:
        """Retrieve active alert rules with optional filtering.

        Args:
            alert_type: Optional alert type to filter by
            severity: Optional severity level to filter by

        Returns:
            List of active AlertRule instances matching criteria

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                conditions = [AlertRule.status == AlertRuleStatus.ACTIVE]

                if alert_type:
                    conditions.append(AlertRule.alert_type == alert_type)
                if severity:
                    conditions.append(AlertRule.severity == severity)

                stmt = (
                    select(AlertRule).where(and_(*conditions)).order_by(AlertRule.name)
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve active alert rules"
                raise DataAccessError(
                    error_msg,
                    model_type="AlertRule",
                    operation="get_active_rules",
                    context={
                        "alert_type": alert_type.value if alert_type else None,
                        "severity": severity.value if severity else None,
                    },
                ) from e

    async def get_rules_for_evaluation(
        self,
        current_time: datetime | None = None,
    ) -> list[AlertRule]:
        """Retrieve active rules that are due for evaluation.

        This method finds active rules that should be evaluated based on their
        evaluation interval and last trigger time, considering cooldown periods.

        Args:
            current_time: Current time for evaluation (defaults to now)

        Returns:
            List of AlertRule instances ready for evaluation

        Raises:
            DataAccessError: If database operation fails
        """
        if current_time is None:
            current_time = datetime.now(UTC)

        async with self.database.session_factory() as session:
            try:
                # Rules are due for evaluation if:
                # 1. They are active
                # 2. Either never triggered OR last trigger + evaluation interval <= now
                conditions = [AlertRule.status == AlertRuleStatus.ACTIVE]

                # Add time-based evaluation conditions
                never_triggered = AlertRule.last_triggered.is_(None)

                # For rules that have been triggered, check if evaluation interval has passed
                interval_passed = and_(
                    AlertRule.last_triggered.is_not(None),
                    func.extract("epoch", current_time - AlertRule.last_triggered)
                    >= AlertRule.evaluation_interval_minutes * 60,
                )

                conditions.append(or_(never_triggered, interval_passed))

                stmt = (
                    select(AlertRule)
                    .where(and_(*conditions))
                    .order_by(AlertRule.severity.desc(), AlertRule.name)
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = "Failed to retrieve rules for evaluation"
                raise DataAccessError(
                    error_msg,
                    model_type="AlertRule",
                    operation="get_rules_for_evaluation",
                    context={"current_time": current_time.isoformat()},
                ) from e

    async def get_rules_targeting_area(
        self,
        area_code: str,
        alert_type: AlertType | None = None,
        *,
        active_only: bool = True,
    ) -> list[AlertRule]:
        """Retrieve rules that target a specific area.

        Args:
            area_code: Geographic area code to filter by
            alert_type: Optional alert type to filter by
            active_only: Whether to return only active rules

        Returns:
            List of AlertRule instances targeting the specified area

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                conditions = []

                if active_only:
                    conditions.append(AlertRule.status == AlertRuleStatus.ACTIVE)

                if alert_type:
                    conditions.append(AlertRule.alert_type == alert_type)

                # Rules target this area if they are global OR include this area code
                area_targeting = or_(
                    AlertRule.is_global == True,  # noqa: E712
                    AlertRule.area_codes.op("?")(area_code),
                )
                conditions.append(area_targeting)

                stmt = (
                    select(AlertRule)
                    .where(and_(*conditions))
                    .order_by(AlertRule.severity.desc(), AlertRule.name)
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = f"Failed to retrieve rules targeting area '{area_code}'"
                raise DataAccessError(
                    error_msg,
                    model_type="AlertRule",
                    operation="get_rules_targeting_area",
                    context={
                        "area_code": area_code,
                        "alert_type": alert_type.value if alert_type else None,
                        "active_only": active_only,
                    },
                ) from e

    async def get_rules_targeting_data_type(
        self,
        data_type: EnergyDataType,
        area_code: str | None = None,
        *,
        active_only: bool = True,
    ) -> list[AlertRule]:
        """Retrieve rules that target a specific data type.

        Args:
            data_type: Energy data type to filter by
            area_code: Optional area code for additional filtering
            active_only: Whether to return only active rules

        Returns:
            List of AlertRule instances targeting the specified data type

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                conditions = []

                if active_only:
                    conditions.append(AlertRule.status == AlertRuleStatus.ACTIVE)

                if area_code:
                    area_targeting = or_(
                        AlertRule.is_global == True,  # noqa: E712
                        AlertRule.area_codes.op("?")(area_code),
                    )
                    conditions.append(area_targeting)

                # Rules target this data type if they have no data type restrictions
                # OR include this specific data type
                data_type_targeting = or_(
                    AlertRule.data_types.is_(None),
                    AlertRule.data_types.op("?")(data_type.value),
                )
                conditions.append(data_type_targeting)

                stmt = (
                    select(AlertRule)
                    .where(and_(*conditions))
                    .order_by(AlertRule.severity.desc(), AlertRule.name)
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = (
                    f"Failed to retrieve rules targeting data type '{data_type.value}'"
                )
                raise DataAccessError(
                    error_msg,
                    model_type="AlertRule",
                    operation="get_rules_targeting_data_type",
                    context={
                        "data_type": data_type.value,
                        "area_code": area_code,
                        "active_only": active_only,
                    },
                ) from e

    async def get_rules_by_status(self, status: AlertRuleStatus) -> list[AlertRule]:
        """Retrieve all rules with a specific status.

        Args:
            status: The rule status to filter by

        Returns:
            List of AlertRule instances with the specified status

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                stmt = (
                    select(AlertRule)
                    .where(AlertRule.status == status)
                    .order_by(AlertRule.name)
                )

                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError as e:
                error_msg = f"Failed to retrieve rules with status '{status.value}'"
                raise DataAccessError(
                    error_msg,
                    model_type="AlertRule",
                    operation="get_rules_by_status",
                    context={"status": status.value},
                ) from e

    async def update_trigger_info(
        self,
        rule_id: int,
        triggered_at: datetime | None = None,
    ) -> bool:
        """Update rule trigger information.

        Args:
            rule_id: The alert rule ID
            triggered_at: Timestamp when rule was triggered (defaults to now)

        Returns:
            True if rule was updated, False if not found

        Raises:
            DataAccessError: If database operation fails
        """
        if triggered_at is None:
            triggered_at = datetime.now(UTC)

        async with self.database.session_factory() as session:
            try:
                stmt = select(AlertRule).where(AlertRule.id == rule_id)
                result = await session.execute(stmt)
                rule = result.scalar_one_or_none()

                if rule is None:
                    return False

                rule.last_triggered = triggered_at
                rule.trigger_count += 1
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                error_msg = f"Failed to update trigger info for AlertRule ID {rule_id}"
                raise DataAccessError(
                    error_msg,
                    model_type="AlertRule",
                    operation="update_trigger_info",
                    context={
                        "rule_id": rule_id,
                        "triggered_at": triggered_at.isoformat(),
                    },
                ) from e
            else:
                return True

    async def get_rule_statistics(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """Get aggregated statistics for rule triggers within a time range.

        Args:
            start_time: Start of the time range (inclusive)
            end_time: End of the time range (inclusive)

        Returns:
            Dictionary containing rule statistics

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                # Get basic counts
                total_stmt = select(func.count(AlertRule.id))
                total_result = await session.execute(total_stmt)
                total_rules = total_result.scalar() or 0

                active_stmt = select(func.count(AlertRule.id)).where(
                    AlertRule.status == AlertRuleStatus.ACTIVE
                )
                active_result = await session.execute(active_stmt)
                active_rules = active_result.scalar() or 0

                # Get rules triggered in time range
                triggered_stmt = select(func.count(AlertRule.id)).where(
                    and_(
                        AlertRule.last_triggered >= start_time,
                        AlertRule.last_triggered <= end_time,
                    )
                )
                triggered_result = await session.execute(triggered_stmt)
                triggered_rules = triggered_result.scalar() or 0

                # Get average trigger count for active rules
                avg_triggers_stmt = select(func.avg(AlertRule.trigger_count)).where(
                    AlertRule.status == AlertRuleStatus.ACTIVE
                )
                avg_result = await session.execute(avg_triggers_stmt)
                avg_triggers = avg_result.scalar() or 0.0

                return {
                    "total_rules": total_rules,
                    "active_rules": active_rules,
                    "inactive_rules": total_rules - active_rules,
                    "rules_triggered_in_period": triggered_rules,
                    "average_trigger_count": float(avg_triggers),
                    "period_start": start_time.isoformat(),
                    "period_end": end_time.isoformat(),
                }
            except SQLAlchemyError as e:
                error_msg = "Failed to get rule statistics"
                raise DataAccessError(
                    error_msg,
                    model_type="AlertRule",
                    operation="get_rule_statistics",
                    context={
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                    },
                ) from e

    async def cleanup_inactive_rules(self, inactive_days: int) -> int:
        """Remove rules that have been inactive for the specified period.

        Args:
            inactive_days: Number of days a rule must be inactive to be cleaned up

        Returns:
            Number of deleted rules

        Raises:
            DataAccessError: If database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                cutoff_date = datetime.now(UTC) - timedelta(days=inactive_days)

                # Find inactive rules older than cutoff
                conditions = [
                    AlertRule.status == AlertRuleStatus.INACTIVE,
                    AlertRule.updated_at < cutoff_date,
                ]

                count_stmt = select(func.count(AlertRule.id)).where(and_(*conditions))
                count_result = await session.execute(count_stmt)
                delete_count = count_result.scalar() or 0

                if delete_count == 0:
                    return 0

                # Delete old inactive rules
                rules_stmt = select(AlertRule).where(and_(*conditions))
                rules_result = await session.execute(rules_stmt)
                inactive_rules = rules_result.scalars().all()

                for rule in inactive_rules:
                    await session.delete(rule)

                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                error_msg = (
                    f"Failed to cleanup inactive rules older than {inactive_days} days"
                )
                raise DataAccessError(
                    error_msg,
                    model_type="AlertRule",
                    operation="cleanup_inactive_rules",
                    context={
                        "inactive_days": inactive_days,
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
        return "AlertRule"
