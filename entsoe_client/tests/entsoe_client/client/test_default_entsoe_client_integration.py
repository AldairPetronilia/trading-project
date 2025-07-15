"""Integration test for DefaultEntsoEClient against real ENTSO-E API."""

import os
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio

from entsoe_client.client.entsoe_client import EntsoEClient
from entsoe_client.client.entsoe_client_factory import EntsoEClientFactory
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.load.gl_market_document import GlMarketDocument


@pytest_asyncio.fixture
async def client() -> EntsoEClient:
    """
    Create a client instance for integration testing.
    This fixture creates a client using the EntsoEClientFactory, which is the
    public entry point of the library. It requires the ENTSOE_API_TOKEN
    environment variable to be set. If the token is not available, all
    tests using this fixture will be skipped.
    The client is properly closed after the test completes.
    """
    api_token = os.environ.get("ENTSOE_API_TOKEN")
    if not api_token:
        pytest.skip(
            "Skipping integration tests: ENTSOE_API_TOKEN environment variable not set.",
        )

    client_instance = EntsoEClientFactory.create_client(api_token)
    yield client_instance
    await client_instance.close()


class TestDefaultEntsoEClientIntegration:
    """Integration tests for DefaultEntsoEClient against real ENTSO-E API."""

    def _get_test_periods(self) -> tuple[datetime, datetime]:
        """Get test period - yesterday for actual data, tomorrow for forecasts."""
        today = datetime.now(UTC).date()
        yesterday = today - timedelta(days=1)
        period_start = datetime.combine(yesterday, datetime.min.time()).replace(
            tzinfo=UTC,
        )
        period_end = period_start + timedelta(days=1)
        return period_start, period_end

    def _get_forecast_periods(self) -> tuple[datetime, datetime]:
        """Get forecast period - tomorrow for day-ahead forecasts."""
        today = datetime.now(UTC).date()
        tomorrow = today + timedelta(days=1)
        period_start = datetime.combine(tomorrow, datetime.min.time()).replace(
            tzinfo=UTC,
        )
        period_end = period_start + timedelta(days=1)
        return period_start, period_end

    def _validate_market_document(self, result: GlMarketDocument) -> None:
        """Validate all fields of GlMarketDocument are properly populated."""
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
        assert result.timeSeries.mRID is not None
        assert result.timeSeries.businessType is not None
        assert result.timeSeries.objectAggregation is not None
        assert result.timeSeries.outBiddingZoneDomainMRID is not None
        assert result.timeSeries.quantityMeasureUnitName is not None
        assert result.timeSeries.curveType is not None

        # Validate time period
        if result.timeSeries.period:
            assert result.timeSeries.period.timeInterval is not None
            assert result.timeSeries.period.resolution is not None
            if result.timeSeries.period.points:
                assert len(result.timeSeries.period.points) > 0
                for point in result.timeSeries.period.points:
                    assert point.position is not None
                    assert point.quantity is not None
                    assert point.quantity > 0

    @pytest.mark.asyncio
    async def test_get_actual_total_load_real_api(
        self,
        client: EntsoEClient,
    ) -> None:
        """Test actual total load retrieval against real ENTSO-E API."""
        bidding_zone = AreaCode.CZECH_REPUBLIC
        period_start, period_end = self._get_test_periods()

        result = await client.get_actual_total_load(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
        )

        self._validate_market_document(result)

    @pytest.mark.asyncio
    async def test_get_day_ahead_load_forecast_real_api(
        self,
        client: EntsoEClient,
    ) -> None:
        """Test day-ahead load forecast retrieval against real ENTSO-E API."""
        bidding_zone = AreaCode.CZECH_REPUBLIC
        period_start, period_end = self._get_forecast_periods()

        result = await client.get_day_ahead_load_forecast(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
        )

        self._validate_market_document(result)

    @pytest.mark.asyncio
    async def test_get_week_ahead_load_forecast_real_api(
        self,
        client: EntsoEClient,
    ) -> None:
        """Test week-ahead load forecast retrieval against real ENTSO-E API."""
        bidding_zone = AreaCode.CZECH_REPUBLIC
        period_start, period_end = self._get_forecast_periods()

        result = await client.get_week_ahead_load_forecast(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
        )

        self._validate_market_document(result)

    @pytest.mark.asyncio
    async def test_get_month_ahead_load_forecast_real_api(
        self,
        client: EntsoEClient,
    ) -> None:
        """Test month-ahead load forecast retrieval against real ENTSO-E API."""
        bidding_zone = AreaCode.CZECH_REPUBLIC
        period_start, period_end = self._get_forecast_periods()

        result = await client.get_month_ahead_load_forecast(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
        )

        self._validate_market_document(result)

    @pytest.mark.asyncio
    async def test_get_year_ahead_load_forecast_real_api(
        self,
        client: EntsoEClient,
    ) -> None:
        """Test year-ahead load forecast retrieval against real ENTSO-E API."""
        bidding_zone = AreaCode.CZECH_REPUBLIC
        period_start, period_end = self._get_forecast_periods()

        result = await client.get_year_ahead_load_forecast(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
        )

        self._validate_market_document(result)

    @pytest.mark.asyncio
    async def test_get_year_ahead_forecast_margin_real_api(
        self,
        client: EntsoEClient,
    ) -> None:
        """Test year-ahead forecast margin retrieval against real ENTSO-E API."""
        bidding_zone = AreaCode.CZECH_REPUBLIC
        period_start, period_end = self._get_forecast_periods()

        result = await client.get_year_ahead_forecast_margin(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
        )

        self._validate_market_document(result)
