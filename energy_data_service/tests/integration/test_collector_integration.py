"""Integration tests for EntsoeCollector against real ENTSO-E API."""

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from app.collectors.entsoe_collector import EntsoeCollector
from app.container import Container

from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.load.gl_market_document import GlMarketDocument


@pytest_asyncio.fixture
async def collector() -> AsyncGenerator[EntsoeCollector]:
    """Create EntsoeCollector for real API integration testing."""
    api_token = os.environ.get("ENTSOE_CLIENT__API_TOKEN")
    if not api_token:
        pytest.skip(
            "Skipping integration tests: ENTSOE_CLIENT__API_TOKEN environment variable not set."
        )

    container = Container()
    collector_instance = container.entsoe_collector()

    yield collector_instance

    await collector_instance._client.close()


def _get_test_periods() -> tuple[datetime, datetime]:
    """Get test period - yesterday for actual data."""
    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)
    period_start = datetime.combine(yesterday, datetime.min.time()).replace(
        tzinfo=UTC,
    )
    period_end = period_start + timedelta(days=1)
    return period_start, period_end


def _get_forecast_periods() -> tuple[datetime, datetime]:
    """Get forecast period - tomorrow for forecasts."""
    today = datetime.now(UTC).date()
    tomorrow = today + timedelta(days=1)
    period_start = datetime.combine(tomorrow, datetime.min.time()).replace(
        tzinfo=UTC,
    )
    period_end = period_start + timedelta(days=1)
    return period_start, period_end


def _validate_market_document(result: GlMarketDocument) -> None:
    """Validate GlMarketDocument structure."""
    assert isinstance(result, GlMarketDocument)
    assert result.mRID is not None
    assert len(result.mRID) > 0
    assert result.type is not None
    assert result.processType is not None
    assert result.senderMarketParticipantMRID is not None
    assert result.senderMarketParticipantMarketRoleType is not None
    assert result.receiverMarketParticipantMRID is not None
    assert result.receiverMarketParticipantMarketRoleType is not None
    assert result.createdDateTime is not None
    assert result.timePeriodTimeInterval is not None
    assert result.timeSeries is not None

    # Validate time series structure
    assert result.timeSeries[0].mRID is not None
    assert result.timeSeries[0].businessType is not None
    assert result.timeSeries[0].objectAggregation is not None
    assert result.timeSeries[0].outBiddingZoneDomainMRID is not None
    assert result.timeSeries[0].quantityMeasureUnitName is not None
    assert result.timeSeries[0].curveType is not None

    # Validate period and points
    if result.timeSeries[0].period:
        assert result.timeSeries[0].period.timeInterval is not None
        assert result.timeSeries[0].period.resolution is not None
        if result.timeSeries[0].period.points:
            assert len(result.timeSeries[0].period.points) > 0
            for point in result.timeSeries[0].period.points:
                assert point.position is not None
                assert point.quantity is not None
                assert point.quantity > 0


class TestEntsoeCollectorIntegration:
    """Integration tests for EntsoeCollector against real ENTSO-E API."""

    @pytest.mark.asyncio
    async def test_get_actual_total_load_integration(
        self,
        collector: EntsoeCollector,
    ) -> None:
        """Test actual total load retrieval integration."""
        bidding_zone = AreaCode.CZECH_REPUBLIC
        period_start, period_end = _get_test_periods()

        result = await collector.get_actual_total_load(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
        )

        _validate_market_document(result)
        assert result.processType.value[0] == "A16"

    @pytest.mark.asyncio
    async def test_get_day_ahead_load_forecast_integration(
        self,
        collector: EntsoeCollector,
    ) -> None:
        """Test day-ahead load forecast retrieval integration."""
        bidding_zone = AreaCode.CZECH_REPUBLIC
        period_start, period_end = _get_forecast_periods()

        result = await collector.get_day_ahead_load_forecast(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
        )

        _validate_market_document(result)
        assert result.processType.value[0] == "A01"

    @pytest.mark.asyncio
    async def test_get_week_ahead_load_forecast_integration(
        self,
        collector: EntsoeCollector,
    ) -> None:
        """Test week-ahead load forecast retrieval integration."""
        bidding_zone = AreaCode.CZECH_REPUBLIC
        period_start, period_end = _get_forecast_periods()

        result = await collector.get_week_ahead_load_forecast(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
        )

        _validate_market_document(result)
        assert result.processType.value[0] == "A31"

    @pytest.mark.asyncio
    async def test_get_month_ahead_load_forecast_integration(
        self,
        collector: EntsoeCollector,
    ) -> None:
        """Test month-ahead load forecast retrieval integration."""
        bidding_zone = AreaCode.CZECH_REPUBLIC
        period_start, period_end = _get_forecast_periods()

        result = await collector.get_month_ahead_load_forecast(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
        )

        _validate_market_document(result)
        assert result.processType.value[0] == "A32"

    @pytest.mark.asyncio
    async def test_get_year_ahead_load_forecast_integration(
        self,
        collector: EntsoeCollector,
    ) -> None:
        """Test year-ahead load forecast retrieval integration."""
        bidding_zone = AreaCode.CZECH_REPUBLIC
        period_start, period_end = _get_forecast_periods()

        result = await collector.get_year_ahead_load_forecast(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
        )

        _validate_market_document(result)
        assert result.processType.value[0] == "A33"

    @pytest.mark.asyncio
    async def test_get_year_ahead_forecast_margin_integration(
        self,
        collector: EntsoeCollector,
    ) -> None:
        """Test year-ahead forecast margin retrieval integration."""
        bidding_zone = AreaCode.CZECH_REPUBLIC
        period_start, period_end = _get_forecast_periods()

        result = await collector.get_year_ahead_forecast_margin(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
        )

        _validate_market_document(result)
        assert result.processType.value[0] == "A33"
        assert result.timeSeries[0].businessType.value[0] == "A91"

    @pytest.mark.asyncio
    async def test_collector_health_check_integration(
        self,
        collector: EntsoeCollector,
    ) -> None:
        """Test collector health check integration."""
        result = await collector.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_collector_with_offset_parameter_integration(
        self,
        collector: EntsoeCollector,
    ) -> None:
        """Test collector methods with offset parameter."""
        bidding_zone = AreaCode.CZECH_REPUBLIC
        period_start, period_end = _get_test_periods()

        result = await collector.get_actual_total_load(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
            offset=100,
        )

        _validate_market_document(result)
