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
from entsoe_client.model.market.market_time_series import MarketTimeSeries
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
        yesterday = today - timedelta(days=2)
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
        self._validate_document_metadata(result)
        self._validate_time_series(result.timeSeries)

    def _validate_document_metadata(self, result: PublicationMarketDocument) -> None:
        """Validate basic document metadata fields."""
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

    def _validate_time_series(self, time_series_list: list[MarketTimeSeries]) -> None:
        """Validate time series structure with optional fields."""
        for time_series in time_series_list:
            assert time_series.mRID is not None
            assert time_series.businessType is not None
            self._validate_optional_time_series_fields(time_series)
            self._validate_period_and_points(time_series)

    def _validate_optional_time_series_fields(
        self, time_series: MarketTimeSeries
    ) -> None:
        """Validate optional time series fields when present."""
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

    def _validate_period_and_points(self, time_series: MarketTimeSeries) -> None:
        """Validate period and points data when present."""
        if time_series.period:
            assert time_series.period.timeInterval is not None
            assert time_series.period.resolution is not None
            if time_series.period.points:
                assert len(time_series.period.points) > 0
                for point in time_series.period.points:
                    assert point.position is not None
                    has_price = point.price_amount is not None
                    has_quantity = point.quantity is not None
                    assert has_price or has_quantity
                    if has_price:
                        assert isinstance(point.price_amount, (int | float))
                    if has_quantity:
                        assert isinstance(point.quantity, (int | float))

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

    @pytest.mark.asyncio
    async def test_get_physical_flows_real_api(
        self,
        client: EntsoEClient,
    ) -> None:
        """Test physical flows retrieval against real ENTSO-E API."""
        # Use different domains for directional flow (Czech Republic -> Slovakia)
        in_domain = AreaCode.CZECH_REPUBLIC
        out_domain = AreaCode.SLOVAKIA
        period_start, period_end = self._get_test_periods()

        result = await client.get_physical_flows(
            in_domain=in_domain,
            out_domain=out_domain,
            period_start=period_start,
            period_end=period_end,
        )

        if result is not None:
            # Validate using the same method as other publication market documents
            self._validate_publication_market_document(result)

            # Additional validation specific to physical flows
            assert len(result.timeSeries) >= 1
            time_series = result.timeSeries[0]

            # Verify physical flows business type
            assert time_series.businessType.code == "A66"

            # Verify directional flow information
            assert time_series.in_domain_mRID is not None
            assert time_series.out_domain_mRID is not None

            # Verify quantity measure unit is present (typical: MAW)
            assert time_series.quantity_measure_unit_name is not None

            # Verify points contain quantity data (not price data)
            if time_series.period.points:
                for point in time_series.period.points:
                    assert point.quantity is not None  # Should have quantity data
                    assert point.price_amount is None  # Should NOT have price data
