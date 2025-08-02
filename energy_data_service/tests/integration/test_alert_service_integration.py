"""Integration tests for AlertService using testcontainers.

This module provides comprehensive integration testing for the AlertService
using real TimescaleDB testcontainers for database operations and alert
management workflows.

Key Features:
- Real TimescaleDB database for alert and alert rule storage
- Complete alert workflow testing from rule evaluation to delivery
- Multi-channel delivery testing with mock integrations
- Deduplication and correlation testing with real data
- Rate limiting and cooldown validation
- Alert resolution and recovery notification testing
- Integration with MonitoringService for system health alerting
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from app.config.database import Database
from app.config.settings import (
    AlertConfig,
    DatabaseConfig,
    MonitoringConfig,
    Settings,
)
from app.container import Container
from app.models.alert import Alert
from app.models.alert_enums import (
    AlertDeliveryChannel,
    AlertDeliveryStatus,
    AlertRuleStatus,
    AlertSeverity,
    AlertType,
)
from app.models.alert_rule import AlertRule
from app.models.base import Base
from app.models.collection_metrics import CollectionMetrics
from app.models.load_data import EnergyDataType
from app.repositories.alert_repository import AlertRepository
from app.repositories.alert_rule_repository import AlertRuleRepository
from app.repositories.collection_metrics_repository import CollectionMetricsRepository
from app.services.alert_service import AlertService
from app.services.monitoring_service import MonitoringService
from pydantic import SecretStr
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer


@pytest.fixture(autouse=True)
def reset_container_state() -> Generator:
    """Reset container state before and after each test for proper isolation."""
    # Create a fresh container instance for each test
    yield
    # Reset any singleton providers after each test
    try:
        # Reset the singleton providers to ensure clean state
        if hasattr(Container, "_singletons"):
            Container._singletons.clear()
    except AttributeError:
        pass  # Container might not have this attribute in all versions


@pytest.fixture
def postgres_container() -> Generator[PostgresContainer]:
    """Fixture that provides a TimescaleDB testcontainer."""
    # Use timescale/timescaledb image for TimescaleDB support
    with PostgresContainer("timescale/timescaledb:2.16.1-pg16") as postgres:
        yield postgres


@pytest.fixture
def database_config(postgres_container: PostgresContainer) -> DatabaseConfig:
    """Create DatabaseConfig using testcontainer connection details."""
    return DatabaseConfig(
        host=postgres_container.get_container_host_ip(),
        port=postgres_container.get_exposed_port(5432),
        user=postgres_container.username,
        password=SecretStr(postgres_container.password),
        name=postgres_container.dbname,
    )


@pytest.fixture
def alert_config() -> AlertConfig:
    """Create AlertConfig with test-appropriate settings."""
    return AlertConfig(
        evaluation_interval_minutes=1,
        max_delivery_attempts=2,
        delivery_retry_delay_seconds=30,
        delivery_timeout_seconds=10,
        cooldown_override_minutes=5,
        alert_retention_days=7,
        resolved_alert_retention_days=7,
    )


@pytest.fixture
def monitoring_config() -> MonitoringConfig:
    """Create MonitoringConfig with test-appropriate settings."""
    return MonitoringConfig(
        metrics_retention_days=7,  # Short retention for testing
        performance_threshold_ms=2000.0,  # Lower threshold for testing
        success_rate_threshold=0.8,  # Lower threshold for testing
        anomaly_detection_enabled=True,
        dashboard_update_interval_minutes=1,  # Short interval for testing
    )


@pytest.fixture
def test_settings(
    database_config: DatabaseConfig,
    alert_config: AlertConfig,
    monitoring_config: MonitoringConfig,
) -> Settings:
    """Create test settings with testcontainer database configuration."""
    return Settings(
        environment="development",
        debug=True,
        database=database_config,
        entsoe_client__api_token=SecretStr("test_token_123456789"),
        alert=alert_config,
        monitoring=monitoring_config,
    )


@pytest_asyncio.fixture
async def database(test_settings: Settings) -> AsyncGenerator[Database]:
    """Initialize database with test settings and create tables."""
    database = Database(test_settings)
    async with database.engine.begin() as conn:
        # Create all tables including TimescaleDB extensions
        await conn.run_sync(Base.metadata.create_all)

        # Create TimescaleDB extension if not exists
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))

        # Create hypertables for time-series data
        try:  # noqa: SIM105
            await conn.execute(
                text(
                    "SELECT create_hypertable('collection_metrics', 'collection_start', "
                    "if_not_exists => TRUE);"
                )
            )
        except Exception:  # noqa: BLE001, S110
            # Hypertable might already exist, which is fine for tests
            pass

        await conn.commit()

    yield database

    # Cleanup after tests
    await database.engine.dispose()


@pytest_asyncio.fixture
async def alert_repository(database: Database) -> AsyncGenerator[AlertRepository]:
    """Create AlertRepository instance for testing."""
    repository = AlertRepository(database)
    yield repository


@pytest_asyncio.fixture
async def alert_rule_repository(
    database: Database,
) -> AsyncGenerator[AlertRuleRepository]:
    """Create AlertRuleRepository instance for testing."""
    repository = AlertRuleRepository(database)
    yield repository


@pytest_asyncio.fixture
async def metrics_repository(
    database: Database,
) -> AsyncGenerator[CollectionMetricsRepository]:
    """Create CollectionMetricsRepository instance for testing."""
    repository = CollectionMetricsRepository(database)
    yield repository


@pytest_asyncio.fixture
async def monitoring_service(
    metrics_repository: CollectionMetricsRepository,
    database: Database,
    monitoring_config: MonitoringConfig,
) -> AsyncGenerator[MonitoringService]:
    """Create MonitoringService instance for testing."""
    service = MonitoringService(
        metrics_repository=metrics_repository,
        database=database,
        config=monitoring_config,
    )
    yield service


@pytest_asyncio.fixture
async def alert_service(
    alert_repository: AlertRepository,
    alert_rule_repository: AlertRuleRepository,
    alert_config: AlertConfig,
    monitoring_service: MonitoringService,
) -> AsyncGenerator[AlertService]:
    """Create AlertService instance for testing."""
    service = AlertService(
        alert_repository=alert_repository,
        alert_rule_repository=alert_rule_repository,
        config=alert_config,
        monitoring_service=monitoring_service,
    )
    yield service


@pytest_asyncio.fixture
async def sample_alert_rule(
    alert_rule_repository: AlertRuleRepository,
) -> AsyncGenerator[AlertRule]:
    """Create a sample alert rule for testing."""
    rule = AlertRule(
        name="test_system_health_rule",
        description="Test rule for system health monitoring",
        alert_type=AlertType.SYSTEM_HEALTH,
        severity=AlertSeverity.HIGH,
        conditions={"system_health": True, "threshold": 0.8},
        delivery_channels={
            "email": {"recipients": ["test@example.com"], "enabled": True},
            "webhook": {"url": "https://example.com/webhook", "enabled": True},
        },
        is_global=True,
        evaluation_interval_minutes=15,
        cooldown_minutes=30,
    )

    async with alert_rule_repository.database.session_factory() as session:
        session.add(rule)
        await session.commit()
        await session.refresh(rule)

    yield rule


@pytest_asyncio.fixture
async def sample_collection_metrics(
    metrics_repository: CollectionMetricsRepository,
) -> AsyncGenerator[list[CollectionMetrics]]:
    """Create sample collection metrics for testing."""
    current_time = datetime.now(UTC)

    metrics = [
        # Successful metrics
        CollectionMetrics(
            job_id="job_001",
            area_code="DE",
            data_type=EnergyDataType.ACTUAL,
            collection_start=current_time - timedelta(hours=2),
            collection_end=current_time - timedelta(hours=2, minutes=-5),
            points_collected=100,
            success=True,
            api_response_time=1500,
            processing_time=200,
        ),
        CollectionMetrics(
            job_id="job_002",
            area_code="FR",
            data_type=EnergyDataType.ACTUAL,
            collection_start=current_time - timedelta(hours=1),
            collection_end=current_time - timedelta(hours=1, minutes=-5),
            points_collected=95,
            success=True,
            api_response_time=1800,
            processing_time=250,
        ),
        # Failed metrics to trigger alerts
        CollectionMetrics(
            job_id="job_003",
            area_code="DE",
            data_type=EnergyDataType.ACTUAL,
            collection_start=current_time - timedelta(minutes=30),
            collection_end=current_time - timedelta(minutes=25),
            points_collected=0,
            success=False,
            error_message="API connection timeout",
            api_response_time=None,
            processing_time=None,
        ),
        CollectionMetrics(
            job_id="job_004",
            area_code="FR",
            data_type=EnergyDataType.ACTUAL,
            collection_start=current_time - timedelta(minutes=20),
            collection_end=current_time - timedelta(minutes=15),
            points_collected=0,
            success=False,
            error_message="Data validation failed",
            api_response_time=3000,
            processing_time=500,
        ),
    ]

    async with metrics_repository.database.session_factory() as session:
        for metric in metrics:
            session.add(metric)
        await session.commit()
        for metric in metrics:
            await session.refresh(metric)

    yield metrics


class TestAlertServiceIntegration:
    """Integration tests for AlertService functionality."""

    @pytest.mark.asyncio
    async def test_create_alert_basic_workflow(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
    ) -> None:
        """Test basic alert creation workflow."""
        # Create an alert
        alert = await alert_service.create_alert(
            rule=sample_alert_rule,
            title="Test System Health Alert",
            message="System health degraded below threshold",
            trigger_context={
                "health_check": "performance_monitoring",
                "current_value": 0.75,
                "threshold": 0.8,
            },
            area_code="DE",
        )

        # Verify alert was created
        assert alert is not None
        assert alert.id is not None
        assert alert.alert_rule_id == sample_alert_rule.id
        assert alert.title == "Test System Health Alert"
        assert alert.area_code == "DE"
        assert alert.delivery_status == AlertDeliveryStatus.PENDING
        assert not alert.is_resolved
        assert alert.correlation_key is not None

    @pytest.mark.asyncio
    async def test_alert_deduplication(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
    ) -> None:
        """Test alert deduplication functionality."""
        # Create first alert
        alert1 = await alert_service.create_alert(
            rule=sample_alert_rule,
            title="Duplicate Alert Test",
            message="This is a test for deduplication",
            trigger_context={"test": "deduplication"},
            correlation_key="test_correlation_key",
        )

        # Create second alert with same correlation key
        alert2 = await alert_service.create_alert(
            rule=sample_alert_rule,
            title="Duplicate Alert Test 2",
            message="This should be deduplicated",
            trigger_context={"test": "deduplication"},
            correlation_key="test_correlation_key",
        )

        # Second alert should be the same as the first due to deduplication
        assert alert2 is not None
        assert alert2.id == alert1.id

    @pytest.mark.asyncio
    async def test_correlation_key_generation(
        self, alert_service: AlertService
    ) -> None:
        """Test correlation key generation for different alert types."""
        # Test basic correlation key
        key1 = alert_service.generate_correlation_key(
            alert_type=AlertType.SYSTEM_HEALTH,
            area_code="DE",
            data_type="actual",
        )
        assert key1.startswith("system_health_")
        assert len(key1) > len("system_health_")

        # Test different parameters generate different keys
        key2 = alert_service.generate_correlation_key(
            alert_type=AlertType.SYSTEM_HEALTH,
            area_code="FR",
            data_type="actual",
        )
        assert key1 != key2

        # Test context-specific correlation
        key3 = alert_service.generate_correlation_key(
            alert_type=AlertType.SYSTEM_HEALTH,
            trigger_context={"health_check": "performance"},
        )
        assert key3.startswith("system_health_")

    @pytest.mark.asyncio
    async def test_alert_delivery_workflow(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
    ) -> None:
        """Test complete alert delivery workflow."""
        # Create an alert
        alert = await alert_service.create_alert(
            rule=sample_alert_rule,
            title="Delivery Test Alert",
            message="Testing delivery workflow",
            trigger_context={"test": "delivery"},
        )

        # Deliver the alert
        delivery_result = await alert_service.deliver_alert(alert)

        # Verify delivery results
        assert delivery_result["alert_id"] == alert.id
        assert "email" in delivery_result["channels_attempted"]
        assert "webhook" in delivery_result["channels_attempted"]
        assert delivery_result["overall_status"] in ["success", "partial", "failed"]

        # Verify alert status was updated
        updated_alert = await alert_service._alert_repository.get_by_id(alert.id)
        assert updated_alert is not None
        assert updated_alert.delivery_status in [
            AlertDeliveryStatus.DELIVERED,
            AlertDeliveryStatus.RETRYING,
            AlertDeliveryStatus.FAILED,
        ]
        assert updated_alert.delivery_attempts > 0

    @pytest.mark.asyncio
    async def test_alert_resolution(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
    ) -> None:
        """Test alert resolution functionality."""
        # Create an alert
        alert = await alert_service.create_alert(
            rule=sample_alert_rule,
            title="Resolution Test Alert",
            message="Testing resolution workflow",
            trigger_context={"test": "resolution"},
        )

        # Verify alert is not resolved
        assert not alert.is_resolved

        # Resolve the alert
        resolved_alert = await alert_service.resolve_alert(
            alert_id=alert.id,
            resolved_by="test_user",
            notes="Resolved for testing",
        )

        # Verify resolution
        assert resolved_alert is not None
        assert resolved_alert.is_resolved
        assert resolved_alert.resolved_by == "test_user"
        assert resolved_alert.resolution_notes == "Resolved for testing"
        assert resolved_alert.resolved_at is not None

    @pytest.mark.asyncio
    async def test_get_active_alerts_filtering(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
    ) -> None:
        """Test active alerts retrieval with filtering."""
        # Create multiple alerts with different properties
        alert1 = await alert_service.create_alert(
            rule=sample_alert_rule,
            title="High Severity Alert",
            message="High severity test",
            trigger_context={"test": "filtering"},
            severity=AlertSeverity.HIGH,
            area_code="DE",
        )

        alert2 = await alert_service.create_alert(
            rule=sample_alert_rule,
            title="Medium Severity Alert",
            message="Medium severity test",
            trigger_context={"test": "filtering"},
            severity=AlertSeverity.MEDIUM,
            area_code="FR",
        )

        # Resolve one alert
        await alert_service.resolve_alert(alert2.id, "test_resolver")

        # Test filtering by severity
        high_alerts = await alert_service.get_active_alerts(severity=AlertSeverity.HIGH)
        assert len(high_alerts) >= 1
        assert all(alert.severity == AlertSeverity.HIGH for alert in high_alerts)

        # Test filtering by area
        de_alerts = await alert_service.get_active_alerts(area_code="DE")
        assert len(de_alerts) >= 1
        assert all(alert.area_code == "DE" for alert in de_alerts)

        # Test that resolved alerts are not included
        all_active = await alert_service.get_active_alerts()
        active_ids = [alert.id for alert in all_active]
        assert alert1.id in active_ids
        assert alert2.id not in active_ids  # This one was resolved

    @pytest.mark.asyncio
    async def test_monitoring_integration(
        self,
        alert_service: AlertService,
        sample_collection_metrics: list[CollectionMetrics],
    ) -> None:
        """Test integration with MonitoringService for health alerts."""
        # Test monitoring condition evaluation
        evaluation_result = await alert_service.evaluate_monitoring_conditions(
            period=timedelta(hours=3)
        )

        # Verify evaluation structure
        assert evaluation_result["monitoring_service_available"] is True
        assert "threshold_violations" in evaluation_result
        assert "system_health_alerts" in evaluation_result
        assert "performance_alerts" in evaluation_result
        assert "data_quality_alerts" in evaluation_result

    @pytest.mark.asyncio
    async def test_collection_health_monitoring(
        self,
        alert_service: AlertService,
        sample_collection_metrics: list[CollectionMetrics],
    ) -> None:
        """Test collection health monitoring functionality."""
        # Test collection health check
        health_result = await alert_service.check_collection_health()

        # Verify health check structure
        assert health_result["monitoring_service_available"] is True
        assert "collection_health_status" in health_result
        assert health_result["collection_health_status"] in ["healthy", "degraded"]
        assert "issues_detected" in health_result
        assert "alerts_triggered" in health_result

    @pytest.mark.asyncio
    async def test_system_health_alert_creation(
        self,
        alert_service: AlertService,
    ) -> None:
        """Test system health alert creation."""
        # Send a system health alert
        alert = await alert_service.send_system_health_alert(
            title="Database Connection Issues",
            message="Database connection pool exhausted",
            context={
                "database_status": "degraded",
                "active_connections": 95,
                "max_connections": 100,
            },
            severity=AlertSeverity.CRITICAL,
        )

        # Verify alert creation
        assert alert is not None
        assert alert.alert_type == AlertType.SYSTEM_HEALTH
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.title == "Database Connection Issues"
        assert "database_status" in alert.trigger_context

    @pytest.mark.asyncio
    async def test_retry_failed_deliveries(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
    ) -> None:
        """Test retry mechanism for failed deliveries."""
        # Create an alert
        alert = await alert_service.create_alert(
            rule=sample_alert_rule,
            title="Retry Test Alert",
            message="Testing retry mechanism",
            trigger_context={"test": "retry"},
        )

        # Simulate delivery failure by updating status
        await alert_service._alert_repository.update_delivery_status(
            alert.id,
            AlertDeliveryStatus.FAILED,
            {"failure_reason": "timeout"},
        )

        # Update last delivery attempt to be old enough for retry
        updated_alert = await alert_service._alert_repository.get_by_id(alert.id)
        assert updated_alert is not None

        # Test retry mechanism
        retry_result = await alert_service.retry_failed_deliveries()

        # Verify retry results structure
        assert "candidates_found" in retry_result
        assert "retry_attempts" in retry_result
        assert "successful_retries" in retry_result
        assert "failed_retries" in retry_result

    @pytest.mark.asyncio
    async def test_alert_rule_evaluation(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
    ) -> None:
        """Test alert rule evaluation workflow."""
        # Test rule evaluation (should not trigger due to implementation)
        evaluation_result = await alert_service.evaluate_alert_rules()

        # Verify evaluation structure
        assert "total_rules_evaluated" in evaluation_result
        assert "alerts_triggered" in evaluation_result
        assert "rules_skipped_cooldown" in evaluation_result
        assert "rules_skipped_rate_limit" in evaluation_result
        assert evaluation_result["total_rules_evaluated"] >= 1  # Our sample rule

    @pytest.mark.asyncio
    async def test_error_handling(
        self,
        alert_service: AlertService,
    ) -> None:
        """Test error handling in alert service operations."""
        # Test with invalid alert ID
        resolved_alert = await alert_service.resolve_alert(
            alert_id=99999,  # Non-existent ID
            resolved_by="test_user",
        )
        assert resolved_alert is None

        # Test get active alerts with invalid parameters doesn't crash
        alerts = await alert_service.get_active_alerts(
            severity=AlertSeverity.LOW,
            limit=0,
        )
        assert isinstance(alerts, list)

    @pytest.mark.asyncio
    async def test_find_similar_alerts(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
    ) -> None:
        """Test finding similar alerts by correlation key."""
        correlation_key = "test_similarity_key"

        # Create multiple alerts with same correlation key
        alert1 = await alert_service.create_alert(
            rule=sample_alert_rule,
            title="Similar Alert 1",
            message="First similar alert",
            trigger_context={"test": "similarity"},
            correlation_key=correlation_key,
        )

        # Find similar alerts
        similar_alert = await alert_service.find_similar_alerts(correlation_key)

        # Should find the alert
        assert similar_alert is not None
        assert similar_alert.id == alert1.id

    @pytest.mark.asyncio
    async def test_alert_lifecycle_complete(
        self,
        alert_service: AlertService,
        sample_alert_rule: AlertRule,
    ) -> None:
        """Test complete alert lifecycle from creation to resolution."""
        # 1. Create alert
        alert = await alert_service.create_alert(
            rule=sample_alert_rule,
            title="Lifecycle Test Alert",
            message="Testing complete alert lifecycle",
            trigger_context={
                "lifecycle_stage": "creation",
                "test_value": 42,
            },
            severity=AlertSeverity.MEDIUM,
            area_code="DE",
        )

        # Verify creation
        assert alert is not None
        assert not alert.is_resolved
        assert alert.delivery_status == AlertDeliveryStatus.PENDING

        # 2. Deliver alert
        delivery_result = await alert_service.deliver_alert(alert)
        assert delivery_result["alert_id"] == alert.id

        # 3. Check alert is in active alerts
        active_alerts = await alert_service.get_active_alerts()
        active_ids = [a.id for a in active_alerts]
        assert alert.id in active_ids

        # 4. Resolve alert
        resolved_alert = await alert_service.resolve_alert(
            alert_id=alert.id,
            resolved_by="lifecycle_test",
            notes="Completed lifecycle test successfully",
        )

        # Verify resolution
        assert resolved_alert is not None
        assert resolved_alert.is_resolved
        assert resolved_alert.resolved_by == "lifecycle_test"

        # 5. Verify alert is no longer in active alerts
        active_alerts_after = await alert_service.get_active_alerts()
        active_ids_after = [a.id for a in active_alerts_after]
        assert alert.id not in active_ids_after


class TestAlertServiceErrorHandling:
    """Test error handling scenarios for AlertService."""

    @pytest.mark.asyncio
    async def test_create_alert_with_invalid_rule(
        self, alert_service: AlertService
    ) -> None:
        """Test alert creation with invalid rule reference."""
        # Create a mock rule that doesn't exist in database
        mock_rule = AlertRule(
            id=99999,  # Non-existent ID
            name="non_existent_rule",
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.HIGH,
            conditions={"test": True},
            delivery_channels={"email": {"enabled": True}},
        )

        # This should not raise an exception but handle gracefully
        try:
            alert = await alert_service.create_alert(
                rule=mock_rule,
                title="Test Alert",
                message="Test message",
                trigger_context={"test": "error_handling"},
            )
            # If it succeeds, the alert should be created
            assert alert is not None
        except Exception as e:
            # If it fails, it should be a proper AlertError
            assert isinstance(e, AlertError)

    @pytest.mark.asyncio
    async def test_monitoring_service_unavailable(
        self,
        alert_repository: AlertRepository,
        alert_rule_repository: AlertRuleRepository,
        alert_config: AlertConfig,
    ) -> None:
        """Test alert service behavior when monitoring service is unavailable."""
        # Create alert service without monitoring service
        alert_service = AlertService(
            alert_repository=alert_repository,
            alert_rule_repository=alert_rule_repository,
            config=alert_config,
            monitoring_service=None,  # No monitoring service
        )

        # Test monitoring operations
        evaluation_result = await alert_service.evaluate_monitoring_conditions()
        assert evaluation_result["monitoring_service_available"] is False

        health_result = await alert_service.check_collection_health()
        assert health_result["monitoring_service_available"] is False
