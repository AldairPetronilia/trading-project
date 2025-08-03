import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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
def entsoe_data_service(
    mock_collector: AsyncMock, mock_processor: AsyncMock, mock_repository: AsyncMock
) -> EntsoEDataService:
    """Fixture for an EntsoEDataService instance with mocked dependencies."""
    return EntsoEDataService(mock_collector, mock_processor, mock_repository)


@pytest.mark.asyncio
class TestEntsoEDataService:
    """Test suite for the EntsoEDataService."""

    async def test_collect_gaps_for_area_success(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """
        Test collect_gaps_for_area successfully collects for all endpoints.
        """
        mock_repository.get_latest_for_area.return_value = (
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
        mock_repository.get_latest_for_area.return_value = None

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
        mock_repository.get_latest_for_area.return_value = None

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
                    http_error.headers = {"Retry-After": "60"}
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
        mock_repository.get_latest_for_area.return_value = latest_point

        result = await entsoe_data_service.collect_gaps_for_endpoint(
            AreaCode.GERMANY, EndpointNames.ACTUAL_LOAD
        )

        assert result.stored_count == 0
        assert result.success is True
        mock_repository.get_latest_for_area.assert_called_once_with(
            "DE", EnergyDataType.ACTUAL, BusinessType.CONSUMPTION.code
        )

    async def test_collect_gaps_for_endpoint_with_gap(
        self, entsoe_data_service: EntsoEDataService, mock_repository: AsyncMock
    ) -> None:
        """
        Test collect_gaps_for_endpoint when a data gap is detected.
        """
        # Simulate that the latest data point is old
        latest_point = EnergyDataPoint(timestamp=datetime.now(UTC) - timedelta(days=1))
        mock_repository.get_latest_for_area.return_value = latest_point

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

        mock_collector.get_actual_total_load.return_value = MagicMock(
            spec=GlMarketDocument
        )
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
        # Processor and repository should not be called if there's no raw document
        assert mock_processor.process.call_count == 0
        assert mock_repository.upsert_batch.call_count == 0

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
            # Second chunk succeeds
            return MagicMock(spec=GlMarketDocument)

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
        mock_repository.get_latest_for_area.return_value = latest_point

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
        mock_repository.get_latest_for_area.return_value = None
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
        mock_repository.get_latest_for_area.return_value = latest_point

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
        mock_repository.get_latest_for_area.return_value = latest_point

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
        mock_repository.get_latest_for_area.return_value = None

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
