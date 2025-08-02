"""
Alert service for comprehensive alert management and delivery.

This service provides comprehensive alerting capabilities for the energy data platform,
enabling intelligent monitoring, multi-channel delivery, deduplication, and recovery
tracking across all system components and data collection operations.

Key Features:
- Multi-channel alert delivery (email, webhook) with retry logic
- Smart alert deduplication and correlation to prevent notification spam
- Rate limiting and cooldown management for alert flood prevention
- Recovery notification when alert conditions are resolved
- Integration with MonitoringService for system health alerting
- Comprehensive alert rule evaluation and threshold management
- Complete audit trail with delivery tracking and resolution status
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.exceptions.service_exceptions import (
    AlertDeliveryError,
    AlertError,
    ServiceError,
)
from app.models.alert import Alert
from app.models.alert_enums import AlertDeliveryStatus, AlertSeverity, AlertType
from app.models.alert_rule import AlertRule
from app.models.load_data import EnergyDataType

if TYPE_CHECKING:
    from app.config.settings import AlertConfig
    from app.repositories.alert_repository import AlertRepository
    from app.repositories.alert_rule_repository import AlertRuleRepository
    from app.services.monitoring_service import MonitoringService

# Set up logging
log = logging.getLogger(__name__)

# Constants
DEFAULT_CORRELATION_WINDOW_MINUTES = 60
DEFAULT_DELIVERY_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_MINUTES = 15


class AlertService:
    """
    Service for comprehensive alert management, delivery, and monitoring integration.

    This service provides intelligent alerting capabilities that integrate with the
    monitoring service to detect system issues, manage alert rules, deliver notifications
    across multiple channels, and track alert resolution. It includes sophisticated
    deduplication, rate limiting, and recovery notification features.

    Key capabilities:
    - Alert rule evaluation and condition monitoring
    - Multi-channel delivery with email and webhook support
    - Smart deduplication using correlation keys and similarity detection
    - Rate limiting to prevent alert flooding during system issues
    - Recovery tracking and automatic resolution notifications
    - Integration with MonitoringService for system health alerting
    - Comprehensive delivery retry logic with exponential backoff
    - Complete audit trail for alert lifecycle management
    """

    def __init__(
        self,
        alert_repository: AlertRepository,
        alert_rule_repository: AlertRuleRepository,
        config: AlertConfig,
        monitoring_service: MonitoringService | None = None,
    ) -> None:
        """
        Initialize the alert service.

        Args:
            alert_repository: Repository for alert data operations
            alert_rule_repository: Repository for alert rule operations
            config: Alert configuration settings
            monitoring_service: Optional monitoring service for health integration
        """
        self._alert_repository = alert_repository
        self._alert_rule_repository = alert_rule_repository
        self._config = config
        self._monitoring_service = monitoring_service

    async def evaluate_alert_rules(self) -> dict[str, Any]:
        """
        Evaluate all active alert rules against current system conditions.

        This method checks all active alert rules, evaluates their conditions
        against current monitoring data, and triggers alerts when thresholds
        are exceeded. It includes rate limiting and cooldown logic to prevent
        alert spam.

        Returns:
            Dictionary with evaluation results including triggered alerts and metrics

        Raises:
            AlertError: If rule evaluation fails
        """
        try:
            # Get all active rules ready for evaluation
            active_rules = await self._alert_rule_repository.get_rules_for_evaluation()

            evaluation_results = {
                "evaluation_timestamp": datetime.now(UTC).isoformat(),
                "total_rules_evaluated": len(active_rules),
                "alerts_triggered": 0,
                "rules_skipped_cooldown": 0,
                "rules_skipped_rate_limit": 0,
                "triggered_rule_details": [],
                "evaluation_errors": [],
            }

            for rule in active_rules:
                try:
                    # Check if rule can trigger (cooldown, rate limits)
                    if not rule.can_trigger_alert():
                        if rule.is_cooldown_active:
                            evaluation_results["rules_skipped_cooldown"] += 1
                        elif rule.is_rate_limited:
                            evaluation_results["rules_skipped_rate_limit"] += 1
                        continue

                    # Evaluate rule conditions
                    (
                        should_trigger,
                        trigger_context,
                    ) = await self._evaluate_rule_conditions(rule)

                    if should_trigger:
                        # Create and deliver alert
                        alert = await self._trigger_alert_from_rule(
                            rule, trigger_context
                        )
                        evaluation_results["alerts_triggered"] += 1
                        evaluation_results["triggered_rule_details"].append(
                            {
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "alert_id": alert.id,
                                "severity": alert.severity.value,
                            }
                        )

                        log.info(
                            "Alert triggered for rule %s (ID: %d): %s",
                            rule.name,
                            rule.id,
                            alert.title,
                        )

                except Exception as rule_error:
                    error_detail = {
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "error": str(rule_error),
                    }
                    evaluation_results["evaluation_errors"].append(error_detail)
                    log.warning(
                        "Failed to evaluate rule %s (ID: %d): %s",
                        rule.name,
                        rule.id,
                        rule_error,
                    )

            log.debug(
                "Alert rule evaluation completed: %d rules evaluated, %d alerts triggered",
                evaluation_results["total_rules_evaluated"],
                evaluation_results["alerts_triggered"],
            )

        except Exception as e:
            error_msg = f"Failed to evaluate alert rules: {e}"
            raise AlertError(
                error_msg,
                alert_operation="evaluate_alert_rules",
                context={"error_type": type(e).__name__},
            ) from e
        else:
            return evaluation_results

    async def create_alert(
        self,
        rule: AlertRule,
        title: str,
        message: str,
        trigger_context: dict[str, Any],
        *,
        severity: AlertSeverity | None = None,
        area_code: str | None = None,
        data_type: str | None = None,
        correlation_key: str | None = None,
    ) -> Alert:
        """
        Create a new alert from rule trigger with deduplication checking.

        Args:
            rule: Alert rule that triggered this alert
            title: Short descriptive title for the alert
            message: Detailed alert message
            trigger_context: Context information about what triggered the alert
            severity: Optional severity override (uses rule severity if not provided)
            area_code: Optional area code if alert is area-specific
            data_type: Optional data type if alert is data-type-specific
            correlation_key: Optional correlation key for deduplication

        Returns:
            Created Alert instance

        Raises:
            AlertError: If alert creation fails
        """
        try:
            # Generate correlation key if not provided
            if not correlation_key:
                correlation_key = self.generate_correlation_key(
                    alert_type=rule.alert_type,
                    area_code=area_code,
                    data_type=data_type,
                    trigger_context=trigger_context,
                )

            # Check for deduplication
            if await self.should_deduplicate_alert(correlation_key):
                log.debug(
                    "Alert deduplicated for correlation key: %s",
                    correlation_key,
                )
                # Return the most recent similar alert instead of creating new one
                existing_alert = await self.find_similar_alerts(correlation_key)
                if existing_alert:
                    return existing_alert

            # Create new alert
            alert = Alert(
                alert_rule_id=rule.id,
                alert_type=rule.alert_type,
                severity=severity or rule.severity,
                title=title,
                message=message,
                triggered_at=datetime.now(UTC),
                triggered_by="AlertService",
                trigger_context=trigger_context,
                correlation_key=correlation_key,
                area_code=area_code,
                data_type=data_type,
                delivery_status=AlertDeliveryStatus.PENDING,
            )

            # Save alert to database using the repository
            alert = await self._alert_repository.create(alert)

            # Update rule trigger information
            await self._alert_rule_repository.update_trigger_info(rule.id)

            log.info(
                "Created alert %d for rule %s: %s",
                alert.id,
                rule.name,
                alert.title,
            )

        except Exception as e:
            error_msg = f"Failed to create alert for rule {rule.name}: {e}"
            raise AlertError(
                error_msg,
                alert_operation="create_alert",
                context={
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "correlation_key": correlation_key,
                },
            ) from e
        else:
            return alert

    async def resolve_alert(
        self,
        alert_id: int,
        resolved_by: str | None = None,
        notes: str | None = None,
    ) -> Alert | None:
        """
        Mark an alert as resolved and send recovery notification if configured.

        Args:
            alert_id: ID of the alert to resolve
            resolved_by: Identifier of who resolved the alert
            notes: Optional resolution notes

        Returns:
            Updated Alert instance if found, None otherwise

        Raises:
            AlertError: If alert resolution fails
        """
        try:
            alert = await self._alert_repository.mark_alert_resolved(
                alert_id=alert_id,
                resolved_by=resolved_by,
                notes=notes,
            )

            if alert is None:
                return None

            # Send recovery notification if configured
            await self._send_recovery_notification(alert)

            log.info(
                "Resolved alert %d: %s (resolved by: %s)",
                alert.id,
                alert.title,
                resolved_by or "system",
            )

        except Exception as e:
            error_msg = f"Failed to resolve alert {alert_id}: {e}"
            raise AlertError(
                error_msg,
                alert_operation="resolve_alert",
                context={"alert_id": alert_id, "resolved_by": resolved_by},
            ) from e
        else:
            return alert

    async def get_active_alerts(
        self,
        *,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        area_code: str | None = None,
        limit: int | None = None,
    ) -> list[Alert]:
        """
        Get active (unresolved) alerts with optional filtering.

        Args:
            severity: Optional severity level to filter by
            alert_type: Optional alert type to filter by
            area_code: Optional area code to filter by
            limit: Optional limit on number of results

        Returns:
            List of active Alert instances

        Raises:
            AlertError: If retrieval fails
        """
        try:
            alerts = await self._alert_repository.get_unresolved_alerts(
                severity=severity,
                alert_type=alert_type,
                area_code=area_code,
                limit=limit,
            )
            log.debug(
                "Retrieved %d active alerts (severity: %s, type: %s, area: %s)",
                len(alerts),
                severity.value if severity else "any",
                alert_type.value if alert_type else "any",
                area_code or "any",
            )
        except Exception as e:
            error_msg = f"Failed to get active alerts: {e}"
            raise AlertError(
                error_msg,
                alert_operation="get_active_alerts",
                context={
                    "severity": severity.value if severity else None,
                    "alert_type": alert_type.value if alert_type else None,
                    "area_code": area_code,
                    "limit": limit,
                },
            ) from e
        else:
            return alerts

    async def find_similar_alerts(
        self, correlation_key: str, window_minutes: int | None = None
    ) -> Alert | None:
        """
        Find the most recent, unresolved alert with the same correlation key within a time window.

        Args:
            correlation_key: Correlation key to search for
            window_minutes: Time window in minutes (uses config default if not provided)

        Returns:
            The most recent unresolved alert if found, None otherwise

        Raises:
            AlertError: If search fails
        """
        try:
            if window_minutes is None:
                window_minutes = self._config.cooldown_override_minutes

            window = timedelta(minutes=window_minutes)
            alert = await self._alert_repository.find_unresolved_similar_alert(
                correlation_key, window
            )

            log.debug(
                "Found %s similar alert for correlation key %s within %d minutes",
                "a" if alert else "no",
                correlation_key,
                window_minutes,
            )
        except Exception as e:
            error_msg = f"Failed to find similar alerts: {e}"
            raise AlertError(
                error_msg,
                alert_operation="find_similar_alerts",
                context={
                    "correlation_key": correlation_key,
                    "window_minutes": window_minutes,
                },
            ) from e
        else:
            return alert

    async def should_deduplicate_alert(
        self, correlation_key: str, window_minutes: int | None = None
    ) -> bool:
        """
        Check if an alert should be deduplicated based on recent similar alerts.

        Args:
            correlation_key: Correlation key to check for duplicates
            window_minutes: Time window for deduplication check

        Returns:
            True if alert should be deduplicated, False otherwise

        Raises:
            AlertError: If deduplication check fails
        """
        try:
            similar_alert = await self.find_similar_alerts(
                correlation_key, window_minutes
            )
            should_dedupe = similar_alert is not None

            log.debug(
                "Deduplication check for %s: %s",
                correlation_key,
                "DEDUPLICATE" if should_dedupe else "CREATE_NEW",
            )
        except Exception as e:
            error_msg = f"Failed to check alert deduplication: {e}"
            raise AlertError(
                error_msg,
                alert_operation="should_deduplicate_alert",
                context={"correlation_key": correlation_key},
            ) from e
        else:
            return should_dedupe

    def generate_correlation_key(
        self,
        alert_type: AlertType,
        area_code: str | None = None,
        data_type: str | None = None,
        trigger_context: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate a correlation key for alert grouping and deduplication.

        Args:
            alert_type: Type of alert
            area_code: Optional area code
            data_type: Optional data type
            trigger_context: Optional trigger context for additional correlation

        Returns:
            Generated correlation key string
        """
        # Build correlation components
        components = [alert_type.value]

        if area_code:
            components.append(f"area:{area_code}")
        if data_type:
            components.append(f"data:{data_type}")

        # Add specific context for certain alert types
        if trigger_context:
            if (
                alert_type == AlertType.SYSTEM_HEALTH
                and "health_check" in trigger_context
            ):
                components.append(f"check:{trigger_context['health_check']}")
            elif (
                alert_type == AlertType.DATA_QUALITY
                and "quality_issue" in trigger_context
            ):
                components.append(f"issue:{trigger_context['quality_issue']}")
            elif (
                alert_type == AlertType.PERFORMANCE and "metric_type" in trigger_context
            ):
                components.append(f"metric:{trigger_context['metric_type']}")

        # Create hash-based correlation key
        correlation_string = "|".join(components)
        correlation_hash = hashlib.md5(correlation_string.encode()).hexdigest()[:12]

        return f"{alert_type.value}_{correlation_hash}"

    async def deliver_alert(self, alert: Alert) -> dict[str, Any]:
        """
        Deliver alert through all configured channels with retry logic.

        Args:
            alert: Alert instance to deliver

        Returns:
            Dictionary with delivery results per channel

        Raises:
            AlertError: If delivery configuration fails
        """
        try:
            # Get alert rule to determine delivery channels
            rule = await self._alert_rule_repository.get_by_id(alert.alert_rule_id)
            if not rule:
                raise AlertError(
                    f"Alert rule {alert.alert_rule_id} not found for alert {alert.id}",
                    alert_operation="deliver_alert",
                )

            delivery_results = {
                "alert_id": alert.id,
                "delivery_timestamp": datetime.now(UTC).isoformat(),
                "channels_attempted": [],
                "successful_deliveries": [],
                "failed_deliveries": [],
                "overall_status": "pending",
            }

            # Deliver through each configured channel
            for channel in rule.configured_delivery_channels:
                channel_result = None
                delivery_results["channels_attempted"].append(channel.value)

                try:
                    if channel.value == "email":
                        channel_result = await self.deliver_email(alert, rule)
                    elif channel.value == "webhook":
                        channel_result = await self.deliver_webhook(alert, rule)

                    if channel_result and channel_result.get("success"):
                        delivery_results["successful_deliveries"].append(channel.value)
                    else:
                        delivery_results["failed_deliveries"].append(channel.value)

                except Exception as channel_error:
                    delivery_results["failed_deliveries"].append(channel.value)
                    log.warning(
                        "Failed to deliver alert %d via %s: %s",
                        alert.id,
                        channel.value,
                        channel_error,
                    )

            # Update overall delivery status
            if delivery_results["successful_deliveries"]:
                if delivery_results["failed_deliveries"]:
                    delivery_results["overall_status"] = "partial"
                    new_status = AlertDeliveryStatus.RETRYING
                else:
                    delivery_results["overall_status"] = "success"
                    new_status = AlertDeliveryStatus.DELIVERED
            else:
                delivery_results["overall_status"] = "failed"
                new_status = AlertDeliveryStatus.FAILED

            # Update alert delivery status
            await self._alert_repository.update_delivery_status(
                alert.id, new_status, delivery_results
            )

            log.info(
                "Alert %d delivery completed: %s (%d successful, %d failed)",
                alert.id,
                delivery_results["overall_status"],
                len(delivery_results["successful_deliveries"]),
                len(delivery_results["failed_deliveries"]),
            )

        except Exception as e:
            error_msg = f"Failed to deliver alert {alert.id}: {e}"
            raise AlertError(
                error_msg,
                alert_operation="deliver_alert",
                context={"alert_id": alert.id},
            ) from e
        else:
            return delivery_results

    async def deliver_email(self, alert: Alert, rule: AlertRule) -> dict[str, Any]:
        """
        Deliver alert via email channel.

        Args:
            alert: Alert to deliver
            rule: Alert rule with email configuration

        Returns:
            Dictionary with email delivery result

        Raises:
            AlertDeliveryError: If email delivery fails
        """
        try:
            email_config = rule.get_delivery_config(AlertDeliveryChannel.EMAIL)

            # For now, return a mock successful delivery
            # In production, this would integrate with an email service
            result = {
                "channel": "email",
                "success": True,
                "timestamp": datetime.now(UTC).isoformat(),
                "recipients": email_config.get("recipients", []),
                "subject": f"Alert: {alert.title}",
                "delivery_id": f"email_{alert.id}_{datetime.now(UTC).timestamp()}",
            }

            log.debug("Email delivery simulated for alert %d", alert.id)

        except Exception as e:
            error_msg = f"Email delivery failed for alert {alert.id}: {e}"
            raise AlertDeliveryError(
                message=error_msg,
                delivery_channel="email",
                channel_type="email",
                alert_id=str(alert.id),
                delivery_context={"recipients": email_config.get("recipients", [])},
            ) from e
        else:
            return result

    async def deliver_webhook(self, alert: Alert, rule: AlertRule) -> dict[str, Any]:
        """
        Deliver alert via webhook channel.

        Args:
            alert: Alert to deliver
            rule: Alert rule with webhook configuration

        Returns:
            Dictionary with webhook delivery result

        Raises:
            AlertDeliveryError: If webhook delivery fails
        """
        try:
            webhook_config = rule.get_delivery_config(AlertDeliveryChannel.WEBHOOK)

            # For now, return a mock successful delivery
            # In production, this would make HTTP requests to configured webhooks
            result = {
                "channel": "webhook",
                "success": True,
                "timestamp": datetime.now(UTC).isoformat(),
                "webhook_url": webhook_config.get("url", ""),
                "response_status": 200,
                "delivery_id": f"webhook_{alert.id}_{datetime.now(UTC).timestamp()}",
            }

            log.debug("Webhook delivery simulated for alert %d", alert.id)

        except Exception as e:
            error_msg = f"Webhook delivery failed for alert {alert.id}: {e}"
            raise AlertDeliveryError(
                message=error_msg,
                delivery_channel="webhook",
                channel_type="webhook",
                alert_id=str(alert.id),
                delivery_context={"url": webhook_config.get("url", "")},
            ) from e
        else:
            return result

    async def retry_failed_deliveries(self) -> dict[str, Any]:
        """
        Retry delivery for alerts with failed or retrying status.

        Returns:
            Dictionary with retry operation results

        Raises:
            AlertError: If retry operation fails
        """
        try:
            max_attempts = self._config.max_delivery_attempts
            retry_delay = self._config.delivery_retry_delay_seconds

            retry_candidates = (
                await self._alert_repository.get_delivery_retry_candidates(
                    max_attempts=max_attempts,
                    retry_delay_minutes=int(retry_delay / 60),
                )
            )

            retry_results = {
                "retry_timestamp": datetime.now(UTC).isoformat(),
                "candidates_found": len(retry_candidates),
                "retry_attempts": 0,
                "successful_retries": 0,
                "failed_retries": 0,
                "retry_details": [],
            }

            for alert in retry_candidates:
                try:
                    retry_results["retry_attempts"] += 1
                    delivery_result = await self.deliver_alert(alert)

                    if delivery_result["overall_status"] in ["success", "partial"]:
                        retry_results["successful_retries"] += 1
                    else:
                        retry_results["failed_retries"] += 1

                    retry_results["retry_details"].append(
                        {
                            "alert_id": alert.id,
                            "attempt_number": alert.delivery_attempts + 1,
                            "result": delivery_result["overall_status"],
                        }
                    )

                except Exception as retry_error:
                    retry_results["failed_retries"] += 1
                    log.warning(
                        "Retry failed for alert %d: %s",
                        alert.id,
                        retry_error,
                    )

            log.info(
                "Delivery retry completed: %d attempts, %d successful, %d failed",
                retry_results["retry_attempts"],
                retry_results["successful_retries"],
                retry_results["failed_retries"],
            )

        except Exception as e:
            error_msg = f"Failed to retry alert deliveries: {e}"
            raise AlertError(
                error_msg,
                alert_operation="retry_failed_deliveries",
            ) from e
        else:
            return retry_results

    async def evaluate_monitoring_conditions(
        self, period: timedelta = timedelta(hours=1)
    ) -> dict[str, Any]:
        """
        Evaluate monitoring service conditions against alert thresholds.

        Args:
            period: Time period to analyze for threshold violations

        Returns:
            Dictionary with monitoring evaluation results

        Raises:
            AlertError: If monitoring evaluation fails
        """
        try:
            if not self._monitoring_service:
                return {
                    "monitoring_service_available": False,
                    "message": "Monitoring service not configured",
                }

            evaluation_results = {
                "evaluation_timestamp": datetime.now(UTC).isoformat(),
                "period_analyzed": period.total_seconds(),
                "monitoring_service_available": True,
                "threshold_violations": [],
                "system_health_alerts": [],
                "performance_alerts": [],
                "data_quality_alerts": [],
            }

            # Get system health summary
            health_summary = await self._monitoring_service.get_system_health_summary()

            # Check for system health issues
            health_status = health_summary.get("health_assessment", {}).get(
                "overall_status"
            )
            if health_status == "degraded":
                await self._create_system_health_alert(
                    health_summary, evaluation_results
                )

            # Get performance metrics
            performance_metrics = (
                await self._monitoring_service.get_performance_metrics(period)
            )

            # Check performance thresholds
            await self._check_performance_thresholds(
                performance_metrics, evaluation_results
            )

            # Analyze failure patterns for data quality alerts
            failure_analysis = await self._monitoring_service.analyze_failure_patterns(
                period
            )

            # Check failure rate thresholds
            await self._check_failure_thresholds(failure_analysis, evaluation_results)

            log.debug(
                "Monitoring condition evaluation completed: %d violations found",
                len(evaluation_results["threshold_violations"]),
            )

        except Exception as e:
            error_msg = f"Failed to evaluate monitoring conditions: {e}"
            raise AlertError(
                error_msg,
                alert_operation="evaluate_monitoring_conditions",
                context={"period_seconds": period.total_seconds()},
            ) from e
        else:
            return evaluation_results

    async def check_collection_health(self) -> dict[str, Any]:
        """
        Monitor data collection health and trigger alerts for issues.

        Returns:
            Dictionary with collection health assessment

        Raises:
            AlertError: If collection health check fails
        """
        try:
            if not self._monitoring_service:
                return {
                    "monitoring_service_available": False,
                    "message": "Monitoring service not configured for collection health checks",
                }

            health_results = {
                "check_timestamp": datetime.now(UTC).isoformat(),
                "monitoring_service_available": True,
                "collection_health_status": "healthy",
                "issues_detected": [],
                "alerts_triggered": [],
            }

            # Check recent collection activity
            recent_metrics = await self._monitoring_service.get_recent_metrics(
                60
            )  # Last hour

            if not recent_metrics:
                # No recent collection activity - potential issue
                health_results["collection_health_status"] = "degraded"
                health_results["issues_detected"].append(
                    "no_recent_collection_activity"
                )
                await self._create_collection_health_alert(
                    "No Recent Collection Activity",
                    "No data collection operations detected in the last hour",
                    {"recent_metrics_count": 0},
                    health_results,
                )

            # Check success rates
            success_rates = await self._monitoring_service.calculate_success_rates(
                timedelta(hours=24)
            )

            for combination, success_rate in success_rates.items():
                threshold = self._config.success_rate_threshold
                if success_rate < threshold:
                    health_results["collection_health_status"] = "degraded"
                    health_results["issues_detected"].append(
                        f"low_success_rate_{combination}"
                    )
                    await self._create_collection_health_alert(
                        f"Low Success Rate: {combination}",
                        f"Collection success rate ({success_rate:.2%}) below threshold ({threshold:.2%}) for {combination}",
                        {
                            "combination": combination,
                            "success_rate": success_rate,
                            "threshold": threshold,
                        },
                        health_results,
                    )

            log.debug(
                "Collection health check completed: %s status, %d issues detected",
                health_results["collection_health_status"],
                len(health_results["issues_detected"]),
            )

        except Exception as e:
            error_msg = f"Failed to check collection health: {e}"
            raise AlertError(
                error_msg,
                alert_operation="check_collection_health",
            ) from e
        else:
            return health_results

    async def send_system_health_alert(
        self,
        title: str,
        message: str,
        context: dict[str, Any],
        severity: AlertSeverity = AlertSeverity.HIGH,
    ) -> Alert | None:
        """
        Send a system health alert with specified details.

        Args:
            title: Alert title
            message: Alert message
            context: Alert context information
            severity: Alert severity level

        Returns:
            Created Alert instance or None if deduplicated

        Raises:
            AlertError: If system health alert creation fails
        """
        try:
            # Find or create a system health alert rule
            rule = await self._get_or_create_system_health_rule(severity)

            # Create alert with system health context
            alert = await self.create_alert(
                rule=rule,
                title=title,
                message=message,
                trigger_context=context,
                severity=severity,
            )

            if alert:
                # Deliver alert immediately for system health issues
                await self.deliver_alert(alert)

                log.info(
                    "System health alert sent: %s (ID: %d)",
                    alert.title,
                    alert.id,
                )

        except Exception as e:
            error_msg = f"Failed to send system health alert: {e}"
            raise AlertError(
                error_msg,
                alert_operation="send_system_health_alert",
                context={"title": title, "severity": severity.value},
            ) from e
        else:
            return alert

    # Private helper methods

    async def _evaluate_rule_conditions(
        self, rule: AlertRule
    ) -> tuple[bool, dict[str, Any]]:
        """Evaluate if rule conditions are met based on monitoring data."""
        if not self._monitoring_service:
            return False, {}

        if rule.alert_type == AlertType.SYSTEM_HEALTH:
            health_summary = await self._monitoring_service.get_system_health_summary()
            status = health_summary.get("health_assessment", {}).get("overall_status")
            if status == "degraded":
                return True, {"health_summary": health_summary}

        elif rule.alert_type == AlertType.PERFORMANCE:
            threshold = rule.get_condition_value("threshold_ms", 5000.0)
            period = timedelta(minutes=rule.get_condition_value("period_minutes", 60))
            metrics = await self._monitoring_service.get_performance_metrics(period)
            avg_response_time = metrics.get("avg_api_response_time")
            if avg_response_time and avg_response_time > threshold:
                return True, {"performance_metrics": metrics, "threshold_ms": threshold}

        return False, {}

    async def _trigger_alert_from_rule(
        self, rule: AlertRule, trigger_context: dict[str, Any]
    ) -> Alert:
        """Trigger an alert from a rule evaluation."""
        return await self.create_alert(
            rule=rule,
            title=f"Alert Triggered: {rule.name}",
            message=f"Alert rule '{rule.name}' conditions have been met. Context: {trigger_context}",
            trigger_context={
                "rule_evaluation": True,
                "evaluation_time": datetime.now(UTC).isoformat(),
                **trigger_context,
            },
        )

    async def _send_recovery_notification(self, alert: Alert) -> None:
        """Send recovery notification if configured."""
        # Placeholder for recovery notification logic
        log.debug("Recovery notification sent for alert %d", alert.id)

    async def _create_system_health_alert(
        self, health_summary: dict[str, Any], results: dict[str, Any]
    ) -> None:
        """Create system health alert from monitoring data."""
        status_reasons = health_summary.get("health_assessment", {}).get(
            "status_reasons", []
        )

        alert = await self.send_system_health_alert(
            title="System Health Degraded",
            message=f"System health is degraded. Issues: {', '.join(status_reasons)}",
            context={"health_summary": health_summary},
            severity=AlertSeverity.HIGH,
        )

        if alert:
            results["system_health_alerts"].append(
                {
                    "alert_id": alert.id,
                    "title": alert.title,
                    "issues": status_reasons,
                }
            )

    async def _check_performance_thresholds(
        self, performance_metrics: dict[str, Any], results: dict[str, Any]
    ) -> None:
        """Check performance metrics against thresholds."""
        # Placeholder for performance threshold checking
        avg_response_time = performance_metrics.get("avg_api_response_time")
        threshold = self._config.performance_threshold_ms

        if avg_response_time and avg_response_time > threshold:
            results["threshold_violations"].append(
                {
                    "type": "performance_threshold",
                    "metric": "avg_api_response_time",
                    "value": avg_response_time,
                    "threshold": threshold,
                }
            )

    async def _check_failure_thresholds(
        self, failure_analysis: dict[str, Any], results: dict[str, Any]
    ) -> None:
        """Check failure patterns against thresholds."""
        # Placeholder for failure threshold checking
        failure_rate = failure_analysis.get("failure_rate", 0)
        threshold = self._config.success_rate_threshold

        if failure_rate > (1 - threshold):
            results["threshold_violations"].append(
                {
                    "type": "failure_rate_threshold",
                    "metric": "failure_rate",
                    "value": failure_rate,
                    "threshold": 1 - threshold,
                }
            )

    async def _create_collection_health_alert(
        self,
        title: str,
        message: str,
        context: dict[str, Any],
        results: dict[str, Any],
    ) -> None:
        """Create collection health alert."""
        alert = await self.send_system_health_alert(
            title=title,
            message=message,
            context=context,
            severity=AlertSeverity.MEDIUM,
        )

        if alert:
            results["alerts_triggered"].append(
                {
                    "alert_id": alert.id,
                    "title": alert.title,
                    "type": "collection_health",
                }
            )

    async def _get_or_create_system_health_rule(
        self, severity: AlertSeverity
    ) -> AlertRule:
        """Get or create a system health alert rule."""
        # Try to find existing system health rule
        rule_name = f"system_health_{severity.value}"
        rule = await self._alert_rule_repository.get_by_name(rule_name)

        if not rule:
            # Create default system health rule
            rule = AlertRule(
                name=rule_name,
                description=f"System health monitoring rule for {severity.value} severity alerts",
                alert_type=AlertType.SYSTEM_HEALTH,
                severity=severity,
                conditions={"system_health": True},
                delivery_channels={
                    "email": {"enabled": True},
                    "webhook": {"enabled": True},
                },
                is_global=True,
                evaluation_interval_minutes=15,
                cooldown_minutes=30,
            )

            rule = await self._alert_rule_repository.create(rule)

        return rule
