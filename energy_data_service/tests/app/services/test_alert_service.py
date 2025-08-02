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
        mock_alert_repository.find_unresolved_similar_alert.return_value = None
        mock_alert_rule_repository.update_trigger_info.return_value = True
        mock_alert_repository.create.side_effect = lambda alert: alert

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
        mock_alert_repository.create.assert_called_once()
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
        mock_alert_repository.find_unresolved_similar_alert.return_value = sample_alert

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
        mock_alert_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_alert_generation_correlation_key(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test alert creation with automatic correlation key generation."""
        # Mock no existing alerts
        mock_alert_repository.find_unresolved_similar_alert.return_value = None
        mock_alert_repository.create.side_effect = lambda alert: alert

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
        mock_alert_repository.find_unresolved_similar_alert.return_value = sample_alert

        result = await alert_service.should_deduplicate_alert("test_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_should_deduplicate_alert_with_resolved(
        self,
        alert_service: AlertService,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test no deduplication when only resolved alerts exist."""
        mock_alert_repository.find_unresolved_similar_alert.return_value = None

        result = await alert_service.should_deduplicate_alert("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_find_similar_alerts(
        self,
        alert_service: AlertService,
        sample_alert: Alert,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test finding similar alerts within time window."""
        mock_alert_repository.find_unresolved_similar_alert.return_value = sample_alert

        result = await alert_service.find_similar_alerts("test_key", 60)

        assert result is not None
        assert result.id == sample_alert.id
        mock_alert_repository.find_unresolved_similar_alert.assert_called_once()

    # Alert Resolution Tests

    @pytest.mark.asyncio
    async def test_resolve_alert_success(
        self,
        alert_service: AlertService,
        sample_alert: Alert,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test successful alert resolution."""
        resolved_alert = sample_alert
        resolved_alert.resolved_at = datetime.now(UTC)
        resolved_alert.resolved_by = "test_user"
        resolved_alert.resolution_notes = "Test resolution"
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
    async def test_get_active_alerts_with_filters(
        self,
        alert_service: AlertService,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test active alerts retrieval with filters."""
        await alert_service.get_active_alerts(
            severity=AlertSeverity.HIGH, area_code="DE", limit=10
        )

        mock_alert_repository.get_unresolved_alerts.assert_called_once_with(
            severity=AlertSeverity.HIGH,
            alert_type=None,
            area_code="DE",
            limit=10,
        )

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

    # Rule Evaluation Tests

    @pytest.mark.asyncio
    async def test_evaluate_rule_conditions_system_health_degraded_triggers_alert(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
        mock_monitoring_service: AsyncMock,
    ) -> None:
        """Test that a degraded system health status triggers a SYSTEM_HEALTH alert."""
        sample_alert_rule.alert_type = AlertType.SYSTEM_HEALTH
        mock_monitoring_service.get_system_health_summary.return_value = {
            "health_assessment": {"overall_status": "degraded"}
        }

        should_trigger, context = await alert_service._evaluate_rule_conditions(
            sample_alert_rule
        )

        assert should_trigger is True
        assert "health_summary" in context

    @pytest.mark.asyncio
    async def test_evaluate_rule_conditions_system_health_healthy_no_trigger(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
        mock_monitoring_service: AsyncMock,
    ) -> None:
        """Test that a healthy system status does not trigger a SYSTEM_HEALTH alert."""
        sample_alert_rule.alert_type = AlertType.SYSTEM_HEALTH
        mock_monitoring_service.get_system_health_summary.return_value = {
            "health_assessment": {"overall_status": "healthy"}
        }

        should_trigger, _ = await alert_service._evaluate_rule_conditions(
            sample_alert_rule
        )

        assert should_trigger is False

    @pytest.mark.asyncio
    async def test_evaluate_rule_conditions_performance_threshold_exceeded_triggers_alert(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
        mock_monitoring_service: AsyncMock,
    ) -> None:
        """Test that exceeding a performance threshold triggers a PERFORMANCE alert."""
        sample_alert_rule.alert_type = AlertType.PERFORMANCE
        sample_alert_rule.conditions = {"threshold_ms": 5000.0}
        mock_monitoring_service.get_performance_metrics.return_value = {
            "avg_api_response_time": 6000.0
        }

        should_trigger, context = await alert_service._evaluate_rule_conditions(
            sample_alert_rule
        )

        assert should_trigger is True
        assert "performance_metrics" in context

    @pytest.mark.asyncio
    async def test_evaluate_rule_conditions_performance_threshold_ok_no_trigger(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
        mock_monitoring_service: AsyncMock,
    ) -> None:
        """Test that meeting a performance threshold does not trigger a PERFORMANCE alert."""
        sample_alert_rule.alert_type = AlertType.PERFORMANCE
        sample_alert_rule.conditions = {"threshold_ms": 5000.0}
        mock_monitoring_service.get_performance_metrics.return_value = {
            "avg_api_response_time": 4000.0
        }

        should_trigger, _ = await alert_service._evaluate_rule_conditions(
            sample_alert_rule
        )

        assert should_trigger is False

    @pytest.mark.asyncio
    async def test_evaluate_rule_conditions_unsupported_type_no_trigger(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
    ) -> None:
        """Test that an unsupported alert type does not trigger."""
        sample_alert_rule.alert_type = AlertType.DATA_QUALITY  # Not yet implemented

        should_trigger, _ = await alert_service._evaluate_rule_conditions(
            sample_alert_rule
        )

        assert should_trigger is False

    # Other Tests

    @pytest.mark.asyncio
    async def test_send_system_health_alert(
        self,
        alert_service: AlertService,
        mock_alert_rule_repository: AsyncMock,
        mock_alert_repository: AsyncMock,
    ) -> None:
        """Test system health alert sending."""
        system_rule = AlertRule(
            id=2,
            name="system_health_high",
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.HIGH,
            conditions={"system_health": True},
            delivery_channels={"email": {"enabled": True}},
        )
        mock_alert_rule_repository.get_by_name.return_value = system_rule
        mock_alert_repository.find_unresolved_similar_alert.return_value = None
        mock_alert_repository.create.side_effect = lambda alert: alert

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
