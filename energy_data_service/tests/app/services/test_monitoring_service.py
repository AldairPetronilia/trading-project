"""
Unit tests for MonitoringService.

This module provides comprehensive unit tests for the MonitoringService class,
covering collection tracking, performance analysis, anomaly detection, trend analysis,
and error handling scenarios.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.config.settings import MonitoringConfig
from app.exceptions.service_exceptions import ServiceError
from app.models.collection_metrics import CollectionMetrics
from app.models.load_data import EnergyDataType
from app.services.monitoring_service import MonitoringError, MonitoringService


class TestMonitoringService:
    """Test suite for MonitoringService."""

    @pytest.fixture
    def mock_metrics_repository(self) -> AsyncMock:
        """Create a mock collection metrics repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_database(self) -> AsyncMock:
        """Create a mock database."""
        return AsyncMock()

    @pytest.fixture
    def monitoring_config(self) -> MonitoringConfig:
        """Create a monitoring configuration."""
        return MonitoringConfig(
            metrics_retention_days=30,
            performance_threshold_ms=5000.0,
            success_rate_threshold=0.95,
            anomaly_detection_enabled=True,
        )

    @pytest.fixture
    def monitoring_service(
        self,
        mock_metrics_repository: AsyncMock,
        mock_database: AsyncMock,
        monitoring_config: MonitoringConfig,
    ) -> MonitoringService:
        """Create a MonitoringService with mocked dependencies."""
        return MonitoringService(
            metrics_repository=mock_metrics_repository,
            database=mock_database,
            config=monitoring_config,
        )

    @pytest.fixture
    def sample_collection_result(self) -> MagicMock:
        """Create a sample collection result for testing."""
        result = MagicMock()
        result.job_id = "test_job_123"
        result.start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        result.end_time = datetime(2024, 1, 1, 12, 30, 0, tzinfo=UTC)

        # Create mock area results
        area_result = MagicMock()
        area_result.area_code = "DE"
        area_result.data_type = EnergyDataType.ACTUAL
        area_result.points_collected = 100
        area_result.success = True
        area_result.error_message = None
        area_result.api_response_time_ms = 1500.0
        area_result.processing_time_ms = 500.0

        result.area_results = [area_result]
        return result

    @pytest.fixture
    def sample_metrics_list(self) -> list[CollectionMetrics]:
        """Create a sample list of collection metrics."""
        metrics = []
        for i in range(5):
            metric = CollectionMetrics(
                id=i + 1,
                job_id=f"job_{i + 1}",
                area_code="DE",
                data_type=EnergyDataType.ACTUAL,
                collection_start=datetime(2024, 1, 1, 12, i, 0, tzinfo=UTC),
                collection_end=datetime(2024, 1, 1, 12, i + 1, 0, tzinfo=UTC),
                points_collected=100,
                success=True,
                api_response_time=1000.0 + (i * 100),
                processing_time=200.0 + (i * 50),
            )
            metrics.append(metric)
        return metrics

    # Collection Result Tracking Tests
    # Note: Complex database transaction tests are covered by integration tests

    @pytest.mark.asyncio
    async def test_track_collection_result_invalid_format(
        self,
        monitoring_service: MonitoringService,
    ) -> None:
        """Test tracking collection result with invalid format."""
        # Result without required attributes
        invalid_result = MagicMock()
        invalid_result.job_id = "test_job"
        # Missing area_results attribute
        del invalid_result.area_results

        with pytest.raises(MonitoringError) as exc_info:
            await monitoring_service.track_collection_result(invalid_result)

        error = exc_info.value
        assert "Invalid collection result format" in str(error)
        assert error.service_name == "MonitoringService"
        assert error.operation == "track_collection_result"

    @pytest.mark.asyncio
    async def test_track_collection_result_database_error(
        self,
        mock_metrics_repository: AsyncMock,
        mock_database: AsyncMock,
        monitoring_config: MonitoringConfig,
        sample_collection_result: MagicMock,
    ) -> None:
        """Test tracking collection result with database error."""
        # Create the service without using the fixture to avoid conflicts
        monitoring_service = MonitoringService(
            metrics_repository=mock_metrics_repository,
            database=mock_database,
            config=monitoring_config,
        )

        # Mock the database session_factory to raise an error
        mock_database.session_factory.side_effect = Exception(
            "Database connection failed"
        )

        with pytest.raises(MonitoringError) as exc_info:
            await monitoring_service.track_collection_result(sample_collection_result)

        error = exc_info.value
        assert "Failed to track collection result" in str(error)
        assert error.service_name == "MonitoringService"
        assert error.operation == "track_collection_result"
        assert error.context["job_id"] == "test_job_123"

    # Success Rate Calculation Tests

    @pytest.mark.asyncio
    async def test_calculate_success_rates_success(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
        sample_metrics_list: list[CollectionMetrics],
    ) -> None:
        """Test successful success rate calculation."""
        # Add one failed metric to the sample list
        failed_metric = CollectionMetrics(
            id=6,
            job_id="job_6",
            area_code="FR",
            data_type=EnergyDataType.DAY_AHEAD,
            collection_start=datetime(2024, 1, 1, 12, 5, 0, tzinfo=UTC),
            collection_end=datetime(2024, 1, 1, 12, 6, 0, tzinfo=UTC),
            points_collected=0,
            success=False,
            error_message="API timeout",
        )
        test_metrics = [*sample_metrics_list, failed_metric]

        mock_metrics_repository.get_by_time_range.return_value = test_metrics

        period = timedelta(hours=1)
        success_rates = await monitoring_service.calculate_success_rates(period)

        # Should have success rates for both combinations
        assert "DE/actual" in success_rates
        assert "FR/day_ahead" in success_rates

        # DE/actual: 5 successful out of 5 = 100%
        assert success_rates["DE/actual"] == 1.0

        # FR/day_ahead: 0 successful out of 1 = 0%
        assert success_rates["FR/day_ahead"] == 0.0

        # Verify repository was called with correct time range
        mock_metrics_repository.get_by_time_range.assert_called_once()
        call_args = mock_metrics_repository.get_by_time_range.call_args[1]
        assert "start_time" in call_args
        assert "end_time" in call_args

    @pytest.mark.asyncio
    async def test_calculate_success_rates_empty_data(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test success rate calculation with no data."""
        mock_metrics_repository.get_by_time_range.return_value = []

        period = timedelta(hours=1)
        success_rates = await monitoring_service.calculate_success_rates(period)

        assert success_rates == {}

    @pytest.mark.asyncio
    async def test_calculate_success_rates_repository_error(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test success rate calculation with repository error."""
        mock_metrics_repository.get_by_time_range.side_effect = Exception(
            "Database error"
        )

        period = timedelta(hours=1)

        with pytest.raises(MonitoringError) as exc_info:
            await monitoring_service.calculate_success_rates(period)

        error = exc_info.value
        assert "Failed to calculate success rates" in str(error)
        assert error.operation == "calculate_success_rates"

    # Performance Metrics Tests

    @pytest.mark.asyncio
    async def test_get_performance_metrics_success(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
        sample_metrics_list: list[CollectionMetrics],
    ) -> None:
        """Test successful performance metrics retrieval."""
        # Mock repository responses
        performance_data = {
            "avg_api_response_time": 1200.0,
            "min_api_response_time": 1000.0,
            "max_api_response_time": 1400.0,
            "avg_processing_time": 225.0,
            "min_processing_time": 200.0,
            "max_processing_time": 250.0,
        }
        mock_metrics_repository.get_performance_metrics.return_value = performance_data
        mock_metrics_repository.get_by_time_range.return_value = sample_metrics_list

        period = timedelta(hours=1)
        metrics = await monitoring_service.get_performance_metrics(period)

        # Check enhanced metrics
        assert metrics["avg_api_response_time"] == 1200.0
        assert metrics["total_operations"] == 5
        assert metrics["successful_operations"] == 5
        assert metrics["failed_operations"] == 0
        assert metrics["overall_success_rate"] == 1.0
        assert "period_start" in metrics
        assert "period_end" in metrics
        assert metrics["period_duration_seconds"] == 3600.0

    @pytest.mark.asyncio
    async def test_get_performance_metrics_mixed_success(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test performance metrics with mixed success/failure operations."""
        # Create metrics with mixed success
        mixed_metrics = []
        for i in range(4):
            metric = CollectionMetrics(
                id=i + 1,
                job_id=f"job_{i + 1}",
                area_code="DE",
                data_type=EnergyDataType.ACTUAL,
                collection_start=datetime(2024, 1, 1, 12, i, 0, tzinfo=UTC),
                collection_end=datetime(2024, 1, 1, 12, i + 1, 0, tzinfo=UTC),
                points_collected=100 if i < 3 else 0,  # Last one failed
                success=i < 3,  # First 3 successful, last one failed
            )
            mixed_metrics.append(metric)

        performance_data = {
            "avg_api_response_time": 1100.0,
            "min_api_response_time": 1000.0,
            "max_api_response_time": 1200.0,
            "avg_processing_time": 200.0,
            "min_processing_time": 150.0,
            "max_processing_time": 250.0,
        }
        mock_metrics_repository.get_performance_metrics.return_value = performance_data
        mock_metrics_repository.get_by_time_range.return_value = mixed_metrics

        period = timedelta(hours=1)
        metrics = await monitoring_service.get_performance_metrics(period)

        assert metrics["total_operations"] == 4
        assert metrics["successful_operations"] == 3
        assert metrics["failed_operations"] == 1
        assert metrics["overall_success_rate"] == 0.75

    @pytest.mark.asyncio
    async def test_get_performance_metrics_repository_error(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test performance metrics with repository error."""
        mock_metrics_repository.get_performance_metrics.side_effect = Exception(
            "Database error"
        )

        period = timedelta(hours=1)

        with pytest.raises(MonitoringError) as exc_info:
            await monitoring_service.get_performance_metrics(period)

        error = exc_info.value
        assert "Failed to get performance metrics" in str(error)
        assert error.operation == "get_performance_metrics"

    # Recent Metrics Tests

    @pytest.mark.asyncio
    async def test_get_recent_metrics_success(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
        sample_metrics_list: list[CollectionMetrics],
    ) -> None:
        """Test successful recent metrics retrieval."""
        mock_metrics_repository.get_recent_metrics.return_value = sample_metrics_list

        recent_metrics = await monitoring_service.get_recent_metrics(30)

        assert len(recent_metrics) == 5
        assert all(isinstance(metric, CollectionMetrics) for metric in recent_metrics)
        mock_metrics_repository.get_recent_metrics.assert_called_once_with(30)

    @pytest.mark.asyncio
    async def test_get_recent_metrics_empty(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test recent metrics retrieval with no data."""
        mock_metrics_repository.get_recent_metrics.return_value = []

        recent_metrics = await monitoring_service.get_recent_metrics(30)

        assert recent_metrics == []

    @pytest.mark.asyncio
    async def test_get_recent_metrics_repository_error(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test recent metrics with repository error."""
        mock_metrics_repository.get_recent_metrics.side_effect = Exception(
            "Database error"
        )

        with pytest.raises(MonitoringError) as exc_info:
            await monitoring_service.get_recent_metrics(30)

        error = exc_info.value
        assert "Failed to get recent metrics" in str(error)
        assert error.operation == "get_recent_metrics"

    # Anomaly Detection Tests

    @pytest.mark.asyncio
    async def test_detect_anomalies_disabled(
        self,
        monitoring_service: MonitoringService,
    ) -> None:
        """Test anomaly detection when disabled in configuration."""
        # Disable anomaly detection
        monitoring_service._config.anomaly_detection_enabled = False

        period = timedelta(hours=1)
        result = await monitoring_service.detect_anomalies(
            "DE", EnergyDataType.ACTUAL, period
        )

        assert result["anomaly_detection_enabled"] is False
        assert "disabled in configuration" in result["message"]

    @pytest.mark.asyncio
    async def test_detect_anomalies_no_data(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test anomaly detection with no data available."""
        mock_metrics_repository.get_by_time_range.return_value = []

        period = timedelta(hours=1)
        result = await monitoring_service.detect_anomalies(
            "DE", EnergyDataType.ACTUAL, period
        )

        assert result["anomaly_detection_enabled"] is True
        assert result["area_code"] == "DE"
        assert result["data_type"] == "actual"
        assert result["anomalies_detected"] == []
        assert "No data available" in result["message"]

    @pytest.mark.asyncio
    async def test_detect_anomalies_low_success_rate(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test anomaly detection with low success rate."""
        # Create metrics with low success rate (2 out of 5 successful = 40%)
        failed_metrics = []
        for i in range(5):
            metric = CollectionMetrics(
                id=i + 1,
                job_id=f"job_{i + 1}",
                area_code="DE",
                data_type=EnergyDataType.ACTUAL,
                collection_start=datetime(2024, 1, 1, 12, i, 0, tzinfo=UTC),
                collection_end=datetime(2024, 1, 1, 12, i + 1, 0, tzinfo=UTC),
                points_collected=100 if i < 2 else 0,
                success=i < 2,  # Only first 2 successful
                api_response_time=1000.0,
            )
            failed_metrics.append(metric)

        mock_metrics_repository.get_by_time_range.return_value = failed_metrics

        period = timedelta(hours=1)
        result = await monitoring_service.detect_anomalies(
            "DE", EnergyDataType.ACTUAL, period
        )

        assert result["anomaly_detection_enabled"] is True
        assert result["success_rate"] == 0.4
        assert len(result["anomalies_detected"]) >= 1

        # Check for low success rate anomaly
        anomalies = result["anomalies_detected"]
        low_success_anomaly = next(
            (a for a in anomalies if a["type"] == "low_success_rate"), None
        )
        assert low_success_anomaly is not None
        assert low_success_anomaly["severity"] == "high"  # < 0.8
        assert low_success_anomaly["value"] == 0.4

    @pytest.mark.asyncio
    async def test_detect_anomalies_high_response_time(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
        monitoring_config: MonitoringConfig,
    ) -> None:
        """Test anomaly detection with high response times."""
        # Create metrics with high response times (above threshold of 5000ms)
        slow_metrics = []
        for i in range(3):
            metric = CollectionMetrics(
                id=i + 1,
                job_id=f"job_{i + 1}",
                area_code="DE",
                data_type=EnergyDataType.ACTUAL,
                collection_start=datetime(2024, 1, 1, 12, i, 0, tzinfo=UTC),
                collection_end=datetime(2024, 1, 1, 12, i + 1, 0, tzinfo=UTC),
                points_collected=100,
                success=True,
                api_response_time=6000.0,  # Above 5000ms threshold
            )
            slow_metrics.append(metric)

        mock_metrics_repository.get_by_time_range.return_value = slow_metrics

        period = timedelta(hours=1)
        result = await monitoring_service.detect_anomalies(
            "DE", EnergyDataType.ACTUAL, period
        )

        anomalies = result["anomalies_detected"]
        high_response_anomaly = next(
            (a for a in anomalies if a["type"] == "high_response_time"), None
        )
        assert high_response_anomaly is not None
        assert high_response_anomaly["severity"] == "medium"
        assert high_response_anomaly["value"] == 6000.0
        assert (
            high_response_anomaly["threshold"]
            == monitoring_config.performance_threshold_ms
        )

    @pytest.mark.asyncio
    async def test_detect_anomalies_no_operations(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test anomaly detection when no operations occurred."""
        # Return empty list to simulate no data collection
        mock_metrics_repository.get_by_time_range.return_value = []

        period = timedelta(hours=1)
        result = await monitoring_service.detect_anomalies(
            "DE", EnergyDataType.ACTUAL, period
        )

        # This should be handled by the "no data available" path, not the anomaly path
        assert result["anomalies_detected"] == []
        assert "No data available" in result["message"]

    @pytest.mark.asyncio
    async def test_detect_anomalies_repository_error(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test anomaly detection with repository error."""
        mock_metrics_repository.get_by_time_range.side_effect = Exception(
            "Database error"
        )

        period = timedelta(hours=1)

        with pytest.raises(MonitoringError) as exc_info:
            await monitoring_service.detect_anomalies(
                "DE", EnergyDataType.ACTUAL, period
            )

        error = exc_info.value
        assert "Failed to detect anomalies" in str(error)
        assert error.operation == "detect_anomalies"
        assert error.context["area_code"] == "DE"

    # Cleanup Tests

    @pytest.mark.asyncio
    async def test_cleanup_old_metrics_success(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test successful cleanup of old metrics."""
        mock_metrics_repository.cleanup_old_metrics.return_value = 15

        deleted_count = await monitoring_service.cleanup_old_metrics()

        assert deleted_count == 15
        mock_metrics_repository.cleanup_old_metrics.assert_called_once_with(
            retention_days=30  # From monitoring config
        )

    @pytest.mark.asyncio
    async def test_cleanup_old_metrics_repository_error(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test cleanup with repository error."""
        mock_metrics_repository.cleanup_old_metrics.side_effect = Exception(
            "Database error"
        )

        with pytest.raises(MonitoringError) as exc_info:
            await monitoring_service.cleanup_old_metrics()

        error = exc_info.value
        assert "Failed to cleanup old metrics" in str(error)
        assert error.operation == "cleanup_old_metrics"

    # Collection Trends Tests

    @pytest.mark.asyncio
    async def test_get_collection_trends_success(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test successful collection trends analysis."""
        # Create metrics across multiple days
        trend_metrics = []
        for day in range(5):
            for hour in range(3):  # 3 operations per day
                metric = CollectionMetrics(
                    id=day * 3 + hour + 1,
                    job_id=f"job_{day}_{hour}",
                    area_code="DE",
                    data_type=EnergyDataType.ACTUAL,
                    collection_start=datetime(
                        2024, 1, day + 1, hour + 10, 0, 0, tzinfo=UTC
                    ),
                    collection_end=datetime(
                        2024, 1, day + 1, hour + 11, 0, 0, tzinfo=UTC
                    ),
                    points_collected=100,
                    success=True,
                    api_response_time=1000.0,
                )
                trend_metrics.append(metric)

        mock_metrics_repository.get_by_time_range.return_value = trend_metrics

        trends = await monitoring_service.get_collection_trends(7)

        assert trends["period_days"] == 7
        assert trends["total_operations"] == 15  # 5 days * 3 operations
        assert trends["total_successful_operations"] == 15
        assert trends["total_points_collected"] == 1500  # 15 * 100
        assert trends["overall_success_rate"] == 1.0
        assert "daily_statistics" in trends
        assert "trend_direction" in trends

    @pytest.mark.asyncio
    async def test_get_collection_trends_no_data(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test collection trends with no data."""
        mock_metrics_repository.get_by_time_range.return_value = []

        trends = await monitoring_service.get_collection_trends(7)

        assert trends["period_days"] == 7
        assert trends["total_operations"] == 0
        assert "No data available" in trends["message"]

    @pytest.mark.asyncio
    async def test_get_collection_trends_insufficient_data_for_trend(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test collection trends with insufficient data for trend calculation."""
        # Create metrics for only 2 days (less than minimum 3 for trend)
        few_metrics = []
        for day in range(2):
            metric = CollectionMetrics(
                id=day + 1,
                job_id=f"job_{day}",
                area_code="DE",
                data_type=EnergyDataType.ACTUAL,
                collection_start=datetime(2024, 1, day + 1, 12, 0, 0, tzinfo=UTC),
                collection_end=datetime(2024, 1, day + 1, 13, 0, 0, tzinfo=UTC),
                points_collected=100,
                success=True,
            )
            few_metrics.append(metric)

        mock_metrics_repository.get_by_time_range.return_value = few_metrics

        trends = await monitoring_service.get_collection_trends(7)

        assert trends["trend_direction"] == "insufficient_data"
        assert trends["total_operations"] == 2

    @pytest.mark.asyncio
    async def test_get_collection_trends_repository_error(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test collection trends with repository error."""
        mock_metrics_repository.get_by_time_range.side_effect = Exception(
            "Database error"
        )

        with pytest.raises(MonitoringError) as exc_info:
            await monitoring_service.get_collection_trends(7)

        error = exc_info.value
        assert "Failed to get collection trends" in str(error)
        assert error.operation == "get_collection_trends"

    # System Health Tests

    @pytest.mark.asyncio
    async def test_get_system_health_summary_healthy(
        self,
        monitoring_service: MonitoringService,
        sample_metrics_list: list[CollectionMetrics],
    ) -> None:
        """Test system health summary when system is healthy."""
        # Mock performance metrics (good performance)
        performance_data = {
            "avg_api_response_time": 2000.0,  # Below 5000ms threshold
            "overall_success_rate": 0.98,  # Above 0.95 threshold
            "total_operations": 5,
            "successful_operations": 5,
            "failed_operations": 0,
        }

        # Mock the service's own methods
        with (
            patch.object(
                monitoring_service,
                "get_performance_metrics",
                return_value=performance_data,
            ),
            patch.object(
                monitoring_service,
                "get_recent_metrics",
                return_value=sample_metrics_list,
            ),
        ):
            health_summary = await monitoring_service.get_system_health_summary()

        health_assessment = health_summary["health_assessment"]
        assert health_assessment["overall_status"] == "healthy"
        assert health_assessment["performance_status"] == "good"
        assert health_assessment["availability_status"] == "good"
        assert health_assessment["data_quality_status"] == "good"
        assert len(health_assessment["status_reasons"]) == 0

    @pytest.mark.asyncio
    async def test_get_system_health_summary_degraded_performance(
        self,
        monitoring_service: MonitoringService,
        sample_metrics_list: list[CollectionMetrics],
    ) -> None:
        """Test system health summary with degraded performance."""
        # Mock performance metrics (poor performance)
        performance_data = {
            "avg_api_response_time": 7000.0,  # Above 5000ms threshold
            "overall_success_rate": 0.98,  # Good success rate
            "total_operations": 5,
            "successful_operations": 5,
            "failed_operations": 0,
        }

        with (
            patch.object(
                monitoring_service,
                "get_performance_metrics",
                return_value=performance_data,
            ),
            patch.object(
                monitoring_service,
                "get_recent_metrics",
                return_value=sample_metrics_list,
            ),
        ):
            health_summary = await monitoring_service.get_system_health_summary()

        health_assessment = health_summary["health_assessment"]
        assert health_assessment["overall_status"] == "degraded"
        assert health_assessment["performance_status"] == "degraded"
        assert health_assessment["availability_status"] == "good"
        assert len(health_assessment["status_reasons"]) == 1
        assert "High average response time" in health_assessment["status_reasons"][0]

    @pytest.mark.asyncio
    async def test_get_system_health_summary_low_availability(
        self,
        monitoring_service: MonitoringService,
        sample_metrics_list: list[CollectionMetrics],
    ) -> None:
        """Test system health summary with low availability."""
        # Mock performance metrics (low success rate)
        performance_data = {
            "avg_api_response_time": 2000.0,  # Good performance
            "overall_success_rate": 0.80,  # Below 0.95 threshold
            "total_operations": 5,
            "successful_operations": 4,
            "failed_operations": 1,
        }

        with (
            patch.object(
                monitoring_service,
                "get_performance_metrics",
                return_value=performance_data,
            ),
            patch.object(
                monitoring_service,
                "get_recent_metrics",
                return_value=sample_metrics_list,
            ),
        ):
            health_summary = await monitoring_service.get_system_health_summary()

        health_assessment = health_summary["health_assessment"]
        assert health_assessment["overall_status"] == "degraded"
        assert health_assessment["performance_status"] == "good"
        assert health_assessment["availability_status"] == "degraded"
        assert len(health_assessment["status_reasons"]) == 1
        assert "Low success rate" in health_assessment["status_reasons"][0]

    @pytest.mark.asyncio
    async def test_get_system_health_summary_no_recent_operations(
        self,
        monitoring_service: MonitoringService,
    ) -> None:
        """Test system health summary with no recent operations."""
        performance_data = {
            "avg_api_response_time": 2000.0,
            "overall_success_rate": 1.0,
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
        }

        with (
            patch.object(
                monitoring_service,
                "get_performance_metrics",
                return_value=performance_data,
            ),
            patch.object(monitoring_service, "get_recent_metrics", return_value=[]),
        ):
            health_summary = await monitoring_service.get_system_health_summary()

        health_assessment = health_summary["health_assessment"]
        assert health_assessment["overall_status"] == "degraded"
        assert health_assessment["data_quality_status"] == "degraded"
        assert (
            "No recent data collection operations"
            in health_assessment["status_reasons"]
        )

    @pytest.mark.asyncio
    async def test_get_system_health_summary_service_error(
        self,
        monitoring_service: MonitoringService,
    ) -> None:
        """Test system health summary with service error."""
        with (
            patch.object(
                monitoring_service,
                "get_performance_metrics",
                side_effect=Exception("Service error"),
            ),
            pytest.raises(MonitoringError) as exc_info,
        ):
            await monitoring_service.get_system_health_summary()

        error = exc_info.value
        assert "Failed to get system health summary" in str(error)
        assert error.operation == "get_system_health_summary"

    # Failure Pattern Analysis Tests

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_success(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test successful failure pattern analysis."""
        # Create mixed success/failure metrics
        failure_metrics = []
        areas = ["DE", "FR", "DE", "NL", "DE"]  # DE has most failures
        data_types = [EnergyDataType.ACTUAL, EnergyDataType.DAY_AHEAD] * 3
        success_flags = [True, False, False, True, False]  # 3 failures out of 5
        error_messages = [None, "Timeout", "APIError", None, "Timeout"]

        for i in range(5):
            metric = CollectionMetrics(
                id=i + 1,
                job_id=f"job_{i + 1}",
                area_code=areas[i],
                data_type=data_types[i % 2],
                collection_start=datetime(2024, 1, 1, 12, i, 0, tzinfo=UTC),
                collection_end=datetime(2024, 1, 1, 12, i + 1, 0, tzinfo=UTC),
                points_collected=100 if success_flags[i] else 0,
                success=success_flags[i],
                error_message=error_messages[i],
            )
            failure_metrics.append(metric)

        mock_metrics_repository.get_by_time_range.return_value = failure_metrics

        period = timedelta(hours=1)
        analysis = await monitoring_service.analyze_failure_patterns(period)

        assert analysis["total_operations"] == 5
        assert analysis["failed_operations"] == 3
        assert analysis["failure_rate"] == 0.6

        failure_patterns = analysis["failure_patterns"]
        assert "DE" in failure_patterns["by_area_code"]
        assert failure_patterns["by_area_code"]["DE"] == 2  # DE had 2 failures

        assert "Timeout" in failure_patterns["by_error_pattern"]
        assert failure_patterns["by_error_pattern"]["Timeout"] == 2  # 2 timeout errors

        # Check recommendations
        recommendations = analysis["recommendations"]
        assert len(recommendations) > 0
        assert any("DE" in rec for rec in recommendations)

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_no_data(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test failure pattern analysis with no data."""
        mock_metrics_repository.get_by_time_range.return_value = []

        period = timedelta(hours=1)
        analysis = await monitoring_service.analyze_failure_patterns(period)

        assert analysis["total_operations"] == 0
        assert "No data available" in analysis["message"]

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_no_failures(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
        sample_metrics_list: list[CollectionMetrics],
    ) -> None:
        """Test failure pattern analysis with no failures."""
        # All metrics are successful
        mock_metrics_repository.get_by_time_range.return_value = sample_metrics_list

        period = timedelta(hours=1)
        analysis = await monitoring_service.analyze_failure_patterns(period)

        assert analysis["total_operations"] == 5
        assert analysis["failed_operations"] == 0
        assert analysis["failure_rate"] == 0.0
        assert "No failures detected" in analysis["message"]

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_repository_error(
        self,
        monitoring_service: MonitoringService,
        mock_metrics_repository: AsyncMock,
    ) -> None:
        """Test failure pattern analysis with repository error."""
        mock_metrics_repository.get_by_time_range.side_effect = Exception(
            "Database error"
        )

        period = timedelta(hours=1)

        with pytest.raises(MonitoringError) as exc_info:
            await monitoring_service.analyze_failure_patterns(period)

        error = exc_info.value
        assert "Failed to analyze failure patterns" in str(error)
        assert error.operation == "analyze_failure_patterns"


class TestMonitoringError:
    """Test suite for MonitoringError exception."""

    def test_monitoring_error_creation(self) -> None:
        """Test creating a monitoring error."""
        error = MonitoringError(
            "Test error message",
            monitoring_operation="test_operation",
            context={"key": "value"},
        )

        assert str(error) == "Test error message"
        assert error.service_name == "MonitoringService"
        assert error.operation == "test_operation"
        assert error.context == {"key": "value"}

    def test_monitoring_error_inheritance(self) -> None:
        """Test that MonitoringError inherits from ServiceError."""
        error = MonitoringError("Test error")

        assert isinstance(error, ServiceError)
        assert error.service_name == "MonitoringService"
        assert error.operation == "unknown_monitoring_operation"

    def test_monitoring_error_with_defaults(self) -> None:
        """Test MonitoringError with default values."""
        error = MonitoringError("Test error")

        assert error.operation == "unknown_monitoring_operation"
        assert error.context == {}
