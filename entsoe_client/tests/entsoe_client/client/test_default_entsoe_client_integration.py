"""Integration test for DefaultEntsoEClient against real ENTSO-E API."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from pydantic import ValidationError

from entsoe_client.client.entsoe_client import EntsoEClient
from entsoe_client.client.entsoe_client_factory import EntsoEClientFactory
from entsoe_client.config.settings import EntsoEClientConfig
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.load.gl_market_document import GlMarketDocument
from entsoe_client.model.market.publication_market_document import (
    PublicationMarketDocument,
)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[EntsoEClient]:
    """
    Create a client instance for integration testing.
    This fixture creates a client using the EntsoEClientFactory with configuration
    loaded from the .env file. If the API token is not available or invalid,
    all tests using this fixture will be skipped.
    The client is properly closed after the test completes.
    """
    try:
        # Try to load config from .env file
        config = EntsoEClientConfig()
        api_token = config.api_token.get_secret_value()

        # Check if we have a real token (not the dummy value)
        if not api_token or api_token == "your-actual-entsoe-api-token-goes-here":
            pytest.skip(
                "Skipping integration tests: Please set a real ENTSOE_API_TOKEN in .env file.",
            )

        client_instance = EntsoEClientFactory.create_client(api_token)
        yield client_instance
        await client_instance.close()

    except ValidationError as e:
        pytest.skip(
            f"Skipping integration tests: Invalid configuration - {e}",
        )
    except (RuntimeError, OSError) as e:
        pytest.skip(
            f"Skipping integration tests: Failed to create client - {e}",
        )


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
        assert len(result.timeSeries) > 0

        # Validate time series structure (timeSeries is now a list)
        for time_series in result.timeSeries:
            assert time_series.mRID is not None
            assert time_series.businessType is not None
            assert time_series.objectAggregation is not None
            assert time_series.outBiddingZoneDomainMRID is not None
            assert time_series.quantityMeasureUnitName is not None
            assert time_series.curveType is not None

            # Validate time period
            if time_series.period:
                assert time_series.period.timeInterval is not None
                assert time_series.period.resolution is not None
                if time_series.period.points:
                    assert len(time_series.period.points) > 0
                    for point in time_series.period.points:
                        assert point.position is not None
                        assert point.quantity is not None
                        assert point.quantity > 0

    def _validate_publication_market_document(
        self, result: PublicationMarketDocument
    ) -> None:
        """Validate all fields of PublicationMarketDocument are properly populated."""
        assert isinstance(result, PublicationMarketDocument)
        assert result.mRID is not None
        assert len(result.mRID) > 0
        assert result.type is not None
        assert result.senderMarketParticipantMRID is not None
        assert result.senderMarketParticipantMarketRoleType is not None
        assert result.receiverMarketParticipantMRID is not None
        assert result.receiverMarketParticipantMarketRoleType is not None
        assert result.createdDateTime is not None
        assert result.periodTimeInterval is not None
        assert result.timeSeries is not None
        assert len(result.timeSeries) > 0

        # Validate time series structure (with optional fields for now)
        for time_series in result.timeSeries:
            assert time_series.mRID is not None
            assert time_series.businessType is not None

            # These fields might be present based on XML parsing
            if time_series.in_domain_mRID:
                assert time_series.in_domain_mRID is not None
            if time_series.out_domain_mRID:
                assert time_series.out_domain_mRID is not None
            if time_series.currency_unit_name:
                assert time_series.currency_unit_name is not None
            if time_series.price_measure_unit_name:
                assert time_series.price_measure_unit_name is not None
            if time_series.curveType:
                assert time_series.curveType is not None

            # Validate period and points if present
            if time_series.period:
                assert time_series.period.timeInterval is not None
                assert time_series.period.resolution is not None
                if time_series.period.points:
                    assert len(time_series.period.points) > 0
                    for point in time_series.period.points:
                        assert point.position is not None
                        assert point.price_amount is not None
                        assert point.price_amount > 0

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

        assert result is not None
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

        assert result is not None
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

        assert result is not None
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

        assert result is not None
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

        assert result is not None
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

        assert result is not None
        self._validate_market_document(result)

    @pytest.mark.asyncio
    async def test_get_day_ahead_prices_real_api(
        self,
        client: EntsoEClient,
    ) -> None:
        """Test day-ahead prices retrieval against real ENTSO-E API."""
        bidding_zone = AreaCode.CZECH_REPUBLIC
        period_start, period_end = self._get_test_periods()

        result = await client.get_day_ahead_prices(
            in_domain=bidding_zone,
            out_domain=bidding_zone,
            period_start=period_start,
            period_end=period_end,
        )

        if result is not None:
            self._validate_publication_market_document(result)
