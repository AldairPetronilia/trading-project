"""
Unit tests for BackfillService.

This module provides comprehensive unit tests for the BackfillService class,
covering coverage analysis, backfill operations, progress tracking, and
error handling scenarios.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.config.settings import BackfillConfig, EntsoEDataCollectionConfig
from app.exceptions import (
    BackfillCoverageError,
    BackfillError,
    BackfillProgressError,
    BackfillResourceError,
)
from app.models import BackfillProgress, BackfillStatus, EnergyDataType
from app.services.backfill_service import (
    BackfillResult,
    BackfillService,
    CoverageAnalysis,
)

from entsoe_client.model.common.area_code import AreaCode


class TestBackfillService:
    """Test suite for BackfillService."""

    @pytest.fixture
    def mock_collector(self) -> AsyncMock:
        """Create a mock ENTSO-E collector."""
        return AsyncMock()

    @pytest.fixture
    def mock_processor(self) -> AsyncMock:
        """Create a mock processor."""
        return AsyncMock()

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create a mock repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_database(self) -> AsyncMock:
        """Create a mock database."""
        database = AsyncMock()

        # Create an async generator mock
        async def mock_session_generator() -> AsyncGenerator[AsyncMock]:
            session = AsyncMock()
            try:
                yield session
            finally:
                pass  # Mock cleanup

        database.get_database_session = mock_session_generator
        return database

    @pytest.fixture
    def mock_progress_repository(self) -> AsyncMock:
        """Create a mock progress repository."""
        return AsyncMock()

    @pytest.fixture
    def backfill_config(self) -> BackfillConfig:
        """Create a backfill configuration."""
        return BackfillConfig(
            historical_years=2,
            chunk_months=6,
            rate_limit_delay=1.0,
            max_concurrent_areas=2,
            enable_progress_persistence=True,
            resume_incomplete_backfills=True,
        )

    @pytest.fixture
    def entsoe_data_collection_config(self) -> EntsoEDataCollectionConfig:
        """Create an ENTSO-E data collection configuration."""
        return EntsoEDataCollectionConfig(target_areas=["DE-LU", "DE-AT-LU"])

    @pytest.fixture
    def backfill_service(
        self,
        mock_collector: AsyncMock,
        mock_processor: AsyncMock,
        mock_repository: AsyncMock,
        mock_database: AsyncMock,
        backfill_config: BackfillConfig,
        mock_progress_repository: AsyncMock,
        entsoe_data_collection_config: EntsoEDataCollectionConfig,
    ) -> BackfillService:
        """Create a BackfillService with mocked dependencies."""
        return BackfillService(
            collector=mock_collector,
            processor=mock_processor,
            repository=mock_repository,
            database=mock_database,
            config=backfill_config,
            progress_repository=mock_progress_repository,
            entsoe_data_collection_config=entsoe_data_collection_config,
        )

    @pytest.fixture
    def sample_areas(self) -> list[AreaCode]:
        """Create sample area codes."""
        return [AreaCode.GERMANY, AreaCode.FRANCE, AreaCode.NETHERLANDS]

    @pytest.fixture
    def sample_endpoints(self) -> list[str]:
        """Create sample endpoint names."""
        return ["actual_load", "day_ahead_forecast", "week_ahead_forecast"]

    @pytest.fixture
    def sample_period_start(self) -> datetime:
        """Create sample period start."""
        return datetime(2022, 1, 1, tzinfo=UTC)

    @pytest.fixture
    def sample_period_end(self) -> datetime:
        """Create sample period end."""
        return datetime(2022, 3, 1, tzinfo=UTC)  # Shorter period for faster tests

    # Coverage Analysis Tests

    @pytest.mark.asyncio
    async def test_analyze_coverage_with_defaults(
        self,
        backfill_service: BackfillService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test coverage analysis with default parameters."""
        # Mock repository to return some data points
        mock_repository.get_by_time_range.return_value = [MagicMock()] * 100

        results = await backfill_service.analyze_coverage()

        # Should analyze 2 default areas and 6 default endpoints
        assert len(results) == 12  # 2 areas * 6 endpoints
        assert all(isinstance(result, CoverageAnalysis) for result in results)

    @pytest.mark.asyncio
    async def test_analyze_coverage_with_specific_parameters(
        self,
        backfill_service: BackfillService,
        mock_repository: AsyncMock,
        sample_areas: list[AreaCode],
        sample_endpoints: list[str],
    ) -> None:
        """Test coverage analysis with specific parameters."""
        # Mock repository to return data points
        mock_repository.get_by_time_range.return_value = [MagicMock()] * 50

        results = await backfill_service.analyze_coverage(
            areas=sample_areas[:2], endpoints=sample_endpoints[:2], years_back=1
        )

        # Should analyze 2 areas and 2 endpoints
        assert len(results) == 4  # 2 areas * 2 endpoints

        # Verify parameters passed to repository
        call_args_list = mock_repository.get_by_time_range.call_args_list
        assert len(call_args_list) == 4

        # Check that time range is approximately 1 year
        for call_args in call_args_list:
            kwargs = call_args[1]
            time_diff = kwargs["end_time"] - kwargs["start_time"]
            assert 360 <= time_diff.days <= 366  # Approximately 1 year

    @pytest.mark.asyncio
    async def test_analyze_coverage_empty_database(
        self,
        backfill_service: BackfillService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test coverage analysis with empty database."""
        # Mock repository to return no data points
        mock_repository.get_by_time_range.return_value = []

        results = await backfill_service.analyze_coverage(
            areas=[AreaCode.GERMANY], endpoints=["actual_load"], years_back=1
        )

        assert len(results) == 1
        result = results[0]
        assert result.coverage_percentage == 0.0
        assert result.needs_backfill is True
        assert result.actual_data_points == 0
        assert result.expected_data_points > 0

    @pytest.mark.asyncio
    async def test_analyze_coverage_repository_error(
        self,
        backfill_service: BackfillService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test coverage analysis with repository error."""
        # Mock repository to raise an exception
        mock_repository.get_by_time_range.side_effect = Exception("Database error")

        with pytest.raises(BackfillCoverageError) as exc_info:
            await backfill_service.analyze_coverage(
                areas=[AreaCode.GERMANY], endpoints=["actual_load"]
            )

        error = exc_info.value
        assert "Coverage analysis failed" in str(error)
        assert error.area_code == "DE"
        assert error.endpoint_name == "actual_load"

    # Backfill Operation Tests

    @pytest.mark.asyncio
    async def test_start_backfill_success(
        self,
        backfill_service: BackfillService,
        mock_collector: AsyncMock,
        mock_processor: AsyncMock,
        mock_repository: AsyncMock,
        sample_period_start: datetime,
        sample_period_end: datetime,
    ) -> None:
        """Test successful backfill operation."""
        # Mock collector to return documents
        mock_document = MagicMock()
        mock_collector.get_actual_total_load.return_value = mock_document

        # Mock processor to return data points
        mock_data_points = [MagicMock()] * 10
        mock_processor.process.return_value = mock_data_points

        # Mock repository for upsert
        mock_repository.upsert_batch.return_value = mock_data_points

        # Mock the _collect_chunk_data method to return a valid data point count
        async def mock_collect_chunk_data(*_args: Any, **_kwargs: Any) -> int:
            return 100

        with patch.object(
            backfill_service, "_collect_chunk_data", side_effect=mock_collect_chunk_data
        ):
            result = await backfill_service.start_backfill(
                area_code="DE",
                endpoint_name="actual_load",
                period_start=sample_period_start,
                period_end=sample_period_end,
                chunk_size_days=30,
            )

        assert isinstance(result, BackfillResult)
        assert result.success is True
        assert result.area_code == "DE"
        assert result.endpoint_name == "actual_load"
        assert result.data_points_collected > 0
        assert result.chunks_processed > 0
        assert result.chunks_failed == 0

    @pytest.mark.asyncio
    async def test_start_backfill_resource_limit_exceeded(
        self,
        backfill_service: BackfillService,
        sample_period_start: datetime,
        sample_period_end: datetime,
    ) -> None:
        """Test backfill operation when resource limits are exceeded."""
        # Fill up active operations to exceed limit
        backfill_service._active_operations = {
            "op1": MagicMock(),
            "op2": MagicMock(),
        }  # Config max is 2, so adding one more should fail

        with pytest.raises(BackfillResourceError) as exc_info:
            await backfill_service.start_backfill(
                area_code="DE",
                endpoint_name="actual_load",
                period_start=sample_period_start,
                period_end=sample_period_end,
            )

        error = exc_info.value
        assert error.resource_type == "concurrent_operations"
        assert error.limit_value == 2
        assert error.current_value == 2

    @pytest.mark.asyncio
    async def test_start_backfill_collector_failure(
        self,
        backfill_service: BackfillService,
        mock_collector: AsyncMock,
        sample_period_start: datetime,
        sample_period_end: datetime,
    ) -> None:
        """Test backfill operation with collector failure."""
        # Mock collector to raise an exception
        mock_collector.get_actual_total_load.side_effect = Exception("API error")

        # For this test, we expect the _collect_chunk_data to be called and fail
        # so we don't need to mock it - the real method will be called and fail
        result = await backfill_service.start_backfill(
            area_code="DE",
            endpoint_name="actual_load",
            period_start=sample_period_start,
            period_end=sample_period_end,
            chunk_size_days=30,
        )

        assert isinstance(result, BackfillResult)
        assert result.success is False
        assert result.chunks_failed > 0
        assert len(result.error_messages) > 0

    # Resume Backfill Tests

    @pytest.mark.asyncio
    async def test_resume_backfill_success(
        self,
        backfill_service: BackfillService,
        mock_collector: AsyncMock,
        mock_processor: AsyncMock,
        mock_repository: AsyncMock,
        mock_progress_repository: AsyncMock,
    ) -> None:
        """Test successful backfill resume operation."""
        # Mock progress record that can be resumed
        mock_progress = BackfillProgress(
            id=1,
            area_code="DE",
            endpoint_name="actual_load",
            period_start=datetime(2022, 1, 1, tzinfo=UTC),
            period_end=datetime(2022, 2, 1, tzinfo=UTC),
            status=BackfillStatus.FAILED,
            total_chunks=4,
            completed_chunks=2,
            failed_chunks=0,
            total_data_points=500,
            chunk_size_days=7,
            rate_limit_delay=Decimal("1.0"),
        )

        # Mock progress repository to return progress
        mock_progress_repository.get_by_id.return_value = mock_progress

        # Mock collector and processor
        mock_collector.get_actual_total_load.return_value = MagicMock()
        mock_processor.process.return_value = [MagicMock()] * 5
        mock_repository.upsert_batch.return_value = [MagicMock()] * 5

        # Mock the _collect_chunk_data method to return a valid data point count
        async def mock_collect_chunk_data(*_args: Any, **_kwargs: Any) -> int:
            return 100

        with patch.object(
            backfill_service, "_collect_chunk_data", side_effect=mock_collect_chunk_data
        ):
            result = await backfill_service.resume_backfill(backfill_id=1)

        assert isinstance(result, BackfillResult)
        assert result.success is True
        assert result.backfill_id == 1

    @pytest.mark.asyncio
    async def test_resume_backfill_cannot_be_resumed(
        self,
        backfill_service: BackfillService,
        mock_progress_repository: AsyncMock,
    ) -> None:
        """Test resume backfill when operation cannot be resumed."""
        # Mock progress record that cannot be resumed
        mock_progress = BackfillProgress(
            id=1,
            area_code="DE",
            endpoint_name="actual_load",
            period_start=datetime(2022, 1, 1, tzinfo=UTC),
            period_end=datetime(2022, 2, 1, tzinfo=UTC),
            status=BackfillStatus.COMPLETED,
            total_chunks=4,
            completed_chunks=4,
            chunk_size_days=7,
            rate_limit_delay=Decimal("1.0"),
        )

        # Mock progress repository to return progress
        mock_progress_repository.get_by_id.return_value = mock_progress

        with pytest.raises(BackfillProgressError) as exc_info:
            await backfill_service.resume_backfill(backfill_id=1)

        error = exc_info.value
        assert "cannot be resumed" in str(error)
        assert error.backfill_id == "1"

    @pytest.mark.asyncio
    async def test_resume_backfill_not_found(
        self,
        backfill_service: BackfillService,
        mock_progress_repository: AsyncMock,
    ) -> None:
        """Test resume backfill when progress record is not found."""

        # Mock progress repository to return None
        mock_progress_repository.get_by_id.return_value = None

        with pytest.raises(BackfillProgressError) as exc_info:
            await backfill_service.resume_backfill(backfill_id=999)

        error = exc_info.value
        assert "not found" in str(error)
        assert error.backfill_id == "999"

    # Status and Monitoring Tests

    @pytest.mark.asyncio
    async def test_get_backfill_status_success(
        self,
        backfill_service: BackfillService,
        mock_progress_repository: AsyncMock,
    ) -> None:
        """Test getting backfill status successfully."""
        # Mock progress record
        mock_progress = BackfillProgress(
            id=1,
            area_code="DE",
            endpoint_name="actual_load",
            period_start=datetime(2022, 1, 1, tzinfo=UTC),
            period_end=datetime(2022, 2, 1, tzinfo=UTC),
            status=BackfillStatus.FAILED,
            progress_percentage=Decimal("50.00"),
            total_chunks=4,
            completed_chunks=2,
            failed_chunks=0,
            total_data_points=1000,
            chunk_size_days=7,
            rate_limit_delay=Decimal("1.0"),
            started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        )

        # Mock progress repository to return progress
        mock_progress_repository.get_by_id.return_value = mock_progress

        status = await backfill_service.get_backfill_status(backfill_id=1)

        assert status["backfill_id"] == 1
        assert status["area_code"] == "DE"
        assert status["endpoint_name"] == "actual_load"
        assert status["status"] == "failed"
        assert status["progress_percentage"] == 50.0
        assert status["total_chunks"] == 4
        assert status["completed_chunks"] == 2
        assert status["remaining_chunks"] == 2
        assert status["is_active"] is False
        assert status["can_be_resumed"] is True

    @pytest.mark.asyncio
    async def test_list_active_backfills_success(
        self,
        backfill_service: BackfillService,
        mock_progress_repository: AsyncMock,
    ) -> None:
        """Test listing active backfills successfully using repository pattern."""
        # Mock active progress records
        mock_progresses = [
            BackfillProgress(
                id=1,
                area_code="DE",
                endpoint_name="actual_load",
                period_start=datetime(2022, 1, 1, tzinfo=UTC),
                period_end=datetime(2022, 2, 1, tzinfo=UTC),
                status=BackfillStatus.IN_PROGRESS,
                progress_percentage=Decimal("25.00"),
                completed_chunks=2,
                total_chunks=8,
                total_data_points=500,
                failed_chunks=0,
                chunk_size_days=7,
                rate_limit_delay=Decimal("1.0"),
                started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            ),
            BackfillProgress(
                id=2,
                area_code="FR",
                endpoint_name="day_ahead_forecast",
                period_start=datetime(2022, 1, 1, tzinfo=UTC),
                period_end=datetime(2022, 2, 1, tzinfo=UTC),
                status=BackfillStatus.PENDING,
                progress_percentage=Decimal("0.00"),
                completed_chunks=0,
                total_chunks=8,
                total_data_points=0,
                failed_chunks=0,
                chunk_size_days=7,
                rate_limit_delay=Decimal("1.0"),
            ),
        ]

        # Mock repository method instead of direct database access
        mock_progress_repository.get_active_backfills.return_value = mock_progresses

        summaries = await backfill_service.list_active_backfills()

        assert len(summaries) == 2

        # Check first summary
        summary1 = summaries[0]
        assert summary1["backfill_id"] == 1
        assert summary1["area_code"] == "DE"
        assert summary1["endpoint_name"] == "actual_load"
        assert summary1["status"] == "in_progress"
        assert summary1["progress_percentage"] == 25.0

        # Check second summary
        summary2 = summaries[1]
        assert summary2["backfill_id"] == 2
        assert summary2["area_code"] == "FR"
        assert summary2["endpoint_name"] == "day_ahead_forecast"
        assert summary2["status"] == "pending"
        assert summary2["progress_percentage"] == 0.0

    @pytest.mark.asyncio
    async def test_list_active_backfills_empty(
        self,
        backfill_service: BackfillService,
        mock_progress_repository: AsyncMock,
    ) -> None:
        """Test listing active backfills when none exist using repository pattern."""
        # Mock repository method to return empty list
        mock_progress_repository.get_active_backfills.return_value = []

        summaries = await backfill_service.list_active_backfills()

        assert len(summaries) == 0

    # Helper Method Tests

    def test_create_time_chunks(self, backfill_service: BackfillService) -> None:
        """Test time chunk creation."""
        start_time = datetime(2022, 1, 1, tzinfo=UTC)
        end_time = datetime(2022, 3, 1, tzinfo=UTC)  # 2 months
        chunk_size_days = 30

        chunks = backfill_service._create_time_chunks(
            start_time, end_time, chunk_size_days
        )

        assert len(chunks) == 2  # Should create 2 chunks

        # Check first chunk
        assert chunks[0][0] == start_time
        assert chunks[0][1] == datetime(2022, 1, 31, tzinfo=UTC)

        # Check second chunk
        assert chunks[1][0] == datetime(2022, 1, 31, tzinfo=UTC)
        assert chunks[1][1] == end_time

    def test_create_time_chunks_single_chunk(
        self, backfill_service: BackfillService
    ) -> None:
        """Test time chunk creation with period smaller than chunk size."""
        start_time = datetime(2022, 1, 1, tzinfo=UTC)
        end_time = datetime(2022, 1, 15, tzinfo=UTC)  # 15 days
        chunk_size_days = 30

        chunks = backfill_service._create_time_chunks(
            start_time, end_time, chunk_size_days
        )

        assert len(chunks) == 1
        assert chunks[0][0] == start_time
        assert chunks[0][1] == end_time

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_analyze_coverage_invalid_endpoint(
        self,
        backfill_service: BackfillService,
    ) -> None:
        """Test coverage analysis with invalid endpoint name."""
        with pytest.raises(BackfillCoverageError) as exc_info:
            await backfill_service.analyze_coverage(
                areas=[AreaCode.GERMANY], endpoints=["invalid_endpoint"]
            )

        error = exc_info.value
        assert "Coverage analysis failed for DE/invalid_endpoint" in str(error)

    @pytest.mark.asyncio
    async def test_start_backfill_invalid_area_code(
        self,
        backfill_service: BackfillService,
        sample_period_start: datetime,
        sample_period_end: datetime,
    ) -> None:
        """Test start backfill with invalid area code."""
        result = await backfill_service.start_backfill(
            area_code="INVALID",
            endpoint_name="actual_load",
            period_start=sample_period_start,
            period_end=sample_period_end,
        )

        # Should complete but with failures
        assert isinstance(result, BackfillResult)
        assert result.success is False
        assert result.chunks_failed > 0
        assert len(result.error_messages) > 0

    @pytest.mark.asyncio
    async def test_start_backfill_invalid_endpoint(
        self,
        backfill_service: BackfillService,
        sample_period_start: datetime,
        sample_period_end: datetime,
    ) -> None:
        """Test start backfill with invalid endpoint name."""
        result = await backfill_service.start_backfill(
            area_code="DE",
            endpoint_name="invalid_endpoint",
            period_start=sample_period_start,
            period_end=sample_period_end,
        )

        # Should complete but with failures
        assert isinstance(result, BackfillResult)
        assert result.success is False
        assert result.chunks_failed > 0
        assert len(result.error_messages) > 0


class TestCoverageAnalysis:
    """Test suite for CoverageAnalysis class."""

    def test_coverage_analysis_creation(self) -> None:
        """Test creating a coverage analysis result."""
        from app.services.backfill_service import CoverageAnalysisParams

        params = CoverageAnalysisParams(
            area_code="DE",
            endpoint_name="actual_load",
            analysis_period_start=datetime(2022, 1, 1, tzinfo=UTC),
            analysis_period_end=datetime(2023, 1, 1, tzinfo=UTC),
            expected_data_points=1000,
            actual_data_points=950,
            coverage_percentage=95.0,
            missing_periods=[
                (datetime(2022, 6, 1, tzinfo=UTC), datetime(2022, 6, 2, tzinfo=UTC))
            ],
        )
        analysis = CoverageAnalysis(params)

        assert analysis.area_code == "DE"
        assert analysis.endpoint_name == "actual_load"
        assert analysis.expected_data_points == 1000
        assert analysis.actual_data_points == 950
        assert analysis.coverage_percentage == 95.0
        assert analysis.needs_backfill is False  # 95% is above threshold
        assert analysis.total_missing_points == 50

    def test_coverage_analysis_needs_backfill(self) -> None:
        """Test coverage analysis that needs backfill."""
        from app.services.backfill_service import CoverageAnalysisParams

        params = CoverageAnalysisParams(
            area_code="DE",
            endpoint_name="actual_load",
            analysis_period_start=datetime(2022, 1, 1, tzinfo=UTC),
            analysis_period_end=datetime(2023, 1, 1, tzinfo=UTC),
            expected_data_points=1000,
            actual_data_points=900,  # 90% coverage
            coverage_percentage=90.0,
            missing_periods=[],
        )
        analysis = CoverageAnalysis(params)

        assert analysis.needs_backfill is True  # 90% is below threshold
        assert analysis.total_missing_points == 100

    def test_coverage_analysis_to_dict(self) -> None:
        """Test coverage analysis to_dict method."""
        from app.services.backfill_service import CoverageAnalysisParams

        params = CoverageAnalysisParams(
            area_code="DE",
            endpoint_name="actual_load",
            analysis_period_start=datetime(2022, 1, 1, tzinfo=UTC),
            analysis_period_end=datetime(2023, 1, 1, tzinfo=UTC),
            expected_data_points=1000,
            actual_data_points=950,
            coverage_percentage=95.0,
            missing_periods=[
                (datetime(2022, 6, 1, tzinfo=UTC), datetime(2022, 6, 2, tzinfo=UTC))
            ],
        )
        analysis = CoverageAnalysis(params)

        result = analysis.to_dict()

        assert result["area_code"] == "DE"
        assert result["endpoint_name"] == "actual_load"
        assert result["expected_data_points"] == 1000
        assert result["actual_data_points"] == 950
        assert result["coverage_percentage"] == 95.0
        assert result["needs_backfill"] is False
        assert result["total_missing_points"] == 50
        assert result["missing_periods_count"] == 1


class TestBackfillResult:
    """Test suite for BackfillResult class."""

    def test_backfill_result_creation(self) -> None:
        """Test creating a backfill result."""
        from app.services.backfill_service import BackfillResultParams

        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 12, 30, 0, tzinfo=UTC)

        params = BackfillResultParams(
            backfill_id=1,
            area_code="DE",
            endpoint_name="actual_load",
            success=True,
            data_points_collected=1000,
            chunks_processed=4,
            chunks_failed=0,
            start_time=start_time,
            end_time=end_time,
            error_messages=[],
        )
        result = BackfillResult(params)

        assert result.backfill_id == 1
        assert result.area_code == "DE"
        assert result.endpoint_name == "actual_load"
        assert result.success is True
        assert result.data_points_collected == 1000
        assert result.chunks_processed == 4
        assert result.chunks_failed == 0
        assert result.duration_seconds == 1800.0  # 30 minutes
        assert result.success_rate == 100.0

    def test_backfill_result_with_failures(self) -> None:
        """Test backfill result with some failures."""
        from app.services.backfill_service import BackfillResultParams

        params = BackfillResultParams(
            backfill_id=1,
            area_code="DE",
            endpoint_name="actual_load",
            success=False,
            data_points_collected=800,
            chunks_processed=3,
            chunks_failed=1,
            start_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            end_time=datetime(2024, 1, 1, 12, 30, 0, tzinfo=UTC),
            error_messages=["Chunk 4 failed: API error"],
        )
        result = BackfillResult(params)

        assert result.success is False
        assert result.success_rate == 75.0  # 3 out of 4 total chunks
        assert len(result.error_messages) == 1

    def test_backfill_result_to_dict(self) -> None:
        """Test backfill result to_dict method."""
        from app.services.backfill_service import BackfillResultParams

        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 1, 12, 30, 0, tzinfo=UTC)

        params = BackfillResultParams(
            backfill_id=1,
            area_code="DE",
            endpoint_name="actual_load",
            success=True,
            data_points_collected=1000,
            chunks_processed=4,
            chunks_failed=0,
            start_time=start_time,
            end_time=end_time,
            error_messages=[],
        )
        result = BackfillResult(params)

        result_dict = result.to_dict()

        assert result_dict["backfill_id"] == 1
        assert result_dict["area_code"] == "DE"
        assert result_dict["success"] is True
        assert result_dict["data_points_collected"] == 1000
        assert result_dict["success_rate"] == 100.0
        assert result_dict["duration_seconds"] == 1800.0
        assert result_dict["error_count"] == 0
