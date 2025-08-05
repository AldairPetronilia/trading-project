import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from app.config.settings import EntsoEDataCollectionConfig
from app.exceptions.collector_exceptions import CollectorError
from app.models.load_data import EnergyDataPoint, EnergyDataType
from app.services.entsoe_data_service import (
    CollectionResult,
    EndpointConfig,
    EndpointNames,
    EntsoEDataService,
)

from entsoe_client.client.entsoe_client_error import EntsoEClientError
from entsoe_client.http_client.exceptions import HttpClientError
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.business_type import BusinessType
from entsoe_client.model.load.gl_market_document import GlMarketDocument


@pytest.fixture
def mock_collector() -> AsyncMock:
    """Fixture for a mocked EntsoeCollector."""
    return AsyncMock()


@pytest.fixture
def mock_processor() -> AsyncMock:
    """Fixture for a mocked GlMarketDocumentProcessor."""
    return AsyncMock()


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Fixture for a mocked EnergyDataRepository."""
    mock = AsyncMock()
    # Make the mock iterable for the all() call in collect_all_gaps
    mock.__iter__ = MagicMock(return_value=iter([AreaCode.DE_LU, AreaCode.DE_AT_LU]))
    return mock


@pytest.fixture
def entsoe_data_collection_config() -> EntsoEDataCollectionConfig:
    """Fixture for an ENTSO-E data collection configuration."""
    return EntsoEDataCollectionConfig(target_areas=["DE-LU", "DE-AT-LU"])


@pytest.fixture
def entsoe_data_service(
    mock_collector: AsyncMock,
    mock_processor: AsyncMock,
    mock_repository: AsyncMock,
    entsoe_data_collection_config: EntsoEDataCollectionConfig,
) -> EntsoEDataService:
    """Fixture for an EntsoEDataService instance with mocked dependencies."""
    return EntsoEDataService(
        mock_collector, mock_processor, mock_repository, entsoe_data_collection_config
    )


class TestEndpointConfig:
    """Test cases for EndpointConfig class."""

    def test_backward_looking_config_creation(self) -> None:
        """Test creating a backward-looking endpoint configuration."""
        config = EndpointConfig(
            data_type=EnergyDataType.ACTUAL,
            expected_interval=timedelta(minutes=5),
            max_chunk_days=3,
            rate_limit_delay=1.0,
            is_forward_looking=False,
        )

        assert config.data_type == EnergyDataType.ACTUAL
        assert config.expected_interval == timedelta(minutes=5)
        assert config.max_chunk_days == 3
        assert config.rate_limit_delay == 1.0
        assert config.is_forward_looking is False
        assert config.forecast_horizon == timedelta(days=7)  # Default value

    def test_forward_looking_config_creation(self) -> None:
        """Test creating a forward-looking endpoint configuration."""
        forecast_horizon = timedelta(days=2)
        config = EndpointConfig(
            data_type=EnergyDataType.DAY_AHEAD,
            expected_interval=timedelta(minutes=15),
            max_chunk_days=7,
            rate_limit_delay=1.0,
            is_forward_looking=True,
            forecast_horizon=forecast_horizon,
        )

        assert config.data_type == EnergyDataType.DAY_AHEAD
        assert config.expected_interval == timedelta(minutes=15)
        assert config.max_chunk_days == 7
        assert config.rate_limit_delay == 1.0
        assert config.is_forward_looking is True
        assert config.forecast_horizon == forecast_horizon

    def test_forward_looking_config_without_horizon_raises_error(self) -> None:
        """Test that forward-looking config without forecast_horizon raises ValueError."""
        with pytest.raises(
            ValueError,
            match="forecast_horizon is required for forward-looking endpoint",
        ):
            EndpointConfig(
                data_type=EnergyDataType.DAY_AHEAD,
                expected_interval=timedelta(minutes=15),
                max_chunk_days=7,
                rate_limit_delay=1.0,
                is_forward_looking=True,
                # Missing forecast_horizon
            )

    def test_forward_looking_config_with_none_horizon_raises_error(self) -> None:
        """Test that forward-looking config with None forecast_horizon raises ValueError."""
        with pytest.raises(
            ValueError,
            match="forecast_horizon is required for forward-looking endpoint",
        ):
            EndpointConfig(
                data_type=EnergyDataType.DAY_AHEAD,
                expected_interval=timedelta(minutes=15),
                max_chunk_days=7,
                rate_limit_delay=1.0,
                is_forward_looking=True,
                forecast_horizon=None,
            )


class TestEntsoEDataServiceConfiguration:
    """Test cases for EntsoEDataService endpoint configuration."""

    def test_endpoint_configs_structure(
        self, entsoe_data_service: EntsoEDataService
    ) -> None:
        """Test that all endpoint configurations are properly structured."""
        configs = entsoe_data_service.ENDPOINT_CONFIGS

        # Verify all expected endpoints are present
        expected_endpoints = {
            EndpointNames.ACTUAL_LOAD,
            EndpointNames.DAY_AHEAD_FORECAST,
            EndpointNames.WEEK_AHEAD_FORECAST,
            EndpointNames.MONTH_AHEAD_FORECAST,
            EndpointNames.YEAR_AHEAD_FORECAST,
            EndpointNames.FORECAST_MARGIN,
        }
        assert set(configs.keys()) == expected_endpoints

        # Verify each configuration has the required attributes
        for config in configs.values():
            assert isinstance(config, EndpointConfig)
            assert isinstance(config.data_type, EnergyDataType)
            assert isinstance(config.expected_interval, timedelta)
            assert isinstance(config.max_chunk_days, int)
            assert isinstance(config.rate_limit_delay, float)
            assert isinstance(config.is_forward_looking, bool)
            assert isinstance(config.forecast_horizon, timedelta)

    def test_actual_load_is_backward_looking(
        self, entsoe_data_service: EntsoEDataService
    ) -> None:
        """Test that ACTUAL_LOAD endpoint is configured as backward-looking."""
        config = entsoe_data_service.ENDPOINT_CONFIGS[EndpointNames.ACTUAL_LOAD]
        assert config.is_forward_looking is False
        assert config.data_type == EnergyDataType.ACTUAL

    def test_forecast_endpoints_are_forward_looking(
        self, entsoe_data_service: EntsoEDataService
    ) -> None:
        """Test that all forecast endpoints are configured as forward-looking."""
        forecast_endpoints = [
            EndpointNames.DAY_AHEAD_FORECAST,
            EndpointNames.WEEK_AHEAD_FORECAST,
            EndpointNames.MONTH_AHEAD_FORECAST,
            EndpointNames.YEAR_AHEAD_FORECAST,
            EndpointNames.FORECAST_MARGIN,
        ]

        for endpoint_name in forecast_endpoints:
            config = entsoe_data_service.ENDPOINT_CONFIGS[endpoint_name]
            assert config.is_forward_looking is True, (
                f"{endpoint_name} should be forward-looking"
            )
            assert config.forecast_horizon > timedelta(0), (
                f"{endpoint_name} should have positive forecast horizon"
            )

    def test_forecast_horizons_are_reasonable(
        self, entsoe_data_service: EntsoEDataService
    ) -> None:
        """Test that forecast horizons are reasonable for each endpoint type."""
        configs = entsoe_data_service.ENDPOINT_CONFIGS

        # Day-ahead should be around 1-3 days
        day_ahead_horizon = configs[EndpointNames.DAY_AHEAD_FORECAST].forecast_horizon
        assert timedelta(hours=12) <= day_ahead_horizon <= timedelta(days=7)

        # Week-ahead should be around 1-4 weeks
        week_ahead_horizon = configs[EndpointNames.WEEK_AHEAD_FORECAST].forecast_horizon
        assert timedelta(days=7) <= week_ahead_horizon <= timedelta(days=35)

        # Month-ahead should be around 1-3 months
        month_ahead_horizon = configs[
            EndpointNames.MONTH_AHEAD_FORECAST
        ].forecast_horizon
        assert timedelta(days=28) <= month_ahead_horizon <= timedelta(days=100)

        # Year-ahead should be around 1-3 years
        year_ahead_horizon = configs[EndpointNames.YEAR_AHEAD_FORECAST].forecast_horizon
        assert timedelta(days=365) <= year_ahead_horizon <= timedelta(days=1100)


class TestDetectGapForEndpointNewBehavior:
    """Test cases for the new gap detection behavior with forward/backward looking logic."""

    @pytest.mark.asyncio
    async def test_detect_gap_backward_looking_no_data(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """Test gap detection for backward-looking endpoint with no existing data."""
        # Setup
        area = AreaCode.DE_LU
        config = EndpointConfig(
            data_type=EnergyDataType.ACTUAL,
            expected_interval=timedelta(minutes=5),
            max_chunk_days=3,
            rate_limit_delay=1.0,
            is_forward_looking=False,
        )
        mock_repository.get_latest_for_area_and_type.return_value = None

        # Execute
        gap_start, gap_end = await entsoe_data_service._detect_gap_for_endpoint(
            area, config
        )

        # Verify
        mock_repository.get_latest_for_area_and_type.assert_called_once_with(
            area.area_code, config.data_type
        )

        # Should look 7 days back for backward-looking endpoint with no data
        expected_duration = gap_end - gap_start
        assert expected_duration == timedelta(days=7)
        assert gap_end <= datetime.now(UTC)  # End should be at or before current time

    @pytest.mark.asyncio
    async def test_detect_gap_backward_looking_with_data(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """Test gap detection for backward-looking endpoint with existing data."""
        # Setup
        area = AreaCode.DE_LU
        config = EndpointConfig(
            data_type=EnergyDataType.ACTUAL,
            expected_interval=timedelta(minutes=5),
            max_chunk_days=3,
            rate_limit_delay=1.0,
            is_forward_looking=False,
        )

        latest_timestamp = datetime.now(UTC) - timedelta(hours=2)
        mock_data_point = MagicMock()
        mock_data_point.timestamp = latest_timestamp
        mock_repository.get_latest_for_area_and_type.return_value = mock_data_point

        # Execute
        gap_start, gap_end = await entsoe_data_service._detect_gap_for_endpoint(
            area, config
        )

        # Verify
        expected_gap_start = latest_timestamp + config.expected_interval
        assert gap_start == expected_gap_start
        assert gap_end <= datetime.now(UTC)  # End should be at or before current time

    @pytest.mark.asyncio
    async def test_detect_gap_forward_looking_no_data(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """Test gap detection for forward-looking endpoint with no existing data."""
        # Setup
        area = AreaCode.DE_LU
        forecast_horizon = timedelta(days=2)
        config = EndpointConfig(
            data_type=EnergyDataType.DAY_AHEAD,
            expected_interval=timedelta(minutes=15),
            max_chunk_days=7,
            rate_limit_delay=1.0,
            is_forward_looking=True,
            forecast_horizon=forecast_horizon,
        )
        mock_repository.get_latest_for_area_and_type.return_value = None

        # Execute
        gap_start, gap_end = await entsoe_data_service._detect_gap_for_endpoint(
            area, config
        )

        # Verify
        current_time = datetime.now(UTC)
        assert gap_start >= current_time - timedelta(
            minutes=1
        )  # Allow for small time differences
        assert gap_end == gap_start + forecast_horizon

    @pytest.mark.asyncio
    async def test_detect_gap_forward_looking_with_data(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """Test gap detection for forward-looking endpoint with existing data."""
        # Setup
        area = AreaCode.DE_LU
        forecast_horizon = timedelta(days=2)
        config = EndpointConfig(
            data_type=EnergyDataType.DAY_AHEAD,
            expected_interval=timedelta(minutes=15),
            max_chunk_days=7,
            rate_limit_delay=1.0,
            is_forward_looking=True,
            forecast_horizon=forecast_horizon,
        )

        latest_timestamp = datetime.now(UTC) - timedelta(hours=1)
        mock_data_point = MagicMock()
        mock_data_point.timestamp = latest_timestamp
        mock_repository.get_latest_for_area_and_type.return_value = mock_data_point

        # Execute
        gap_start, gap_end = await entsoe_data_service._detect_gap_for_endpoint(
            area, config
        )

        # Verify
        expected_gap_start = latest_timestamp + config.expected_interval
        current_time = datetime.now(UTC)
        expected_gap_end = current_time + forecast_horizon

        assert gap_start == expected_gap_start
        # Allow for small time differences in the end time
        assert abs((gap_end - expected_gap_end).total_seconds()) < 60

    @pytest.mark.asyncio
    async def test_detect_gap_different_forecast_horizons(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """Test that different forecast horizons are respected."""
        area = AreaCode.DE_LU
        mock_repository.get_latest_for_area_and_type.return_value = None

        test_cases = [
            (timedelta(days=1), "day_ahead"),
            (timedelta(weeks=1), "week_ahead"),
            (timedelta(days=30), "month_ahead"),
            (timedelta(days=365), "year_ahead"),
        ]

        for forecast_horizon, description in test_cases:
            config = EndpointConfig(
                data_type=EnergyDataType.DAY_AHEAD,
                expected_interval=timedelta(minutes=15),
                max_chunk_days=7,
                rate_limit_delay=1.0,
                is_forward_looking=True,
                forecast_horizon=forecast_horizon,
            )

            gap_start, gap_end = await entsoe_data_service._detect_gap_for_endpoint(
                area, config
            )

            actual_horizon = gap_end - gap_start
            assert actual_horizon == forecast_horizon, (
                f"Failed for {description}: expected {forecast_horizon}, got {actual_horizon}"
            )


@pytest.mark.asyncio
class TestEntsoEDataService:
    """Test suite for the EntsoEDataService."""

    async def test_collect_gaps_for_area_success(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """
        Test collect_gaps_for_area successfully collects for all endpoints.
        """
        mock_repository.get_latest_for_area_and_type.return_value = (
            None  # No existing data, forcing a gap
        )

        # We patch collect_with_chunking because its logic is tested separately
        with patch.object(
            entsoe_data_service, "collect_with_chunking", new_callable=AsyncMock
        ) as mock_collect_chunking:
            # Simulate a successful collection result
            result = CollectionResult(
                area=AreaCode.GERMANY,
                data_type=EnergyDataType.ACTUAL,  # Placeholder, doesn't affect this test
                stored_count=10,
                success=True,
            )
            result.set_time_range(datetime.now(UTC), datetime.now(UTC))
            mock_collect_chunking.return_value = result

            results = await entsoe_data_service.collect_gaps_for_area(AreaCode.GERMANY)

            assert len(results) == len(EndpointNames)
            assert all(result.success for result in results.values())
            assert all(res.stored_count == 10 for res in results.values())
            assert mock_collect_chunking.call_count == len(EndpointNames)

    async def test_collect_gaps_for_area_with_collector_exception(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """
        Test that collect_gaps_for_area handles CollectorError exceptions in one endpoint and continues.
        """
        mock_repository.get_latest_for_area_and_type.return_value = None

        with patch.object(
            entsoe_data_service, "collect_gaps_for_endpoint", new_callable=AsyncMock
        ) as mock_collect_endpoint:
            # Make one endpoint fail and others succeed
            def side_effect(
                area: AreaCode, endpoint_name: EndpointNames
            ) -> CollectionResult:
                if endpoint_name == EndpointNames.ACTUAL_LOAD:
                    error_msg = "Test Exception"
                    raise CollectorError(error_msg)
                result = CollectionResult(
                    area=area,
                    data_type=EnergyDataType.DAY_AHEAD,
                    stored_count=10,
                    success=True,
                )
                result.set_time_range(datetime.now(UTC), datetime.now(UTC))
                return result

            mock_collect_endpoint.side_effect = side_effect

            results = await entsoe_data_service.collect_gaps_for_area(AreaCode.GERMANY)

            assert len(results) == len(EndpointNames)
            # Check that the failed endpoint has a failure result
            assert results[EndpointNames.ACTUAL_LOAD.value].success is False
            assert (
                results[EndpointNames.ACTUAL_LOAD.value].error_message
                == "Test Exception"
            )
            assert results[EndpointNames.ACTUAL_LOAD.value].stored_count == 0
            # Check that other endpoints have success results
            assert results[EndpointNames.DAY_AHEAD_FORECAST.value].success is True
            assert results[EndpointNames.DAY_AHEAD_FORECAST.value].stored_count == 10

    async def test_collect_gaps_for_area_with_entsoe_client_exception(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """
        Test that collect_gaps_for_area handles EntsoEClientException and maps it to CollectorError.
        """
        mock_repository.get_latest_for_area_and_type.return_value = None

        with patch.object(
            entsoe_data_service, "collect_gaps_for_endpoint", new_callable=AsyncMock
        ) as mock_collect_endpoint:
            # Make one endpoint fail with EntsoEClientException and others succeed
            def side_effect(
                area: AreaCode, endpoint_name: EndpointNames
            ) -> CollectionResult:
                if endpoint_name == EndpointNames.ACTUAL_LOAD:
                    # Create an EntsoEClientError with HttpClientError cause
                    http_error = HttpClientError(
                        "HTTP 429 Too Many Requests",
                        status_code=429,
                        responnse_body="Rate limit exceeded",
                    )
                    exc = EntsoEClientError(
                        "HTTP 429 Too Many Requests", cause=http_error
                    )
                    raise exc
                result = CollectionResult(
                    area=area,
                    data_type=EnergyDataType.DAY_AHEAD,
                    stored_count=10,
                    success=True,
                )
                result.set_time_range(datetime.now(UTC), datetime.now(UTC))
                return result

            mock_collect_endpoint.side_effect = side_effect

            results = await entsoe_data_service.collect_gaps_for_area(AreaCode.GERMANY)

            assert len(results) == len(EndpointNames)
            # Check that the failed endpoint has a failure result with mapped error
            assert results[EndpointNames.ACTUAL_LOAD.value].success is False
            # The error message should be from the mapped CollectorError, not the original
            error_message = results[EndpointNames.ACTUAL_LOAD.value].error_message
            assert error_message is not None
            assert "Rate limit exceeded" in error_message
            assert results[EndpointNames.ACTUAL_LOAD.value].stored_count == 0
            # Check that other endpoints have success results
            assert results[EndpointNames.DAY_AHEAD_FORECAST.value].success is True
            assert results[EndpointNames.DAY_AHEAD_FORECAST.value].stored_count == 10

    async def test_collect_gaps_for_endpoint_no_gap(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """
        Test collect_gaps_for_endpoint when no data gap is detected.
        """
        # Simulate that the latest data point is very recent
        latest_point = EnergyDataPoint(
            timestamp=datetime.now(UTC) - timedelta(minutes=1)
        )
        mock_repository.get_latest_for_area_and_type.return_value = latest_point

        result = await entsoe_data_service.collect_gaps_for_endpoint(
            AreaCode.GERMANY, EndpointNames.ACTUAL_LOAD
        )

        assert result.stored_count == 0
        assert result.success is True
        mock_repository.get_latest_for_area_and_type.assert_called_once_with(
            "DE", EnergyDataType.ACTUAL
        )

    async def test_collect_gaps_for_endpoint_with_gap(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """
        Test collect_gaps_for_endpoint when a data gap is detected.
        """
        # Simulate that the latest data point is old
        latest_point = EnergyDataPoint(timestamp=datetime.now(UTC) - timedelta(days=1))
        mock_repository.get_latest_for_area_and_type.return_value = latest_point

        with patch.object(
            entsoe_data_service, "collect_with_chunking", new_callable=AsyncMock
        ) as mock_collect_chunking:
            mock_collect_chunking.return_value.stored_count = 50
            result = await entsoe_data_service.collect_gaps_for_endpoint(
                AreaCode.GERMANY, EndpointNames.ACTUAL_LOAD
            )

            assert result.stored_count == 50
            mock_collect_chunking.assert_called_once()

    async def test_collect_all_gaps(
        self, entsoe_data_service: EntsoEDataService
    ) -> None:
        """
        Test the main entry point for collecting all gaps.
        """
        with patch.object(
            entsoe_data_service, "collect_gaps_for_area", new_callable=AsyncMock
        ) as mock_collect_area:
            mock_result = CollectionResult(
                area=AreaCode.DE_LU,
                data_type=EnergyDataType.ACTUAL,
                stored_count=10,
                success=True,
            )
            mock_collect_area.return_value = {"actual_load": mock_result}
            results = await entsoe_data_service.collect_all_gaps()

            # Default areas are DE_LU, DE_AT_LU (keys use hyphens from area_code property)
            assert mock_collect_area.call_count == 2
            assert "actual_load" in results["DE-LU"]
            assert "actual_load" in results["DE-AT-LU"]

    async def test_collect_with_chunking_logic(
        self,
        entsoe_data_service: EntsoEDataService,
        mock_collector: AsyncMock,
        mock_processor: AsyncMock,
        mock_repository: AsyncMock,
    ) -> None:
        """
        Test the chunking logic in collect_with_chunking.
        """
        start_time = datetime(2024, 1, 1, tzinfo=UTC)
        # A 10-day period with a 3-day chunk size should result in 4 chunks
        end_time = start_time + timedelta(days=10)
        endpoint_name = EndpointNames.ACTUAL_LOAD

        # Create mock document with timeSeries attribute for logging
        mock_document = MagicMock(spec=GlMarketDocument)
        mock_time_series = MagicMock()
        mock_time_series.period = MagicMock()
        mock_time_series.period.points = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]  # Mock data points
        mock_document.timeSeries = [mock_time_series]
        mock_collector.get_actual_total_load.return_value = mock_document
        mock_processor.process.return_value = [MagicMock(spec=EnergyDataPoint)] * 5
        mock_repository.upsert_batch.return_value = [
            MagicMock(spec=EnergyDataPoint)
        ] * 5

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await entsoe_data_service.collect_with_chunking(
                AreaCode.GERMANY, endpoint_name, start_time, end_time
            )

            # 10 days / 3 days/chunk = 3.33 -> 4 chunks
            assert mock_collector.get_actual_total_load.call_count == 4
            assert mock_processor.process.call_count == 4
            assert mock_repository.upsert_batch.call_count == 4
            assert result.stored_count == 20  # 4 chunks * 5 stored per chunk
            # Rate limiting delay should be called between chunks
            assert mock_sleep.call_count == 4

    async def test_collect_with_chunking_no_data(
        self,
        entsoe_data_service: EntsoEDataService,
        mock_collector: AsyncMock,
        mock_processor: AsyncMock,
        mock_repository: AsyncMock,
    ) -> None:
        """
        Test collect_with_chunking when the collector returns no data.
        """
        start_time = datetime(2024, 1, 1, tzinfo=UTC)
        end_time = start_time + timedelta(days=1)
        endpoint_name = EndpointNames.ACTUAL_LOAD

        # Simulate the collector returning None
        mock_collector.get_actual_total_load.return_value = None

        result = await entsoe_data_service.collect_with_chunking(
            AreaCode.GERMANY, endpoint_name, start_time, end_time
        )

        assert result.stored_count == 0
        # NEW: Test the no-data tracking fields
        assert result.no_data_available is True
        assert result.no_data_reason == "1/1 chunks returned no data"
        # Processor and repository should not be called if there's no raw document
        assert mock_processor.process.call_count == 0
        assert mock_repository.upsert_batch.call_count == 0

    async def test_collect_with_chunking_mixed_data_scenarios(
        self,
        entsoe_data_service: EntsoEDataService,
        mock_collector: AsyncMock,
        mock_processor: AsyncMock,
        mock_repository: AsyncMock,
    ) -> None:
        """
        Test collect_with_chunking when some chunks return data and others return None.
        """
        start_time = datetime(2024, 1, 1, tzinfo=UTC)
        end_time = start_time + timedelta(days=6)  # 6 days = 2 chunks (3 days each)
        endpoint_name = EndpointNames.ACTUAL_LOAD

        # Mock GL market document for successful chunks
        mock_gl_doc = Mock()
        mock_gl_doc.timeSeries = [Mock()]
        mock_gl_doc.timeSeries[0].period = Mock()
        mock_gl_doc.timeSeries[0].period.points = [Mock(), Mock()]

        # First chunk returns data, second chunk returns None
        mock_collector.get_actual_total_load.side_effect = [mock_gl_doc, None]

        # Mock processor to return some data points
        mock_data_points = [Mock(), Mock()]
        mock_processor.process.return_value = mock_data_points

        # Mock repository to return stored models
        mock_repository.upsert_batch.return_value = mock_data_points

        result = await entsoe_data_service.collect_with_chunking(
            AreaCode.GERMANY, endpoint_name, start_time, end_time
        )

        # Verify mixed results are tracked correctly
        assert result.stored_count == 2  # Only from the first chunk
        assert result.no_data_available is True  # Because some chunks had no data
        assert result.no_data_reason == "1/2 chunks returned no data"

        # Verify processor and repository were called only once (for the chunk with data)
        assert mock_processor.process.call_count == 1
        assert mock_repository.upsert_batch.call_count == 1

    async def test_collect_with_chunking_entsoe_client_exception(
        self,
        entsoe_data_service: EntsoEDataService,
        mock_collector: AsyncMock,
        mock_processor: AsyncMock,
        mock_repository: AsyncMock,
    ) -> None:
        """
        Test collect_with_chunking continues with other chunks when EntsoEClientException occurs.
        """
        start_time = datetime(2024, 1, 1, tzinfo=UTC)
        end_time = start_time + timedelta(days=6)  # 2 chunks with 3-day limit
        endpoint_name = EndpointNames.ACTUAL_LOAD

        # First chunk fails with EntsoEClientException, second succeeds
        def collector_side_effect(**kwargs: Any) -> GlMarketDocument:
            if kwargs["period_start"] == start_time:
                # First chunk fails
                http_error = HttpClientError(
                    "HTTP 500 Internal Server Error",
                    status_code=500,
                    responnse_body="Server error",
                )
                exc = EntsoEClientError(
                    "HTTP 500 Internal Server Error", cause=http_error
                )
                raise exc
            # Second chunk succeeds - create mock with timeSeries for logging
            mock_document = MagicMock(spec=GlMarketDocument)
            mock_time_series = MagicMock()
            mock_time_series.period = MagicMock()
            mock_time_series.period.points = [
                MagicMock(),
                MagicMock(),
                MagicMock(),
            ]  # Mock data points
            mock_document.timeSeries = [mock_time_series]
            return mock_document

        mock_collector.get_actual_total_load.side_effect = collector_side_effect
        mock_processor.process.return_value = [MagicMock(spec=EnergyDataPoint)] * 3
        mock_repository.upsert_batch.return_value = [
            MagicMock(spec=EnergyDataPoint)
        ] * 3

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await entsoe_data_service.collect_with_chunking(
                AreaCode.GERMANY, endpoint_name, start_time, end_time
            )

            # Should have tried both chunks
            assert mock_collector.get_actual_total_load.call_count == 2
            # Only second chunk should have been processed (first failed)
            assert mock_processor.process.call_count == 1
            assert mock_repository.upsert_batch.call_count == 1
            assert result.stored_count == 3  # Only second chunk stored

    async def test_should_collect_now_true_due_to_age(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """
        Test should_collect_now returns True when collection is due because data is old.
        """
        # Last data point is older than the expected interval (5 mins for actual load)
        latest_point = EnergyDataPoint(timestamp=datetime.now(UTC) - timedelta(hours=1))
        mock_repository.get_latest_for_area_and_type.return_value = latest_point

        result = await entsoe_data_service.should_collect_now(
            AreaCode.GERMANY, EndpointNames.ACTUAL_LOAD
        )
        assert result is True

    async def test_should_collect_now_true_no_data(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """
        Test should_collect_now returns True when no data exists yet.
        """
        mock_repository.get_latest_for_area_and_type.return_value = None
        result = await entsoe_data_service.should_collect_now(
            AreaCode.GERMANY, EndpointNames.ACTUAL_LOAD
        )
        assert result is True

    async def test_should_collect_now_false(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """
        Test should_collect_now returns False when collection is not due.
        """
        # Last data point is recent
        latest_point = EnergyDataPoint(
            timestamp=datetime.now(UTC) - timedelta(minutes=1)
        )
        mock_repository.get_latest_for_area_and_type.return_value = latest_point

        result = await entsoe_data_service.should_collect_now(
            AreaCode.GERMANY, EndpointNames.ACTUAL_LOAD
        )
        assert result is False

    async def test_detect_gap_for_endpoint_with_data(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """
        Test _detect_gap_for_endpoint when there is existing data.
        """
        config = entsoe_data_service.ENDPOINT_CONFIGS[EndpointNames.ACTUAL_LOAD]
        latest_timestamp = datetime.now(UTC) - timedelta(days=1)
        latest_point = EnergyDataPoint(timestamp=latest_timestamp)
        mock_repository.get_latest_for_area_and_type.return_value = latest_point

        gap_start, gap_end = await entsoe_data_service._detect_gap_for_endpoint(
            AreaCode.GERMANY, config
        )

        assert gap_start == latest_timestamp + config.expected_interval
        # The end of the gap should be roughly 'now'
        assert (datetime.now(UTC) - gap_end).total_seconds() < 5

    async def test_detect_gap_for_endpoint_no_data(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """
        Test _detect_gap_for_endpoint when there is no existing data.
        """
        config = entsoe_data_service.ENDPOINT_CONFIGS[EndpointNames.ACTUAL_LOAD]
        mock_repository.get_latest_for_area_and_type.return_value = None

        gap_start, gap_end = await entsoe_data_service._detect_gap_for_endpoint(
            AreaCode.GERMANY, config
        )

        # Should default to the last 7 days
        assert (datetime.now(UTC) - gap_start).days == 7
        assert (datetime.now(UTC) - gap_end).total_seconds() < 5

    @pytest.mark.parametrize(
        ("endpoint_name", "method_name"),
        [
            (EndpointNames.ACTUAL_LOAD, "get_actual_total_load"),
            (EndpointNames.DAY_AHEAD_FORECAST, "get_day_ahead_load_forecast"),
            (EndpointNames.WEEK_AHEAD_FORECAST, "get_week_ahead_load_forecast"),
            (EndpointNames.MONTH_AHEAD_FORECAST, "get_month_ahead_load_forecast"),
            (EndpointNames.YEAR_AHEAD_FORECAST, "get_year_ahead_load_forecast"),
            (EndpointNames.FORECAST_MARGIN, "get_year_ahead_forecast_margin"),
        ],
    )
    async def test_collect_raw_data_maps_to_correct_method(
        self,
        entsoe_data_service: EntsoEDataService,
        mock_collector: AsyncMock,
        endpoint_name: EndpointNames,
        method_name: str,
    ) -> None:
        """
        Test that _collect_raw_data calls the correct collector method for each endpoint.
        """
        start_time = datetime(2024, 1, 1, tzinfo=UTC)
        end_time = datetime(2024, 1, 2, tzinfo=UTC)
        area = AreaCode.GERMANY

        await entsoe_data_service._collect_raw_data(
            area, endpoint_name, start_time, end_time
        )

        # Check that the correct method on the collector was called
        collector_method = getattr(mock_collector, method_name)
        collector_method.assert_called_once_with(
            bidding_zone=area,
            period_start=start_time,
            period_end=end_time,
        )

    @pytest.mark.parametrize(
        ("start_time", "end_time", "max_chunk_days", "expected_chunks"),
        [
            # Simple case, exact multiple
            (
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 7, tzinfo=UTC),
                3,
                [
                    (
                        datetime(2024, 1, 1, tzinfo=UTC),
                        datetime(2024, 1, 4, tzinfo=UTC),
                    ),
                    (
                        datetime(2024, 1, 4, tzinfo=UTC),
                        datetime(2024, 1, 7, tzinfo=UTC),
                    ),
                ],
            ),
            # Not an exact multiple, last chunk is smaller
            (
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 8, tzinfo=UTC),
                3,
                [
                    (
                        datetime(2024, 1, 1, tzinfo=UTC),
                        datetime(2024, 1, 4, tzinfo=UTC),
                    ),
                    (
                        datetime(2024, 1, 4, tzinfo=UTC),
                        datetime(2024, 1, 7, tzinfo=UTC),
                    ),
                    (
                        datetime(2024, 1, 7, tzinfo=UTC),
                        datetime(2024, 1, 8, tzinfo=UTC),
                    ),
                ],
            ),
            # Range smaller than chunk size
            (
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 2, tzinfo=UTC),
                5,
                [
                    (
                        datetime(2024, 1, 1, tzinfo=UTC),
                        datetime(2024, 1, 2, tzinfo=UTC),
                    ),
                ],
            ),
            # Range equal to chunk size
            (
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 6, tzinfo=UTC),
                5,
                [
                    (
                        datetime(2024, 1, 1, tzinfo=UTC),
                        datetime(2024, 1, 6, tzinfo=UTC),
                    ),
                ],
            ),
        ],
    )
    def test_create_time_chunks(
        self,
        entsoe_data_service: EntsoEDataService,
        start_time: datetime,
        end_time: datetime,
        max_chunk_days: int,
        expected_chunks: list[tuple[datetime, datetime]],
    ) -> None:
        """
        Test the _create_time_chunks method with various scenarios.
        """
        chunks = entsoe_data_service._create_time_chunks(
            start_time, end_time, max_chunk_days
        )
        assert chunks == expected_chunks
