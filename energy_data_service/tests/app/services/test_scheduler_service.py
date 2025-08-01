"""Unit tests for SchedulerService.

This module provides comprehensive unit testing for the SchedulerService
using mocked dependencies to test business logic, error handling,
and configuration validation in isolation.

Key Features:
- Isolated testing with fully mocked dependencies
- Configuration validation and error handling testing
- Job execution logic validation
- Retry and failure handling scenarios
- State management and lifecycle testing
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.config.settings import SchedulerConfig
from app.exceptions.service_exceptions import (
    SchedulerConfigurationError,
    SchedulerError,
    SchedulerJobError,
    SchedulerStateError,
)
from app.services.scheduler_service import (
    JobExecutionResult,
    ScheduleExecutionResult,
    SchedulerService,
)
from pydantic import ValidationError


@pytest.fixture
def mock_database() -> MagicMock:
    """Create mock database."""
    mock_db = MagicMock()
    mock_config = MagicMock()
    mock_db_config = MagicMock()
    mock_db_config.url = "postgresql://test:test@localhost/test"
    mock_config.database = mock_db_config
    mock_db.config = mock_config
    return mock_db


@pytest.fixture
def mock_entsoe_data_service() -> AsyncMock:
    """Create mock ENTSO-E data service."""
    mock_service = AsyncMock()
    mock_service.collect_all_gaps.return_value = {
        "DE": {
            "actual_load": MagicMock(success=True, stored_count=100),
        }
    }
    return mock_service


@pytest.fixture
def mock_backfill_service() -> AsyncMock:
    """Create mock backfill service."""
    mock_service = AsyncMock()
    mock_coverage_result = MagicMock()
    mock_coverage_result.area_code = "DE"
    mock_coverage_result.endpoint_name = "actual_load"
    mock_coverage_result.needs_backfill = True
    mock_service.analyze_coverage.return_value = [mock_coverage_result]
    return mock_service


@pytest.fixture
def scheduler_config() -> SchedulerConfig:
    """Create test scheduler configuration."""
    return SchedulerConfig(
        enabled=True,
        real_time_collection_enabled=True,
        real_time_collection_interval_minutes=30,
        gap_analysis_enabled=True,
        gap_analysis_interval_hours=4,
        daily_backfill_analysis_enabled=True,
        daily_backfill_analysis_hour=2,
        daily_backfill_analysis_minute=0,
        use_persistent_job_store=True,
        max_retry_attempts=3,
        retry_backoff_base_seconds=2.0,
        retry_backoff_max_seconds=300.0,
    )


@pytest.fixture
def scheduler_service(
    mock_entsoe_data_service: AsyncMock,
    mock_backfill_service: AsyncMock,
    mock_database: MagicMock,
    scheduler_config: SchedulerConfig,
) -> SchedulerService:
    """Create SchedulerService with mocked dependencies."""
    return SchedulerService(
        entsoe_data_service=mock_entsoe_data_service,
        backfill_service=mock_backfill_service,
        database=mock_database,
        config=scheduler_config,
    )


class TestSchedulerService:
    """Unit tests for SchedulerService."""

    def test_scheduler_service_initialization(
        self,
        scheduler_service: SchedulerService,
        scheduler_config: SchedulerConfig,
    ) -> None:
        """Test scheduler service initialization."""
        assert scheduler_service._config == scheduler_config
        assert scheduler_service._scheduler is None
        assert scheduler_service._is_running is False
        assert scheduler_service._job_failure_counts == {}
        assert scheduler_service._last_successful_runs == {}

    def test_job_types_constants(self) -> None:
        """Test that job type constants are properly defined."""
        expected_job_types = {
            "REAL_TIME_COLLECTION": "real_time_collection",
            "GAP_ANALYSIS": "gap_analysis",
            "DAILY_BACKFILL_ANALYSIS": "daily_backfill_analysis",
            "HEALTH_CHECK": "health_check",
        }

        assert expected_job_types == SchedulerService.JOB_TYPES

    @pytest.mark.asyncio
    async def test_start_scheduler_disabled(
        self,
        mock_entsoe_data_service: AsyncMock,
        mock_backfill_service: AsyncMock,
        mock_database: MagicMock,
    ) -> None:
        """Test starting scheduler when disabled in configuration."""
        disabled_config = SchedulerConfig(enabled=False)
        service = SchedulerService(
            entsoe_data_service=mock_entsoe_data_service,
            backfill_service=mock_backfill_service,
            database=mock_database,
            config=disabled_config,
        )

        result = await service.start()

        assert result.success is False
        assert result.operation == "start"
        assert "disabled in configuration" in result.message
        assert result.scheduler_state is not None
        assert result.scheduler_state["enabled"] is False

    @patch("app.services.scheduler_service.AsyncIOScheduler")
    @patch("app.services.scheduler_service.SQLAlchemyJobStore")
    @patch("app.services.scheduler_service.AsyncIOExecutor")
    @pytest.mark.asyncio
    async def test_start_scheduler_success(
        self,
        mock_executor_class: MagicMock,
        mock_jobstore_class: MagicMock,
        mock_scheduler_class: MagicMock,
        scheduler_service: SchedulerService,
    ) -> None:
        """Test successful scheduler startup."""
        mock_scheduler_instance = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler_instance
        mock_jobstore_instance = MagicMock()
        mock_jobstore_class.return_value = mock_jobstore_instance
        mock_executor_instance = MagicMock()
        mock_executor_class.return_value = mock_executor_instance

        result = await scheduler_service.start()

        assert result.success is True
        assert result.operation == "start"
        assert "started successfully" in result.message
        assert scheduler_service._is_running is True

        # Verify scheduler was started
        mock_scheduler_instance.start.assert_called_once()

        # Verify jobstore was created with correct parameters
        mock_jobstore_class.assert_called_once_with(
            url=scheduler_service._database.config.database.url,
            tablename="scheduler_jobs",
        )

    @pytest.mark.asyncio
    async def test_start_scheduler_already_running(
        self,
        scheduler_service: SchedulerService,
    ) -> None:
        """Test starting scheduler when already running."""
        # Set service as already running
        scheduler_service._is_running = True

        result = await scheduler_service.start()

        assert result.success is False
        assert result.operation == "start"
        assert "already running" in result.message
        assert result.scheduler_state is not None
        assert result.scheduler_state["is_running"] is True

    @pytest.mark.asyncio
    async def test_stop_scheduler_not_running(
        self,
        scheduler_service: SchedulerService,
    ) -> None:
        """Test stopping scheduler when not running."""
        result = await scheduler_service.stop()

        assert result.success is True
        assert result.operation == "stop"
        assert "already stopped" in result.message
        assert result.scheduler_state is not None
        assert result.scheduler_state["is_running"] is False

    @pytest.mark.asyncio
    async def test_stop_scheduler_success(
        self,
        scheduler_service: SchedulerService,
    ) -> None:
        """Test successful scheduler shutdown."""
        # Set up running scheduler
        mock_scheduler = MagicMock()
        scheduler_service._scheduler = mock_scheduler
        scheduler_service._is_running = True

        result = await scheduler_service.stop()

        assert result.success is True
        assert result.operation == "stop"
        assert "stopped successfully" in result.message
        assert scheduler_service._is_running is False
        assert scheduler_service._scheduler is None

        # Verify scheduler was shutdown
        mock_scheduler.shutdown.assert_called_once_with(wait=True)  # type: ignore[unreachable]

    @pytest.mark.asyncio
    async def test_get_status_not_initialized(
        self,
        scheduler_service: SchedulerService,
    ) -> None:
        """Test get_status when scheduler is not initialized."""
        status = await scheduler_service.get_status()

        assert status["is_running"] is False
        assert status["scheduler_state"] == "not_initialized"
        assert status["jobs"] == []
        assert status["failure_counts"] == {}
        assert status["last_successful_runs"] == {}

    @pytest.mark.asyncio
    async def test_get_status_with_jobs(
        self,
        scheduler_service: SchedulerService,
    ) -> None:
        """Test get_status with active jobs."""
        # Set up mock scheduler with jobs
        mock_scheduler = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "test_job"
        mock_job.name = "Test Job"
        mock_job.next_run_time = datetime.now(UTC)
        mock_job.trigger = "interval"
        mock_job.executor = "default"
        mock_job.max_instances = 1
        mock_job.misfire_grace_time = 300

        mock_scheduler.get_jobs.return_value = [mock_job]
        scheduler_service._scheduler = mock_scheduler
        scheduler_service._is_running = True
        scheduler_service._job_failure_counts = {"test_job": 2}
        scheduler_service._last_successful_runs = {"test_job": datetime.now(UTC)}

        status = await scheduler_service.get_status()

        assert status["is_running"] is True
        assert status["scheduler_state"] == "running"
        assert len(status["jobs"]) == 1
        assert status["jobs"][0]["id"] == "test_job"
        assert status["jobs"][0]["failure_count"] == 2
        assert status["failure_counts"]["test_job"] == 2
        assert "test_job" in status["last_successful_runs"]

    @pytest.mark.asyncio
    async def test_trigger_real_time_collection_success(
        self,
        scheduler_service: SchedulerService,
        mock_entsoe_data_service: AsyncMock,
    ) -> None:
        """Test successful manual real-time collection trigger."""
        result = await scheduler_service.trigger_real_time_collection()

        assert result.success is True
        assert result.operation == "trigger_real_time_collection"
        assert result.job_results is not None
        assert len(result.job_results) == 1

        job_result = result.job_results[0]
        assert job_result.job_type == "real_time_collection"
        assert job_result.success is True
        assert job_result.data_points_collected == 100
        assert job_result.areas_processed == 1

        mock_entsoe_data_service.collect_all_gaps.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_real_time_collection_failure(
        self,
        scheduler_service: SchedulerService,
        mock_entsoe_data_service: AsyncMock,
    ) -> None:
        """Test real-time collection trigger failure."""
        mock_entsoe_data_service.collect_all_gaps.side_effect = Exception("Test error")

        with pytest.raises(SchedulerJobError) as exc_info:
            await scheduler_service.trigger_real_time_collection()

        assert "Manual real-time collection failed" in str(exc_info.value)
        assert exc_info.value.job_type == "real_time_collection"

    @pytest.mark.asyncio
    async def test_trigger_gap_analysis_success(
        self,
        scheduler_service: SchedulerService,
        mock_backfill_service: AsyncMock,
    ) -> None:
        """Test successful manual gap analysis trigger."""
        result = await scheduler_service.trigger_gap_analysis()

        assert result.success is True
        assert result.operation == "trigger_gap_analysis"
        assert result.job_results is not None
        assert len(result.job_results) == 1

        job_result = result.job_results[0]
        assert job_result.job_type == "gap_analysis"
        assert job_result.success is True

        mock_backfill_service.analyze_coverage.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_gap_analysis_failure(
        self,
        scheduler_service: SchedulerService,
        mock_backfill_service: AsyncMock,
    ) -> None:
        """Test gap analysis trigger failure."""
        mock_backfill_service.analyze_coverage.side_effect = Exception("Test error")

        with pytest.raises(SchedulerJobError) as exc_info:
            await scheduler_service.trigger_gap_analysis()

        assert "Manual gap analysis failed" in str(exc_info.value)
        assert exc_info.value.job_type == "gap_analysis"


class TestJobExecutionResult:
    """Test JobExecutionResult dataclass."""

    def test_job_execution_result_initialization(self) -> None:
        """Test JobExecutionResult initialization."""
        result = JobExecutionResult(
            job_id="test_job",
            job_name="Test Job",
            job_type="test_type",
            success=True,
            execution_time_seconds=1.5,
            data_points_collected=100,
            areas_processed=2,
            endpoints_processed=3,
        )

        assert result.job_id == "test_job"
        assert result.job_name == "Test Job"
        assert result.job_type == "test_type"
        assert result.success is True
        assert result.execution_time_seconds == 1.5
        assert result.data_points_collected == 100
        assert result.areas_processed == 2
        assert result.endpoints_processed == 3
        assert result.error_message is None
        assert result.retry_count == 0
        assert result.next_run_time is None

    def test_job_execution_result_to_dict(self) -> None:
        """Test JobExecutionResult to_dict conversion."""
        next_run_time = datetime.now(UTC)
        result = JobExecutionResult(
            job_id="test_job",
            job_name="Test Job",
            job_type="test_type",
            success=False,
            execution_time_seconds=2.0,
            error_message="Test error",
            retry_count=2,
            next_run_time=next_run_time,
        )

        result_dict = result.to_dict()

        assert result_dict["job_id"] == "test_job"
        assert result_dict["success"] is False
        assert result_dict["error_message"] == "Test error"
        assert result_dict["retry_count"] == 2
        assert result_dict["next_run_time"] == next_run_time.isoformat()


class TestScheduleExecutionResult:
    """Test ScheduleExecutionResult dataclass."""

    def test_schedule_execution_result_initialization(self) -> None:
        """Test ScheduleExecutionResult initialization."""
        timestamp = datetime.now(UTC)
        result = ScheduleExecutionResult(
            operation="test_operation",
            success=True,
            message="Test message",
            timestamp=timestamp,
        )

        assert result.operation == "test_operation"
        assert result.success is True
        assert result.message == "Test message"
        assert result.timestamp == timestamp
        assert result.job_results is None
        assert result.scheduler_state is None
        assert result.error_context is None

    def test_schedule_execution_result_to_dict(self) -> None:
        """Test ScheduleExecutionResult to_dict conversion."""
        timestamp = datetime.now(UTC)
        job_result = JobExecutionResult(
            job_id="test_job",
            job_name="Test Job",
            job_type="test_type",
            success=True,
            execution_time_seconds=1.0,
        )

        result = ScheduleExecutionResult(
            operation="test_operation",
            success=True,
            message="Test message",
            timestamp=timestamp,
            job_results=[job_result],
            scheduler_state={"running": True},
            error_context={"error": "test"},
        )

        result_dict = result.to_dict()

        assert result_dict["operation"] == "test_operation"
        assert result_dict["success"] is True
        assert result_dict["job_results_count"] == 1
        assert result_dict["scheduler_state"] == {"running": True}
        assert result_dict["error_context"] == {"error": "test"}


class TestSchedulerConfigValidation:
    """Test scheduler configuration validation."""

    def test_valid_scheduler_config(self) -> None:
        """Test valid scheduler configuration."""
        config = SchedulerConfig(
            enabled=True,
            real_time_collection_interval_minutes=30,
            gap_analysis_interval_hours=4,
            daily_backfill_analysis_hour=2,
            daily_backfill_analysis_minute=30,
            max_retry_attempts=3,
            retry_backoff_base_seconds=2.0,
            retry_backoff_max_seconds=300.0,
        )

        assert config.enabled is True
        assert config.real_time_collection_interval_minutes == 30
        assert config.gap_analysis_interval_hours == 4
        assert config.daily_backfill_analysis_hour == 2
        assert config.daily_backfill_analysis_minute == 30

    def test_invalid_hour_validation(self) -> None:
        """Test invalid hour validation."""
        with pytest.raises(
            ValidationError, match="Input should be less than or equal to 23"
        ):
            SchedulerConfig(daily_backfill_analysis_hour=25)  # Invalid hour

    def test_invalid_minute_validation(self) -> None:
        """Test invalid minute validation."""
        with pytest.raises(
            ValidationError, match="Input should be less than or equal to 59"
        ):
            SchedulerConfig(daily_backfill_analysis_minute=70)  # Invalid minute

    def test_invalid_backoff_validation(self) -> None:
        """Test invalid backoff configuration validation."""
        with pytest.raises(
            ValidationError,
            match="retry_backoff_max_seconds.*must be greater than retry_backoff_base_seconds",
        ):
            SchedulerConfig(
                retry_backoff_base_seconds=60.0,
                retry_backoff_max_seconds=60.0,  # Max equal to base (invalid)
            )
