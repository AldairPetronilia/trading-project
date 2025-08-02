"""Integration tests for MonitoringService using testcontainers.

This module provides comprehensive integration testing for the MonitoringService
using real TimescaleDB testcontainers for database operations and collection
metrics storage.

Key Features:
- Real TimescaleDB database for collection metrics storage
- Complete monitoring workflow testing with real data
- Performance metrics calculation and validation
- Success rate analysis and anomaly detection testing
- Trend analysis and system health monitoring validation
- Data retention and cleanup operation testing
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
    DatabaseConfig,
    MonitoringConfig,
    Settings,
)
from app.container import Container
from app.models.base import Base
from app.models.collection_metrics import CollectionMetrics
from app.models.load_data import EnergyDataType
from app.repositories.collection_metrics_repository import CollectionMetricsRepository
from app.services.monitoring_service import MonitoringError, MonitoringService
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
    monitoring_config: MonitoringConfig,
) -> Settings:
    """Create test settings with testcontainer database configuration."""
    return Settings(
        environment="development",
        debug=True,
        database=database_config,
        entsoe_client__api_token=SecretStr("test_token_123456789"),
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
                    "SELECT create_hypertable('energy_data_points', 'timestamp', "
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


# Mock collection result for testing
class MockCollectionResult:
    """Mock collection result for testing tracking functionality."""

    def __init__(
        self,
        job_id: str,
        area_results: list[Any],
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> None:
        self.job_id = job_id
        self.area_results = area_results
        self.start_time = start_time or datetime.now(UTC)
        self.end_time = end_time or datetime.now(UTC)


class MockAreaResult:
    """Mock area result for testing tracking functionality."""

    def __init__(
        self,
        area_code: str,
        data_type: EnergyDataType,
        *,
        success: bool = True,
        points_collected: int = 100,
        error_message: str | None = None,
        api_response_time_ms: float | None = None,
        processing_time_ms: float | None = None,
    ) -> None:
        self.area_code = area_code
        self.data_type = data_type
        self.success = success
        self.points_collected = points_collected
        self.error_message = error_message
        self.api_response_time_ms = api_response_time_ms
        self.processing_time_ms = processing_time_ms


@pytest_asyncio.fixture
async def sample_metrics(
    metrics_repository: CollectionMetricsRepository,
) -> AsyncGenerator[list[CollectionMetrics]]:
    """Create sample collection metrics for testing."""
    current_time = datetime.now(UTC)
    metrics = []

    # Create metrics with different patterns for testing
    for i in range(10):
        metric = CollectionMetrics(
            job_id=f"test_job_{i % 3}",  # 3 different jobs
            area_code=["DE", "FR", "NL"][i % 3],  # 3 different areas
            data_type=[EnergyDataType.ACTUAL, EnergyDataType.DAY_AHEAD][
                i % 2
            ],  # 2 data types
            collection_start=current_time - timedelta(hours=i),
            collection_end=current_time - timedelta(hours=i) + timedelta(minutes=5),
            points_collected=100 + (i * 10),  # Varying points collected
            success=i % 4 != 0,  # 75% success rate (fail every 4th)
            error_message="Test error" if i % 4 == 0 else None,
            api_response_time=1000.0 + (i * 100),  # Varying response times
            processing_time=500.0 + (i * 50),  # Varying processing times
        )
        metrics.append(metric)

    # Store metrics in database
    async with metrics_repository.database.session_factory() as session:
        for metric in metrics:
            session.add(metric)
        await session.commit()

    yield metrics


class TestMonitoringServiceIntegration:
    """Integration tests for MonitoringService with real database operations."""

    @pytest.mark.asyncio
    async def test_track_collection_result_success(
        self,
        monitoring_service: MonitoringService,
        metrics_repository: CollectionMetricsRepository,
    ) -> None:
        """Test successful collection result tracking."""
        # Arrange
        start_time = datetime.now(UTC)
        end_time = start_time + timedelta(minutes=5)

        area_results = [
            MockAreaResult(
                area_code="DE",
                data_type=EnergyDataType.ACTUAL,
                success=True,
                points_collected=150,
                api_response_time_ms=1200.0,
                processing_time_ms=300.0,
            ),
            MockAreaResult(
                area_code="FR",
                data_type=EnergyDataType.DAY_AHEAD,
                success=True,
                points_collected=200,
                api_response_time_ms=1500.0,
                processing_time_ms=400.0,
            ),
        ]

        collection_result = MockCollectionResult(
            job_id="test_tracking_job",
            area_results=area_results,
            start_time=start_time,
            end_time=end_time,
        )

        # Act
        await monitoring_service.track_collection_result(collection_result)

        # Assert
        stored_metrics = await metrics_repository.get_metrics_by_job_id(
            "test_tracking_job"
        )
        assert len(stored_metrics) == 2

        # Verify first metric
        de_metric = next(m for m in stored_metrics if m.area_code == "DE")
        assert de_metric.job_id == "test_tracking_job"
        assert de_metric.area_code == "DE"
        assert de_metric.data_type == EnergyDataType.ACTUAL
        assert de_metric.points_collected == 150
        assert de_metric.success is True
        assert de_metric.api_response_time == 1200.0
        assert de_metric.processing_time == 300.0

        # Verify second metric
        fr_metric = next(m for m in stored_metrics if m.area_code == "FR")
        assert fr_metric.job_id == "test_tracking_job"
        assert fr_metric.area_code == "FR"
        assert fr_metric.data_type == EnergyDataType.DAY_AHEAD
        assert fr_metric.points_collected == 200
        assert fr_metric.success is True
        assert fr_metric.api_response_time == 1500.0
        assert fr_metric.processing_time == 400.0

    @pytest.mark.asyncio
    async def test_track_collection_result_with_failure(
        self,
        monitoring_service: MonitoringService,
        metrics_repository: CollectionMetricsRepository,
    ) -> None:
        """Test collection result tracking with failures."""
        # Arrange
        area_results = [
            MockAreaResult(
                area_code="DE",
                data_type=EnergyDataType.ACTUAL,
                success=False,
                points_collected=0,
                error_message="API timeout error",
            ),
        ]

        collection_result = MockCollectionResult(
            job_id="test_failure_job",
            area_results=area_results,
        )

        # Act
        await monitoring_service.track_collection_result(collection_result)

        # Assert
        stored_metrics = await metrics_repository.get_metrics_by_job_id(
            "test_failure_job"
        )
        assert len(stored_metrics) == 1

        metric = stored_metrics[0]
        assert metric.success is False
        assert metric.points_collected == 0
        assert metric.error_message == "API timeout error"

    @pytest.mark.asyncio
    async def test_track_collection_result_invalid_format(
        self,
        monitoring_service: MonitoringService,
    ) -> None:
        """Test collection result tracking with invalid format."""
        # Arrange
        invalid_result = MagicMock()
        del invalid_result.job_id  # Missing required attribute

        # Act & Assert
        with pytest.raises(MonitoringError) as exc_info:
            await monitoring_service.track_collection_result(invalid_result)

        assert "Invalid collection result format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_calculate_success_rates(
        self,
        monitoring_service: MonitoringService,
        sample_metrics: list[CollectionMetrics],  # noqa: ARG002
    ) -> None:
        """Test success rate calculation."""
        # Act
        success_rates = await monitoring_service.calculate_success_rates(
            period=timedelta(hours=12)
        )

        # Assert
        assert len(success_rates) > 0

        # Check that all rates are between 0 and 1
        for rate in success_rates.values():
            assert 0.0 <= rate <= 1.0

        # With our test data (75% success rate), we should see rates around 0.75
        # but it might vary based on which metrics fall within the time window
        assert any(rate > 0.5 for rate in success_rates.values())

    @pytest.mark.asyncio
    async def test_calculate_success_rates_empty_period(
        self,
        monitoring_service: MonitoringService,
    ) -> None:
        """Test success rate calculation with no data."""
        # Act
        success_rates = await monitoring_service.calculate_success_rates(
            period=timedelta(minutes=1)  # Very short period with no data
        )

        # Assert
        assert success_rates == {}

    @pytest.mark.asyncio
    async def test_get_performance_metrics(
        self,
        monitoring_service: MonitoringService,
        sample_metrics: list[CollectionMetrics],  # noqa: ARG002
    ) -> None:
        """Test performance metrics retrieval."""
        # Act
        performance_metrics = await monitoring_service.get_performance_metrics(
            period=timedelta(hours=12)
        )

        # Assert
        assert "avg_api_response_time" in performance_metrics
        assert "total_operations" in performance_metrics
        assert "successful_operations" in performance_metrics
        assert "failed_operations" in performance_metrics
        assert "overall_success_rate" in performance_metrics
        assert "period_start" in performance_metrics
        assert "period_end" in performance_metrics

        # Verify the values make sense
        total = performance_metrics["total_operations"]
        successful = performance_metrics["successful_operations"]
        failed = performance_metrics["failed_operations"]

        assert total == successful + failed
        assert (
            performance_metrics["overall_success_rate"] == successful / total
            if total > 0
            else 0
        )

    @pytest.mark.asyncio
    async def test_get_recent_metrics(
        self,
        monitoring_service: MonitoringService,
        sample_metrics: list[CollectionMetrics],  # noqa: ARG002
    ) -> None:
        """Test recent metrics retrieval."""
        # Act
        recent_metrics = await monitoring_service.get_recent_metrics(minutes=60)

        # Assert
        assert len(recent_metrics) > 0

        # Verify all metrics are recent
        cutoff_time = datetime.now(UTC) - timedelta(minutes=60)
        for metric in recent_metrics:
            assert metric.collection_start >= cutoff_time

    @pytest.mark.asyncio
    async def test_detect_anomalies_with_anomalies(
        self,
        monitoring_service: MonitoringService,
        sample_metrics: list[CollectionMetrics],  # noqa: ARG002
    ) -> None:
        """Test anomaly detection when anomalies exist."""
        # Act - analyze DE area with ACTUAL data type
        anomaly_result = await monitoring_service.detect_anomalies(
            area_code="DE",
            data_type=EnergyDataType.ACTUAL,
            period=timedelta(hours=12),
        )

        # Assert
        assert anomaly_result["anomaly_detection_enabled"] is True
        assert anomaly_result["area_code"] == "DE"
        assert anomaly_result["data_type"] == "actual"
        assert "total_operations" in anomaly_result
        assert "success_rate" in anomaly_result
        assert "anomalies_detected" in anomaly_result
        assert "anomaly_count" in anomaly_result

        # Check if anomalies were detected (depends on test data)
        if anomaly_result["anomaly_count"] > 0:
            for anomaly in anomaly_result["anomalies_detected"]:
                assert "type" in anomaly
                assert "description" in anomaly
                assert "severity" in anomaly

    @pytest.mark.asyncio
    async def test_detect_anomalies_no_data(
        self,
        monitoring_service: MonitoringService,
    ) -> None:
        """Test anomaly detection with no data."""
        # Act
        anomaly_result = await monitoring_service.detect_anomalies(
            area_code="UNKNOWN",
            data_type=EnergyDataType.ACTUAL,
            period=timedelta(hours=1),
        )

        # Assert
        assert anomaly_result["anomaly_detection_enabled"] is True
        assert "No data available for anomaly detection" in anomaly_result["message"]

    @pytest.mark.asyncio
    async def test_cleanup_old_metrics(
        self,
        monitoring_service: MonitoringService,
        metrics_repository: CollectionMetricsRepository,
    ) -> None:
        """Test cleanup of old metrics."""
        # Arrange - create some old metrics
        old_time = datetime.now(UTC) - timedelta(days=10)
        old_metric = CollectionMetrics(
            job_id="old_job",
            area_code="DE",
            data_type=EnergyDataType.ACTUAL,
            collection_start=old_time,
            collection_end=old_time + timedelta(minutes=5),
            points_collected=100,
            success=True,
        )

        async with metrics_repository.database.session_factory() as session:
            session.add(old_metric)
            await session.commit()

        # Act
        deleted_count = await monitoring_service.cleanup_old_metrics()

        # Assert
        assert deleted_count >= 1  # At least the old metric we created

        # Verify the old metric was deleted
        remaining_metrics = await metrics_repository.get_all()
        old_metrics = [m for m in remaining_metrics if m.job_id == "old_job"]
        assert len(old_metrics) == 0

    @pytest.mark.asyncio
    async def test_get_collection_trends(
        self,
        monitoring_service: MonitoringService,
        sample_metrics: list[CollectionMetrics],  # noqa: ARG002
    ) -> None:
        """Test collection trends analysis."""
        # Act
        trends = await monitoring_service.get_collection_trends(days=2)

        # Assert
        assert trends["period_days"] == 2
        assert "total_operations" in trends
        assert "total_successful_operations" in trends
        assert "total_points_collected" in trends
        assert "overall_success_rate" in trends
        assert "daily_statistics" in trends
        assert "trend_direction" in trends
        assert "analysis_timestamp" in trends

        # Verify daily statistics structure
        if trends["total_operations"] > 0:
            daily_stats = trends["daily_statistics"]
            for stats in daily_stats.values():
                assert "total_operations" in stats
                assert "successful_operations" in stats
                assert "total_points" in stats
                assert "success_rate" in stats
                assert "avg_response_time" in stats

    @pytest.mark.asyncio
    async def test_get_collection_trends_no_data(
        self,
        monitoring_service: MonitoringService,
    ) -> None:
        """Test collection trends with no data."""
        # Act
        trends = await monitoring_service.get_collection_trends(days=1)

        # Assert
        assert trends["period_days"] == 1
        assert trends["total_operations"] == 0
        assert "No data available for trend analysis" in trends["message"]

    @pytest.mark.asyncio
    async def test_get_system_health_summary(
        self,
        monitoring_service: MonitoringService,
        sample_metrics: list[CollectionMetrics],  # noqa: ARG002
    ) -> None:
        """Test system health summary."""
        # Act
        health_summary = await monitoring_service.get_system_health_summary()

        # Assert
        assert "health_assessment" in health_summary
        assert "performance_metrics" in health_summary
        assert "recent_operations_count" in health_summary
        assert "assessment_timestamp" in health_summary
        assert "configuration" in health_summary

        # Verify health assessment structure
        health_assessment = health_summary["health_assessment"]
        assert "overall_status" in health_assessment
        assert "status_reasons" in health_assessment
        assert "performance_status" in health_assessment
        assert "availability_status" in health_assessment
        assert "data_quality_status" in health_assessment

        # Verify configuration
        config = health_summary["configuration"]
        assert "performance_threshold_ms" in config
        assert "success_rate_threshold" in config
        assert "anomaly_detection_enabled" in config

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns(
        self,
        monitoring_service: MonitoringService,
        sample_metrics: list[CollectionMetrics],  # noqa: ARG002
    ) -> None:
        """Test failure pattern analysis."""
        # Act
        failure_analysis = await monitoring_service.analyze_failure_patterns(
            period=timedelta(hours=12)
        )

        # Assert
        assert "period_analyzed" in failure_analysis
        assert "total_operations" in failure_analysis
        assert "failed_operations" in failure_analysis
        assert "failure_rate" in failure_analysis
        assert "failure_patterns" in failure_analysis
        assert "top_failures" in failure_analysis
        assert "recommendations" in failure_analysis

        # Verify failure patterns structure
        patterns = failure_analysis["failure_patterns"]
        assert "by_area_code" in patterns
        assert "by_data_type" in patterns
        assert "by_error_pattern" in patterns

        # Verify top failures structure
        top_failures = failure_analysis["top_failures"]
        assert "areas" in top_failures
        assert "data_types" in top_failures
        assert "error_patterns" in top_failures

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_no_failures(
        self,
        monitoring_service: MonitoringService,
        metrics_repository: CollectionMetricsRepository,
    ) -> None:
        """Test failure pattern analysis with no failures."""
        # Arrange - create only successful metrics
        current_time = datetime.now(UTC)
        successful_metric = CollectionMetrics(
            job_id="success_job",
            area_code="DE",
            data_type=EnergyDataType.ACTUAL,
            collection_start=current_time - timedelta(minutes=30),
            collection_end=current_time - timedelta(minutes=25),
            points_collected=100,
            success=True,
        )

        async with metrics_repository.database.session_factory() as session:
            session.add(successful_metric)
            await session.commit()

        # Act
        failure_analysis = await monitoring_service.analyze_failure_patterns(
            period=timedelta(hours=1)
        )

        # Assert
        assert failure_analysis["failed_operations"] == 0
        assert failure_analysis["failure_rate"] == 0.0
        assert "No failures detected" in failure_analysis["message"]

    @pytest.mark.asyncio
    async def test_monitoring_error_handling(
        self,
        monitoring_service: MonitoringService,
    ) -> None:
        """Test proper error handling and exception chaining."""
        # Arrange - create a service with invalid repository (simulate database error)
        invalid_service = MonitoringService(
            metrics_repository=None,  # type: ignore[arg-type]
            database=monitoring_service._database,
            config=monitoring_service._config,
        )

        # Act & Assert
        with pytest.raises(MonitoringError) as exc_info:
            await invalid_service.calculate_success_rates(timedelta(hours=1))

        # Verify exception has proper context
        error = exc_info.value
        assert error.service_name == "MonitoringService"
        assert error.operation == "calculate_success_rates"
        assert isinstance(error.context, dict)

    @pytest.mark.asyncio
    async def test_concurrent_operations(
        self,
        monitoring_service: MonitoringService,
        metrics_repository: CollectionMetricsRepository,
    ) -> None:
        """Test concurrent monitoring operations."""
        # Arrange - create multiple collection results
        collection_results = []
        for i in range(5):
            area_results = [
                MockAreaResult(
                    area_code=f"AREA_{i}",
                    data_type=EnergyDataType.ACTUAL,
                    success=True,
                    points_collected=100 + i,
                ),
            ]
            collection_results.append(
                MockCollectionResult(
                    job_id=f"concurrent_job_{i}",
                    area_results=area_results,
                )
            )

        # Act - track results concurrently
        tasks = [
            monitoring_service.track_collection_result(result)
            for result in collection_results
        ]
        await asyncio.gather(*tasks)

        # Assert - verify all results were tracked
        all_metrics = await metrics_repository.get_all()
        concurrent_metrics = [
            m for m in all_metrics if m.job_id.startswith("concurrent_job_")
        ]
        assert len(concurrent_metrics) == 5

        # Verify each job has its metrics
        for i in range(5):
            job_metrics = [
                m for m in concurrent_metrics if m.job_id == f"concurrent_job_{i}"
            ]
            assert len(job_metrics) == 1
            assert job_metrics[0].area_code == f"AREA_{i}"
            assert job_metrics[0].points_collected == 100 + i
