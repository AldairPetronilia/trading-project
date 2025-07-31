from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock

import pytest
from app.collectors.entsoe_collector import EntsoeCollector

from entsoe_client.client.entsoe_client import EntsoEClient
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.load.gl_market_document import GlMarketDocument


class TestEntsoeCollector:
    """Test suite for EntsoeCollector."""

    @pytest.fixture
    def mock_entsoe_client(self) -> AsyncMock:
        """Create a mock ENTSO-E client."""
        return AsyncMock(spec=EntsoEClient)

    @pytest.fixture
    def entsoe_collector(self, mock_entsoe_client: AsyncMock) -> EntsoeCollector:
        """Create an EntsoeCollector with mocked dependencies."""
        return EntsoeCollector(entsoe_client=mock_entsoe_client)

    @pytest.fixture
    def sample_bidding_zone(self) -> AreaCode:
        """Create a sample bidding zone for testing."""
        return AreaCode.from_code("10Y1001A1001A83F")  # Germany

    @pytest.fixture
    def sample_period_start(self) -> datetime:
        """Create a sample period start for testing."""
        return datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

    @pytest.fixture
    def sample_period_end(self) -> datetime:
        """Create a sample period end for testing."""
        return datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC)

    @pytest.fixture
    def mock_gl_market_document(self) -> AsyncMock:
        """Create a mock GlMarketDocument."""
        return AsyncMock(spec=GlMarketDocument)

    @pytest.mark.asyncio
    async def test_get_actual_total_load_delegates_to_client(
        self,
        entsoe_collector: EntsoeCollector,
        mock_entsoe_client: AsyncMock,
        sample_bidding_zone: AreaCode,
        sample_period_start: datetime,
        sample_period_end: datetime,
        mock_gl_market_document: AsyncMock,
    ) -> None:
        """Test that get_actual_total_load properly delegates to entsoe_client."""
        mock_entsoe_client.get_actual_total_load.return_value = mock_gl_market_document

        result = await entsoe_collector.get_actual_total_load(
            bidding_zone=sample_bidding_zone,
            period_start=sample_period_start,
            period_end=sample_period_end,
            offset=None,
        )

        mock_entsoe_client.get_actual_total_load.assert_called_once_with(
            bidding_zone=sample_bidding_zone,
            period_start=sample_period_start,
            period_end=sample_period_end,
            offset=None,
        )
        assert result == mock_gl_market_document

    @pytest.mark.asyncio
    async def test_get_actual_total_load_with_offset(
        self,
        entsoe_collector: EntsoeCollector,
        mock_entsoe_client: AsyncMock,
        sample_bidding_zone: AreaCode,
        sample_period_start: datetime,
        sample_period_end: datetime,
        mock_gl_market_document: AsyncMock,
    ) -> None:
        """Test get_actual_total_load with offset parameter."""
        mock_entsoe_client.get_actual_total_load.return_value = mock_gl_market_document
        offset = 100

        result = await entsoe_collector.get_actual_total_load(
            bidding_zone=sample_bidding_zone,
            period_start=sample_period_start,
            period_end=sample_period_end,
            offset=offset,
        )

        mock_entsoe_client.get_actual_total_load.assert_called_once_with(
            bidding_zone=sample_bidding_zone,
            period_start=sample_period_start,
            period_end=sample_period_end,
            offset=offset,
        )
        assert result == mock_gl_market_document

    @pytest.mark.asyncio
    async def test_get_day_ahead_load_forecast_delegates_to_client(
        self,
        entsoe_collector: EntsoeCollector,
        mock_entsoe_client: AsyncMock,
        sample_bidding_zone: AreaCode,
        sample_period_start: datetime,
        sample_period_end: datetime,
        mock_gl_market_document: AsyncMock,
    ) -> None:
        """Test that get_day_ahead_load_forecast properly delegates to entsoe_client."""
        mock_entsoe_client.get_day_ahead_load_forecast.return_value = (
            mock_gl_market_document
        )

        result = await entsoe_collector.get_day_ahead_load_forecast(
            bidding_zone=sample_bidding_zone,
            period_start=sample_period_start,
            period_end=sample_period_end,
            offset=None,
        )

        mock_entsoe_client.get_day_ahead_load_forecast.assert_called_once_with(
            bidding_zone=sample_bidding_zone,
            period_start=sample_period_start,
            period_end=sample_period_end,
            offset=None,
        )
        assert result == mock_gl_market_document

    @pytest.mark.asyncio
    async def test_get_week_ahead_load_forecast_delegates_to_client(
        self,
        entsoe_collector: EntsoeCollector,
        mock_entsoe_client: AsyncMock,
        sample_bidding_zone: AreaCode,
        sample_period_start: datetime,
        sample_period_end: datetime,
        mock_gl_market_document: AsyncMock,
    ) -> None:
        """Test that get_week_ahead_load_forecast properly delegates to entsoe_client."""
        mock_entsoe_client.get_week_ahead_load_forecast.return_value = (
            mock_gl_market_document
        )

        result = await entsoe_collector.get_week_ahead_load_forecast(
            bidding_zone=sample_bidding_zone,
            period_start=sample_period_start,
            period_end=sample_period_end,
            offset=None,
        )

        mock_entsoe_client.get_week_ahead_load_forecast.assert_called_once_with(
            bidding_zone=sample_bidding_zone,
            period_start=sample_period_start,
            period_end=sample_period_end,
            offset=None,
        )
        assert result == mock_gl_market_document

    @pytest.mark.asyncio
    async def test_get_month_ahead_load_forecast_delegates_to_client(
        self,
        entsoe_collector: EntsoeCollector,
        mock_entsoe_client: AsyncMock,
        sample_bidding_zone: AreaCode,
        sample_period_start: datetime,
        sample_period_end: datetime,
        mock_gl_market_document: AsyncMock,
    ) -> None:
        """Test that get_month_ahead_load_forecast properly delegates to entsoe_client."""
        mock_entsoe_client.get_month_ahead_load_forecast.return_value = (
            mock_gl_market_document
        )

        result = await entsoe_collector.get_month_ahead_load_forecast(
            bidding_zone=sample_bidding_zone,
            period_start=sample_period_start,
            period_end=sample_period_end,
            offset=None,
        )

        mock_entsoe_client.get_month_ahead_load_forecast.assert_called_once_with(
            bidding_zone=sample_bidding_zone,
            period_start=sample_period_start,
            period_end=sample_period_end,
            offset=None,
        )
        assert result == mock_gl_market_document

    @pytest.mark.asyncio
    async def test_get_year_ahead_load_forecast_delegates_to_client(
        self,
        entsoe_collector: EntsoeCollector,
        mock_entsoe_client: AsyncMock,
        sample_bidding_zone: AreaCode,
        sample_period_start: datetime,
        sample_period_end: datetime,
        mock_gl_market_document: AsyncMock,
    ) -> None:
        """Test that get_year_ahead_load_forecast properly delegates to entsoe_client."""
        mock_entsoe_client.get_year_ahead_load_forecast.return_value = (
            mock_gl_market_document
        )

        result = await entsoe_collector.get_year_ahead_load_forecast(
            bidding_zone=sample_bidding_zone,
            period_start=sample_period_start,
            period_end=sample_period_end,
            offset=None,
        )

        mock_entsoe_client.get_year_ahead_load_forecast.assert_called_once_with(
            bidding_zone=sample_bidding_zone,
            period_start=sample_period_start,
            period_end=sample_period_end,
            offset=None,
        )
        assert result == mock_gl_market_document

    @pytest.mark.asyncio
    async def test_get_year_ahead_forecast_margin_delegates_to_client(
        self,
        entsoe_collector: EntsoeCollector,
        mock_entsoe_client: AsyncMock,
        sample_bidding_zone: AreaCode,
        sample_period_start: datetime,
        sample_period_end: datetime,
        mock_gl_market_document: AsyncMock,
    ) -> None:
        """Test that get_year_ahead_forecast_margin properly delegates to entsoe_client."""
        mock_entsoe_client.get_year_ahead_forecast_margin.return_value = (
            mock_gl_market_document
        )

        result = await entsoe_collector.get_year_ahead_forecast_margin(
            bidding_zone=sample_bidding_zone,
            period_start=sample_period_start,
            period_end=sample_period_end,
            offset=None,
        )

        mock_entsoe_client.get_year_ahead_forecast_margin.assert_called_once_with(
            bidding_zone=sample_bidding_zone,
            period_start=sample_period_start,
            period_end=sample_period_end,
            offset=None,
        )
        assert result == mock_gl_market_document

    @pytest.mark.asyncio
    async def test_health_check_returns_true_by_default(
        self, entsoe_collector: EntsoeCollector
    ) -> None:
        """Test that health_check returns True for a properly initialized collector."""
        result = await entsoe_collector.health_check()
        assert result is True

    def test_collector_initialization(self, mock_entsoe_client: AsyncMock) -> None:
        """Test that collector is properly initialized with entsoe_client."""
        collector = EntsoeCollector(entsoe_client=mock_entsoe_client)
        assert collector._client == mock_entsoe_client
