"""
Unit tests for AlertService.

This module provides comprehensive unit tests for the AlertService class,
covering alert creation, deduplication, delivery, rule evaluation, monitoring
integration, and error handling scenarios.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.config.settings import AlertConfig
from app.exceptions.service_exceptions import AlertDeliveryError, AlertError
from app.models.alert import Alert
from app.models.alert_enums import (
    AlertDeliveryStatus,
    AlertSeverity,
    AlertType,
)
from app.models.alert_rule import AlertRule
from app.services.alert_service import AlertService


class TestAlertService:
    """Test suite for AlertService."""

    @pytest.fixture
    def mock_alert_repository(self) -> AsyncMock:
        """Create a mock alert repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_alert_rule_repository(self) -> AsyncMock:
        """Create a mock alert rule repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_database(self) -> AsyncMock:
        """Create a mock database."""
        mock_db = AsyncMock()
        # Mock session factory
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.session_factory.return_value = mock_session
        return mock_db

    @pytest.fixture
    def mock_monitoring_service(self) -> AsyncMock:
        """Create a mock monitoring service."""
        return AsyncMock()

    @pytest.fixture
    def alert_config(self) -> AlertConfig:
        """Create an alert configuration."""
        return AlertConfig(
            max_delivery_attempts=3,
            delivery_retry_delay_seconds=60,
            delivery_timeout_seconds=30,
            max_alerts_per_rule_per_hour=10,
        )

    @pytest.fixture
    def alert_service(
        self,
        mock_alert_repository: AsyncMock,
        mock_alert_rule_repository: AsyncMock,
        alert_config: AlertConfig,
        mock_monitoring_service: AsyncMock,
    ) -> AlertService:
        """Create an AlertService with mocked dependencies."""
        return AlertService(
            alert_repository=mock_alert_repository,
            alert_rule_repository=mock_alert_rule_repository,
            config=alert_config,
            monitoring_service=mock_monitoring_service,
        )

    @pytest.fixture
    def sample_alert_rule(self) -> AlertRule:
        """Create a sample alert rule for testing."""
        rule = AlertRule(
            id=1,
            name="test_rule",
            description="Test alert rule",
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.HIGH,
            conditions={"threshold": 0.8},
            delivery_channels={
                "email": {"recipients": ["test@example.com"], "enabled": True},
                "webhook": {"url": "https://example.com/webhook", "enabled": True},
            },
            is_global=True,
            evaluation_interval_minutes=15,
            cooldown_minutes=30,
        )
        # Mock the can_trigger_alert method
        rule.can_trigger_alert = MagicMock(return_value=True)
        return rule

    @pytest.fixture
    def sample_alert(self, sample_alert_rule: AlertRule) -> Alert:
        """Create a sample alert for testing."""
        return Alert(
            id=1,
            alert_rule_id=sample_alert_rule.id,
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            triggered_at=datetime.now(UTC),
            triggered_by="test_system",
            trigger_context={"test": "value"},
            correlation_key="test_correlation_key",
            delivery_status=AlertDeliveryStatus.PENDING,
        )

    # Alert Creation Tests

    @pytest.mark.asyncio
    async def test_create_alert_success(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
        mock_alert_repository: AsyncMock,
        mock_alert_rule_repository: AsyncMock,
    ) -> None:
        """Test successful alert creation."""
        # Mock deduplication check
        mock_alert_repository.get_alerts_by_correlation_key.return_value = []
        mock_alert_rule_repository.update_trigger_info.return_value = True

        # Create alert
        alert = await alert_service.create_alert(
            rule=sample_alert_rule,
            title="Test Alert",
            message="Test message",
            trigger_context={"test": "value"},
            area_code="DE",
        )

        # Verify alert properties
        assert alert is not None
        assert alert.alert_rule_id == sample_alert_rule.id
        assert alert.title == "Test Alert"
        assert alert.area_code == "DE"
        assert alert.correlation_key is not None

        # Verify repository calls
        mock_alert_rule_repository.update_trigger_info.assert_called_once_with(
            sample_alert_rule.id
        )

    @pytest.mark.asyncio
    async def test_create_alert_with_deduplication(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
        sample_alert: Alert,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test alert creation with deduplication."""
        # Mock existing similar alerts
        sample_alert.resolved_at = None  # Make it unresolved
        mock_alert_repository.get_alerts_by_correlation_key.return_value = [
            sample_alert
        ]

        # Create alert with same correlation key
        result = await alert_service.create_alert(
            rule=sample_alert_rule,
            title="Duplicate Alert",
            message="This should be deduplicated",
            trigger_context={"test": "dedup"},
            correlation_key="test_correlation_key",
        )

        # Should return existing alert due to deduplication
        assert result is not None
        assert result.id == sample_alert.id

    @pytest.mark.asyncio
    async def test_create_alert_generation_correlation_key(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test alert creation with automatic correlation key generation."""
        # Mock no existing alerts
        mock_alert_repository.get_alerts_by_correlation_key.return_value = []

        # Create alert without correlation key
        alert = await alert_service.create_alert(
            rule=sample_alert_rule,
            title="Auto Correlation Test",
            message="Testing auto-generated correlation key",
            trigger_context={"auto": "correlation"},
            area_code="FR",
            data_type="actual",
        )

        # Verify correlation key was generated
        assert alert.correlation_key is not None
        assert alert.correlation_key.startswith("system_health_")

    # Correlation and Deduplication Tests

    @pytest.mark.asyncio
    async def test_should_deduplicate_alert_with_unresolved(
        self,
        alert_service: AlertService,
        sample_alert: Alert,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test deduplication when unresolved alerts exist."""
        # Mock unresolved alert
        sample_alert.resolved_at = None
        mock_alert_repository.get_alerts_by_correlation_key.return_value = [
            sample_alert
        ]

        result = await alert_service.should_deduplicate_alert("test_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_should_deduplicate_alert_with_resolved(
        self,
        alert_service: AlertService,
        sample_alert: Alert,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test no deduplication when only resolved alerts exist."""
        # Mock resolved alert
        sample_alert.resolved_at = datetime.now(UTC)
        mock_alert_repository.get_alerts_by_correlation_key.return_value = [
            sample_alert
        ]

        result = await alert_service.should_deduplicate_alert("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_find_similar_alerts_within_window(
        self,
        alert_service: AlertService,
        sample_alert: Alert,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test finding similar alerts within time window."""
        # Set alert time within window
        sample_alert.triggered_at = datetime.now(UTC) - timedelta(minutes=30)
        mock_alert_repository.get_alerts_by_correlation_key.return_value = [
            sample_alert
        ]

        result = await alert_service.find_similar_alerts("test_key", 60)

        assert len(result) == 1
        assert result[0].id == sample_alert.id

    @pytest.mark.asyncio
    async def test_find_similar_alerts_outside_window(
        self,
        alert_service: AlertService,
        sample_alert: Alert,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test excluding alerts outside time window."""
        # Set alert time outside window
        sample_alert.triggered_at = datetime.now(UTC) - timedelta(hours=2)
        mock_alert_repository.get_alerts_by_correlation_key.return_value = [
            sample_alert
        ]

        result = await alert_service.find_similar_alerts("test_key", 60)

        assert len(result) == 0

    # Alert Resolution Tests

    @pytest.mark.asyncio
    async def test_resolve_alert_success(
        self,
        alert_service: AlertService,
        sample_alert: Alert,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test successful alert resolution."""
        # Mock resolved alert
        resolved_alert = Alert(
            id=sample_alert.id,
            alert_rule_id=sample_alert.alert_rule_id,
            alert_type=sample_alert.alert_type,
            severity=sample_alert.severity,
            title=sample_alert.title,
            message=sample_alert.message,
            triggered_at=sample_alert.triggered_at,
            triggered_by=sample_alert.triggered_by,
            trigger_context=sample_alert.trigger_context,
            resolved_at=datetime.now(UTC),
            resolved_by="test_user",
            resolution_notes="Test resolution",
        )
        mock_alert_repository.mark_alert_resolved.return_value = resolved_alert

        result = await alert_service.resolve_alert(
            alert_id=1,
            resolved_by="test_user",
            notes="Test resolution",
        )

        assert result is not None
        assert result.resolved_by == "test_user"
        assert result.resolution_notes == "Test resolution"
        mock_alert_repository.mark_alert_resolved.assert_called_once_with(
            alert_id=1,
            resolved_by="test_user",
            notes="Test resolution",
        )

    @pytest.mark.asyncio
    async def test_resolve_alert_not_found(
        self,
        alert_service: AlertService,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test resolving non-existent alert."""
        mock_alert_repository.mark_alert_resolved.return_value = None

        result = await alert_service.resolve_alert(
            alert_id=99999,
            resolved_by="test_user",
        )

        assert result is None

    # Alert Retrieval Tests

    @pytest.mark.asyncio
    async def test_get_active_alerts_basic(
        self,
        alert_service: AlertService,
        sample_alert: Alert,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test basic active alerts retrieval."""
        mock_alert_repository.get_unresolved_alerts.return_value = [sample_alert]

        result = await alert_service.get_active_alerts()

        assert len(result) == 1
        assert result[0].id == sample_alert.id

    @pytest.mark.asyncio
    async def test_get_active_alerts_with_filters(
        self,
        alert_service: AlertService,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test active alerts retrieval with filters."""
        # Create multiple alerts with different properties
        alert1 = Alert(
            id=1,
            alert_rule_id=1,
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.HIGH,
            title="High Alert",
            message="High severity",
            triggered_at=datetime.now(UTC),
            triggered_by="test",
            trigger_context={},
            area_code="DE",
        )
        alert2 = Alert(
            id=2,
            alert_rule_id=1,
            alert_type=AlertType.DATA_QUALITY,
            severity=AlertSeverity.MEDIUM,
            title="Medium Alert",
            message="Medium severity",
            triggered_at=datetime.now(UTC),
            triggered_by="test",
            trigger_context={},
            area_code="FR",
        )

        mock_alert_repository.get_unresolved_alerts.return_value = [alert1, alert2]

        # Test severity filter
        result = await alert_service.get_active_alerts(severity=AlertSeverity.HIGH)
        assert len(result) == 1
        assert result[0].severity == AlertSeverity.HIGH

        # Test area filter
        result = await alert_service.get_active_alerts(area_code="DE")
        assert len(result) == 1
        assert result[0].area_code == "DE"

        # Test limit
        result = await alert_service.get_active_alerts(limit=1)
        assert len(result) == 1

    # Alert Delivery Tests

    @pytest.mark.asyncio
    async def test_deliver_alert_success(
        self,
        alert_service: AlertService,
        sample_alert: Alert,
        sample_alert_rule: AlertRule,
        mock_alert_repository: AsyncMock,
        mock_alert_rule_repository: AsyncMock,
    ) -> None:
        """Test successful alert delivery."""
        mock_alert_rule_repository.get_by_id.return_value = sample_alert_rule
        mock_alert_repository.update_delivery_status.return_value = sample_alert

        # Mock email and webhook delivery methods
        with (
            patch.object(
                alert_service, "deliver_email", return_value={"success": True}
            ),
            patch.object(
                alert_service, "deliver_webhook", return_value={"success": True}
            ),
        ):
            result = await alert_service.deliver_alert(sample_alert)

        assert result["alert_id"] == sample_alert.id
        assert "email" in result["channels_attempted"]
        assert "webhook" in result["channels_attempted"]
        assert result["overall_status"] == "success"

    @pytest.mark.asyncio
    async def test_deliver_alert_partial_failure(
        self,
        alert_service: AlertService,
        sample_alert: Alert,
        sample_alert_rule: AlertRule,
        mock_alert_repository: AsyncMock,
        mock_alert_rule_repository: AsyncMock,
    ) -> None:
        """Test alert delivery with partial failure."""
        mock_alert_rule_repository.get_by_id.return_value = sample_alert_rule
        mock_alert_repository.update_delivery_status.return_value = sample_alert

        # Mock one success, one failure
        with (
            patch.object(
                alert_service, "deliver_email", return_value={"success": True}
            ),
            patch.object(
                alert_service, "deliver_webhook", return_value={"success": False}
            ),
        ):
            result = await alert_service.deliver_alert(sample_alert)

        assert result["overall_status"] == "partial"
        assert len(result["successful_deliveries"]) == 1
        assert len(result["failed_deliveries"]) == 1

    @pytest.mark.asyncio
    async def test_deliver_alert_rule_not_found(
        self,
        alert_service: AlertService,
        sample_alert: Alert,
        mock_alert_rule_repository: AsyncMock,
    ) -> None:
        """Test alert delivery when rule is not found."""
        mock_alert_rule_repository.get_by_id.return_value = None

        with pytest.raises(AlertError) as exc_info:
            await alert_service.deliver_alert(sample_alert)

        assert "Alert rule" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_deliver_email_failure(
        self,
        alert_service: AlertService,
        sample_alert: Alert,
        sample_alert_rule: AlertRule,
    ) -> None:
        """Test email delivery failure raises AlertDeliveryError."""
        with patch("app.services.alert_service.datetime") as mock_datetime:
            mock_datetime.now.side_effect = Exception("Test SMTP error")
            with pytest.raises(AlertDeliveryError) as exc_info:
                await alert_service.deliver_email(sample_alert, sample_alert_rule)

            assert "Email delivery failed" in str(exc_info.value)
            assert exc_info.value.delivery_channel == "email"

    @pytest.mark.asyncio
    async def test_deliver_webhook_failure(
        self,
        alert_service: AlertService,
        sample_alert: Alert,
        sample_alert_rule: AlertRule,
    ) -> None:
        """Test webhook delivery failure raises AlertDeliveryError."""
        with patch("app.services.alert_service.datetime") as mock_datetime:
            mock_datetime.now.side_effect = Exception("Test HTTP error")
            with pytest.raises(AlertDeliveryError) as exc_info:
                await alert_service.deliver_webhook(sample_alert, sample_alert_rule)

            assert "Webhook delivery failed" in str(exc_info.value)
            assert exc_info.value.delivery_channel == "webhook"

    # Rule Evaluation Tests

    @pytest.mark.asyncio
    async def test_evaluate_alert_rules_success(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
        mock_alert_rule_repository: AsyncMock,
    ) -> None:
        """Test successful alert rule evaluation."""
        mock_alert_rule_repository.get_rules_for_evaluation.return_value = [
            sample_alert_rule
        ]

        result = await alert_service.evaluate_alert_rules()

        assert "total_rules_evaluated" in result
        assert result["total_rules_evaluated"] == 1
        assert "alerts_triggered" in result
        assert "rules_skipped_cooldown" in result

    @pytest.mark.asyncio
    async def test_evaluate_alert_rules_with_cooldown(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
        mock_alert_rule_repository: AsyncMock,
    ) -> None:
        """Test rule evaluation with cooldown skipping."""
        # Mock rule in cooldown
        sample_alert_rule.can_trigger_alert = MagicMock(return_value=False)
        sample_alert_rule.is_cooldown_active = True
        sample_alert_rule.is_rate_limited = False

        mock_alert_rule_repository.get_rules_for_evaluation.return_value = [
            sample_alert_rule
        ]

        result = await alert_service.evaluate_alert_rules()

        assert result["rules_skipped_cooldown"] == 1
        assert result["alerts_triggered"] == 0

    # Monitoring Integration Tests

    @pytest.mark.asyncio
    async def test_evaluate_monitoring_conditions_with_service(
        self,
        alert_service: AlertService,
        mock_monitoring_service: AsyncMock,
    ) -> None:
        """Test monitoring condition evaluation with service available."""
        # Mock monitoring service responses
        mock_monitoring_service.get_system_health_summary.return_value = {
            "health_assessment": {"overall_status": "healthy"}
        }
        mock_monitoring_service.get_performance_metrics.return_value = {
            "avg_api_response_time": 2000.0
        }
        mock_monitoring_service.analyze_failure_patterns.return_value = {
            "failure_rate": 0.05
        }

        result = await alert_service.evaluate_monitoring_conditions()

        assert result["monitoring_service_available"] is True
        assert "threshold_violations" in result
        assert "system_health_alerts" in result

    @pytest.mark.asyncio
    async def test_evaluate_monitoring_conditions_without_service(
        self,
        mock_alert_repository: AsyncMock,
        mock_alert_rule_repository: AsyncMock,
        alert_config: AlertConfig,
    ) -> None:
        """Test monitoring condition evaluation without service."""
        # Create service without monitoring service
        alert_service = AlertService(
            alert_repository=mock_alert_repository,
            alert_rule_repository=mock_alert_rule_repository,
            config=alert_config,
            monitoring_service=None,
        )

        result = await alert_service.evaluate_monitoring_conditions()

        assert result["monitoring_service_available"] is False

    @pytest.mark.asyncio
    async def test_send_system_health_alert(
        self,
        alert_service: AlertService,
        mock_alert_rule_repository: AsyncMock,
    ) -> None:
        """Test system health alert sending."""
        # Mock rule creation/retrieval
        system_rule = AlertRule(
            id=2,
            name="system_health_high",
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.HIGH,
            conditions={"system_health": True},
            delivery_channels={"email": {"enabled": True}},
        )
        mock_alert_rule_repository.get_by_name.return_value = system_rule

        # Mock delivery
        with patch.object(alert_service, "deliver_alert", return_value={}):
            result = await alert_service.send_system_health_alert(
                title="Test System Alert",
                message="Test system health message",
                context={"test": "context"},
                severity=AlertSeverity.HIGH,
            )

        assert result is not None
        assert result.alert_type == AlertType.SYSTEM_HEALTH
        assert result.severity == AlertSeverity.HIGH

    # Retry Mechanism Tests

    @pytest.mark.asyncio
    async def test_retry_failed_deliveries(
        self,
        alert_service: AlertService,
        sample_alert: Alert,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test retry mechanism for failed deliveries."""
        mock_alert_repository.get_delivery_retry_candidates.return_value = [
            sample_alert
        ]

        # Mock successful retry
        with patch.object(
            alert_service,
            "deliver_alert",
            return_value={"overall_status": "success"},
        ):
            result = await alert_service.retry_failed_deliveries()

        assert "candidates_found" in result
        assert "retry_attempts" in result
        assert "successful_retries" in result

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_create_alert_exception_handling(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
        mock_database: AsyncMock,
    ) -> None:
        """Test error handling in alert creation."""
        # Mock database session to raise exception
        mock_session = mock_database.session_factory.return_value
        mock_session.commit.side_effect = Exception("Database error")

        with pytest.raises(AlertError) as exc_info:
            await alert_service.create_alert(
                rule=sample_alert_rule,
                title="Error Test",
                message="Testing error handling",
                trigger_context={"test": "error"},
            )

        assert "Failed to create alert" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_similar_alerts_exception_handling(
        self,
        alert_service: AlertService,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test error handling in finding similar alerts."""
        mock_alert_repository.get_alerts_by_correlation_key.side_effect = Exception(
            "Repository error"
        )

        with pytest.raises(AlertError) as exc_info:
            await alert_service.find_similar_alerts("test_key")

        assert "Failed to find similar alerts" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_monitoring_evaluation_exception_handling(
        self,
        alert_service: AlertService,
        mock_monitoring_service: AsyncMock,
    ) -> None:
        """Test error handling in monitoring evaluation."""
        mock_monitoring_service.get_system_health_summary.side_effect = Exception(
            "Monitoring error"
        )

        with pytest.raises(AlertError) as exc_info:
            await alert_service.evaluate_monitoring_conditions()

        assert "Failed to evaluate monitoring conditions" in str(exc_info.value)


class TestAlertServiceHelperMethods:
    """Test helper methods of AlertService."""

    @pytest.fixture
    def alert_service(self) -> AlertService:
        """Create a minimal AlertService for testing helper methods."""
        return AlertService(
            alert_repository=AsyncMock(),
            alert_rule_repository=AsyncMock(),
            database=AsyncMock(),
            config=AlertConfig(),
            monitoring_service=None,
        )

    def test_generate_correlation_key_data_quality(
        self, alert_service: AlertService
    ) -> None:
        """Test correlation key generation for data quality alerts."""
        key = alert_service.generate_correlation_key(
            alert_type=AlertType.DATA_QUALITY,
            trigger_context={"quality_issue": "validation_failed"},
        )

        assert key.startswith("data_quality_")

    def test_generate_correlation_key_collection_failure(
        self, alert_service: AlertService
    ) -> None:
        """Test correlation key generation for collection failure alerts."""
        key = alert_service.generate_correlation_key(
            alert_type=AlertType.COLLECTION_FAILURE,
            area_code="DE",
            trigger_context={"api_error": "timeout"},
        )

        assert key.startswith("collection_failure_")

    def test_generate_correlation_key_consistent(
        self, alert_service: AlertService
    ) -> None:
        """Test that correlation key generation is consistent."""
        key1 = alert_service.generate_correlation_key(
            alert_type=AlertType.SYSTEM_HEALTH,
            area_code="DE",
            data_type="actual",
        )

        key2 = alert_service.generate_correlation_key(
            alert_type=AlertType.SYSTEM_HEALTH,
            area_code="DE",
            data_type="actual",
        )

        assert key1 == key2  # Same inputs should generate same key
