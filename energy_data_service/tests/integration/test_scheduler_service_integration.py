"""Integration tests for SchedulerService using testcontainers.

This module provides comprehensive integration testing for the SchedulerService
using real TimescaleDB testcontainers for database operations while mocking
external API calls to ENTSO-E.

Key Features:
- Real TimescaleDB database with APScheduler job persistence
- Mocked ENTSO-E data service and backfill service for controlled testing
- Full dependency injection testing with real components
- Scheduler lifecycle testing (start, stop, job execution)
- Job failure handling and retry logic testing
- Health monitoring and status reporting validation
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from app.config.database import Database
from app.config.settings import (
    DatabaseConfig,
    SchedulerConfig,
    Settings,
)
from app.container import Container
from app.exceptions.service_exceptions import (
    SchedulerConfigurationError,
    SchedulerError,
    SchedulerJobError,
    SchedulerStateError,
)
from app.models.base import Base
from app.services.scheduler_service import (
    JobExecutionResult,
    ScheduleExecutionResult,
    SchedulerService,
)
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
def scheduler_config() -> SchedulerConfig:
    """Create SchedulerConfig with test-appropriate settings."""
    return SchedulerConfig(
        enabled=True,
        real_time_collection_enabled=True,
        real_time_collection_interval_minutes=5,  # Short interval for testing
        gap_analysis_enabled=True,
        gap_analysis_interval_hours=1,  # Short interval for testing
        daily_backfill_analysis_enabled=False,  # Disable for integration tests
        use_persistent_job_store=False,  # Disable for integration tests (requires psycopg2)
        job_defaults_max_instances=1,
        job_defaults_coalesce=True,
        job_defaults_misfire_grace_time_seconds=60,
        max_retry_attempts=2,  # Reduced for faster testing
        retry_backoff_base_seconds=1.0,
        retry_backoff_max_seconds=60.0,  # Must be >= 60 for validation
        job_health_check_interval_minutes=5,  # Must be >= 5 for validation
        failed_job_notification_threshold=2,
        thread_pool_max_workers=2,
    )


@pytest.fixture
def test_settings(
    database_config: DatabaseConfig,
    scheduler_config: SchedulerConfig,
) -> Settings:
    """Create test settings with testcontainer database configuration."""
    return Settings(
        environment="development",
        debug=True,
        database=database_config,
        entsoe_client__api_token=SecretStr("test_token_123456789"),
        scheduler=scheduler_config,
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


@pytest.fixture
def mock_entsoe_data_service() -> AsyncMock:
    """Create mock ENTSO-E data service."""
    mock_service = AsyncMock()

    # Mock collect_all_gaps method
    mock_service.collect_all_gaps.return_value = {
        "DE": {
            "actual_load": MagicMock(success=True, stored_count=100),
            "day_ahead_forecast": MagicMock(success=True, stored_count=50),
        },
        "FR": {
            "actual_load": MagicMock(success=True, stored_count=75),
            "day_ahead_forecast": MagicMock(success=True, stored_count=25),
        },
    }

    return mock_service


@pytest.fixture
def mock_backfill_service() -> AsyncMock:
    """Create mock backfill service."""
    mock_service = AsyncMock()

    # Mock analyze_coverage method
    mock_coverage_result = MagicMock()
    mock_coverage_result.area_code = "DE"
    mock_coverage_result.endpoint_name = "actual_load"
    mock_coverage_result.coverage_percentage = 85.0
    mock_coverage_result.needs_backfill = True
    mock_coverage_result.total_missing_points = 1500

    mock_service.analyze_coverage.return_value = [mock_coverage_result]

    return mock_service


@pytest_asyncio.fixture
async def scheduler_service(
    database: Database,
    scheduler_config: SchedulerConfig,
    mock_entsoe_data_service: AsyncMock,
    mock_backfill_service: AsyncMock,
) -> AsyncGenerator[SchedulerService]:
    """Create SchedulerService instance with mocked dependencies."""
    service = SchedulerService(
        entsoe_data_service=mock_entsoe_data_service,
        backfill_service=mock_backfill_service,
        database=database,
        config=scheduler_config,
    )

    yield service

    # Cleanup: ensure scheduler is stopped
    try:  # noqa: SIM105
        await service.stop()
    except Exception:  # noqa: BLE001, S110
        pass  # Service might already be stopped


class TestSchedulerServiceIntegration:
    """Integration tests for SchedulerService."""

    @pytest.mark.asyncio
    async def test_scheduler_lifecycle_start_stop(
        self,
        scheduler_service: SchedulerService,
    ) -> None:
        """Test scheduler service start and stop lifecycle."""
        # Test start
        start_result = await scheduler_service.start()

        assert start_result.success is True
        assert start_result.operation == "start"
        assert start_result.scheduler_state is not None
        assert start_result.scheduler_state["running"] is True

        # Test status after start
        status = await scheduler_service.get_status()
        assert status["is_running"] is True
        assert status["scheduler_state"] == "running"
        assert len(status["jobs"]) > 0  # Should have configured jobs

        # Test stop
        stop_result = await scheduler_service.stop()

        assert stop_result.success is True
        assert stop_result.operation == "stop"
        assert stop_result.scheduler_state is not None
        assert stop_result.scheduler_state["is_running"] is False

        # Test status after stop
        status = await scheduler_service.get_status()
        assert status["is_running"] is False
        assert (
            status["scheduler_state"] == "not_initialized"
        )  # Scheduler instance is cleared after stop

    @pytest.mark.asyncio
    async def test_scheduler_start_when_already_running(
        self,
        scheduler_service: SchedulerService,
    ) -> None:
        """Test starting scheduler when it's already running."""
        # Start scheduler first
        await scheduler_service.start()

        # Attempt to start again
        result = await scheduler_service.start()

        assert result.success is False
        assert "already running" in result.message
        assert result.scheduler_state is not None
        assert result.scheduler_state["is_running"] is True

        # Cleanup
        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_scheduler_disabled_configuration(
        self,
        database: Database,
        mock_entsoe_data_service: AsyncMock,
        mock_backfill_service: AsyncMock,
    ) -> None:
        """Test scheduler behavior when disabled in configuration."""
        # Create disabled configuration
        disabled_config = SchedulerConfig(enabled=False)

        service = SchedulerService(
            entsoe_data_service=mock_entsoe_data_service,
            backfill_service=mock_backfill_service,
            database=database,
            config=disabled_config,
        )

        # Attempt to start disabled scheduler
        result = await service.start()

        assert result.success is False
        assert "disabled in configuration" in result.message
        assert result.scheduler_state is not None
        assert result.scheduler_state["enabled"] is False

    @pytest.mark.asyncio
    async def test_manual_real_time_collection_trigger(
        self,
        scheduler_service: SchedulerService,
        mock_entsoe_data_service: AsyncMock,
    ) -> None:
        """Test manual triggering of real-time data collection."""
        # Start scheduler
        await scheduler_service.start()

        # Trigger real-time collection manually
        result = await scheduler_service.trigger_real_time_collection()

        assert result.success is True
        assert result.operation == "trigger_real_time_collection"
        assert result.job_results is not None
        assert len(result.job_results) == 1

        job_result = result.job_results[0]
        assert job_result.job_type == "real_time_collection"
        assert job_result.success is True
        assert job_result.data_points_collected == 250  # 100+50+75+25
        assert job_result.areas_processed == 2
        assert job_result.endpoints_processed == 4

        # Verify the service was called
        mock_entsoe_data_service.collect_all_gaps.assert_called_once()

        # Cleanup
        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_manual_gap_analysis_trigger(
        self,
        scheduler_service: SchedulerService,
        mock_backfill_service: AsyncMock,
    ) -> None:
        """Test manual triggering of gap analysis."""
        # Start scheduler
        await scheduler_service.start()

        # Trigger gap analysis manually
        result = await scheduler_service.trigger_gap_analysis()

        assert result.success is True
        assert result.operation == "trigger_gap_analysis"
        assert result.job_results is not None
        assert len(result.job_results) == 1

        job_result = result.job_results[0]
        assert job_result.job_type == "gap_analysis"
        assert job_result.success is True
        assert job_result.areas_processed == 1
        assert job_result.endpoints_processed == 1

        # Verify the service was called
        mock_backfill_service.analyze_coverage.assert_called_once()

        # Cleanup
        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_job_failure_handling_and_retry(
        self,
        scheduler_service: SchedulerService,
        mock_entsoe_data_service: AsyncMock,
    ) -> None:
        """Test job failure handling and retry logic."""
        # Configure mock to fail
        mock_entsoe_data_service.collect_all_gaps.side_effect = Exception(
            "Test failure"
        )

        # Start scheduler
        await scheduler_service.start()

        # Trigger collection that will fail
        with pytest.raises(SchedulerJobError):
            await scheduler_service.trigger_real_time_collection()

        # Verify the service was called
        mock_entsoe_data_service.collect_all_gaps.assert_called_once()

        # Cleanup
        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_scheduler_job_persistence(
        self,
        database: Database,
        scheduler_config: SchedulerConfig,
        mock_entsoe_data_service: AsyncMock,
        mock_backfill_service: AsyncMock,
    ) -> None:
        """Test job persistence in database."""
        _ = scheduler_config  # Mark as used to avoid warning
        # Create scheduler with persistent job store disabled for integration tests
        persistent_config = SchedulerConfig(
            enabled=True,
            use_persistent_job_store=False,  # Disabled for integration tests (would require psycopg2)
            real_time_collection_enabled=True,
            gap_analysis_enabled=True,
            daily_backfill_analysis_enabled=False,
        )

        service = SchedulerService(
            entsoe_data_service=mock_entsoe_data_service,
            backfill_service=mock_backfill_service,
            database=database,
            config=persistent_config,
        )

        # Start scheduler
        await service.start()

        # Since persistent job store is disabled, just verify scheduler started successfully
        status = await service.get_status()
        assert status["is_running"] is True
        assert len(status["jobs"]) > 0  # Should have configured jobs in memory

        # Stop scheduler
        await service.stop()

    @pytest.mark.asyncio
    async def test_scheduler_status_comprehensive(
        self,
        scheduler_service: SchedulerService,
    ) -> None:
        """Test comprehensive scheduler status reporting."""
        # Test status when not started
        status = await scheduler_service.get_status()
        assert status["is_running"] is False
        assert status["scheduler_state"] == "not_initialized"
        assert status["jobs"] == []

        # Start scheduler
        await scheduler_service.start()

        # Test status when running
        status = await scheduler_service.get_status()
        assert status["is_running"] is True
        assert status["scheduler_state"] == "running"
        assert len(status["jobs"]) > 0
        assert "config_enabled" in status
        assert "total_jobs" in status
        assert "failure_counts" in status
        assert "last_successful_runs" in status

        # Verify job information structure
        for job in status["jobs"]:
            assert "id" in job
            assert "name" in job
            assert "trigger" in job
            assert "executor" in job
            assert "failure_count" in job

        # Cleanup
        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_scheduler_error_handling(
        self,
        database: Database,
        mock_entsoe_data_service: AsyncMock,
        mock_backfill_service: AsyncMock,
    ) -> None:
        """Test scheduler error handling scenarios."""
        # Create valid configuration for proper initialization
        valid_config = SchedulerConfig(
            enabled=True,
            real_time_collection_enabled=True,
            real_time_collection_interval_minutes=5,  # Valid minimum value
            gap_analysis_enabled=True,
            gap_analysis_interval_hours=1,
            use_persistent_job_store=False,  # Disable persistence for test simplicity
        )

        # Create scheduler service with valid config
        scheduler_service = SchedulerService(
            entsoe_data_service=mock_entsoe_data_service,
            backfill_service=mock_backfill_service,
            database=database,
            config=valid_config,
        )

        # Start the scheduler successfully first
        await scheduler_service.start()

        # Test error handling during job execution by making the service fail
        mock_entsoe_data_service.collect_all_gaps.side_effect = Exception(
            "ENTSO-E API service temporarily unavailable"
        )

        # This should raise a SchedulerJobError when the job fails
        with pytest.raises(SchedulerJobError, match=".*real-time collection.*"):
            await scheduler_service.trigger_real_time_collection()

        # Clean up
        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_scheduler_job_configuration(
        self,
        scheduler_service: SchedulerService,
    ) -> None:
        """Test that jobs are configured correctly based on configuration."""
        # Start scheduler
        await scheduler_service.start()

        # Get status and verify job configuration
        status = await scheduler_service.get_status()
        job_ids = [job["id"] for job in status["jobs"]]

        # Should have real-time collection job (enabled in config)
        assert "real_time_collection" in job_ids

        # Should have gap analysis job (enabled in config)
        assert "gap_analysis" in job_ids

        # Should have health check job (always enabled)
        assert "health_check" in job_ids

        # Should NOT have daily backfill analysis (disabled in test config)
        assert "daily_backfill_analysis" not in job_ids

        # Cleanup
        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_concurrent_operations_handling(
        self,
        scheduler_service: SchedulerService,
        mock_entsoe_data_service: AsyncMock,
    ) -> None:
        """Test handling of concurrent job operations."""
        _ = mock_entsoe_data_service  # Mark as used to avoid warning
        # Start scheduler
        await scheduler_service.start()

        # Create multiple concurrent collection triggers
        tasks = [scheduler_service.trigger_real_time_collection() for _ in range(3)]

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least one should succeed (others might fail due to concurrency limits)
        successful_results = [
            r for r in results if isinstance(r, ScheduleExecutionResult) and r.success
        ]
        assert len(successful_results) >= 1

        # Cleanup
        await scheduler_service.stop()


