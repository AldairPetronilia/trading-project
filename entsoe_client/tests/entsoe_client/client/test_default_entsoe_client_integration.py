"""Integration test for DefaultEntsoEClient against real ENTSO-E API."""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio

import entsoe_client
from entsoe_client.client.default_entsoe_client import DefaultEntsoEClient
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.load.gl_market_document import GlMarketDocument


class TestDefaultEntsoEClientIntegration:
    """Integration tests for DefaultEntsoEClient against real ENTSO-E API."""

    @pytest_asyncio.fixture
    async def client(self) -> DefaultEntsoEClient:
        """Create a client instance for testing."""
        try:
            config = entsoe_client.container.config()
            http_client = entsoe_client.container.http_client()
            return DefaultEntsoEClient(http_client, str(config.base_url))
        except Exception as e:
            pytest.skip(
                f"Could not create client from container (likely missing API token): {e}",
            )
            # This return is unreachable due to pytest.skip() but satisfies mypy
            raise

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
        client: DefaultEntsoEClient,
    ) -> None:
        """Test actual total load retrieval against real ENTSO-E API."""
        try:
            bidding_zone = AreaCode.CZECH_REPUBLIC
            period_start, period_end = self._get_test_periods()

            result = await client.get_actual_total_load(
                bidding_zone=bidding_zone,
                period_start=period_start,
                period_end=period_end,
            )

            self._validate_market_document(result)

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_day_ahead_load_forecast_real_api(
        self,
        client: DefaultEntsoEClient,
    ) -> None:
        """Test day-ahead load forecast retrieval against real ENTSO-E API."""
        try:
            bidding_zone = AreaCode.CZECH_REPUBLIC
            period_start, period_end = self._get_forecast_periods()

            result = await client.get_day_ahead_load_forecast(
                bidding_zone=bidding_zone,
                period_start=period_start,
                period_end=period_end,
            )

            self._validate_market_document(result)

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_week_ahead_load_forecast_real_api(
        self,
        client: DefaultEntsoEClient,
    ) -> None:
        """Test week-ahead load forecast retrieval against real ENTSO-E API."""
        try:
            bidding_zone = AreaCode.CZECH_REPUBLIC
            period_start, period_end = self._get_forecast_periods()

            result = await client.get_week_ahead_load_forecast(
                bidding_zone=bidding_zone,
                period_start=period_start,
                period_end=period_end,
            )

            self._validate_market_document(result)

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_month_ahead_load_forecast_real_api(
        self,
        client: DefaultEntsoEClient,
    ) -> None:
        """Test month-ahead load forecast retrieval against real ENTSO-E API."""
        try:
            bidding_zone = AreaCode.CZECH_REPUBLIC
            period_start, period_end = self._get_forecast_periods()

            result = await client.get_month_ahead_load_forecast(
                bidding_zone=bidding_zone,
                period_start=period_start,
                period_end=period_end,
            )

            self._validate_market_document(result)

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_year_ahead_load_forecast_real_api(
        self,
        client: DefaultEntsoEClient,
    ) -> None:
        """Test year-ahead load forecast retrieval against real ENTSO-E API."""
        try:
            bidding_zone = AreaCode.CZECH_REPUBLIC
            period_start, period_end = self._get_forecast_periods()

            result = await client.get_year_ahead_load_forecast(
                bidding_zone=bidding_zone,
                period_start=period_start,
                period_end=period_end,
            )

            self._validate_market_document(result)

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_year_ahead_forecast_margin_real_api(
        self,
        client: DefaultEntsoEClient,
    ) -> None:
        """Test year-ahead forecast margin retrieval against real ENTSO-E API."""
        try:
            bidding_zone = AreaCode.CZECH_REPUBLIC
            period_start, period_end = self._get_forecast_periods()

            result = await client.get_year_ahead_forecast_margin(
                bidding_zone=bidding_zone,
                period_start=period_start,
                period_end=period_end,
            )

            self._validate_market_document(result)

        finally:
            await client.close()