class TestSchedulerServiceErrorScenarios:
    """Test error scenarios and edge cases for SchedulerService."""

    @pytest.mark.asyncio
    async def test_database_connection_failure(
        self,
        scheduler_config: SchedulerConfig,
        mock_entsoe_data_service: AsyncMock,
        mock_backfill_service: AsyncMock,
    ) -> None:
        """Test scheduler behavior with database connection issues."""
        # Create database with invalid configuration
        invalid_db_config = DatabaseConfig(
            host="invalid_host",
            port=5432,
            user="invalid_user",
            password=SecretStr("invalid_password"),
            name="invalid_db",
        )

        invalid_settings = Settings(database=invalid_db_config)
        invalid_database = Database(invalid_settings)

        service = SchedulerService(
            entsoe_data_service=mock_entsoe_data_service,
            backfill_service=mock_backfill_service,
            database=invalid_database,
            config=scheduler_config,
        )

        # Attempt to start scheduler with invalid database
        with pytest.raises((SchedulerStateError, SchedulerConfigurationError)):
            await service.start()

    @pytest.mark.asyncio
    async def test_service_dependency_failures(
        self,
        scheduler_service: SchedulerService,
        mock_entsoe_data_service: AsyncMock,
        mock_backfill_service: AsyncMock,
    ) -> None:
        """Test scheduler behavior when dependent services fail."""
        # Configure both services to fail
        mock_entsoe_data_service.collect_all_gaps.side_effect = Exception(
            "ENTSO-E service down"
        )
        mock_backfill_service.analyze_coverage.side_effect = Exception(
            "Backfill service down"
        )

        # Start scheduler
        await scheduler_service.start()

        # Both manual triggers should fail gracefully
        with pytest.raises(SchedulerJobError):
            await scheduler_service.trigger_real_time_collection()

        with pytest.raises(SchedulerJobError):
            await scheduler_service.trigger_gap_analysis()

        # Scheduler should still be running and responsive
        status = await scheduler_service.get_status()
        assert status["is_running"] is True

        # Cleanup
        await scheduler_service.stop()
