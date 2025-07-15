"""Unit tests for DefaultEntsoEClient."""

# ruff: noqa: PLR0913

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from entsoe_client.client.default_entsoe_client import DefaultEntsoEClient
from entsoe_client.client.entsoe_client_error import EntsoEClientError
from entsoe_client.http_client.exceptions import HttpClientError
from entsoe_client.http_client.http_client import HttpClient
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.document_type import DocumentType
from entsoe_client.model.common.process_type import ProcessType
from entsoe_client.model.load.gl_market_document import GlMarketDocument


class TestDefaultEntsoEClient:
    """Test suite for DefaultEntsoEClient."""

    @pytest.fixture
    def mock_http_client(self) -> AsyncMock:
        """Create a mock HTTP client."""
        mock_client = AsyncMock(spec=HttpClient)
        mock_client.get = AsyncMock(return_value="<xml>mock response</xml>")
        mock_client.close = AsyncMock()
        return mock_client

    @pytest.fixture
    def base_url(self) -> str:
        """Base URL for testing."""
        return "https://web-api.tp.entsoe.eu/api"

    @pytest.fixture
    def client(self, mock_http_client: AsyncMock, base_url: str) -> DefaultEntsoEClient:
        """Create a DefaultEntsoEClient instance for testing."""
        return DefaultEntsoEClient(mock_http_client, base_url)

    @pytest.fixture
    def valid_bidding_zone(self) -> AreaCode:
        """Valid bidding zone for testing."""
        return AreaCode.CZECH_REPUBLIC

    @pytest.fixture
    def valid_start_date(self) -> datetime:
        """Valid start date for testing."""
        return datetime(2024, 1, 1, tzinfo=UTC)

    @pytest.fixture
    def valid_end_date(self) -> datetime:
        """Valid end date for testing."""
        return datetime(2024, 1, 31, tzinfo=UTC)

    @pytest.fixture
    def mock_gl_market_document(self) -> GlMarketDocument:
        """Create a mock GlMarketDocument."""
        mock_doc = Mock(spec=GlMarketDocument)
        mock_doc.mRID = "TEST_ID"
        return mock_doc

    def test_init(self, mock_http_client: AsyncMock, base_url: str) -> None:
        """Test DefaultEntsoEClient initialization."""
        client = DefaultEntsoEClient(mock_http_client, base_url)

        assert client.http_client == mock_http_client
        assert client.base_url == base_url

    @pytest.mark.asyncio
    async def test_get_actual_total_load_success(
        self,
        client: DefaultEntsoEClient,
        mock_http_client: AsyncMock,
        base_url: str,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
        mock_gl_market_document: GlMarketDocument,
    ) -> None:
        """Test successful actual total load retrieval."""
        with patch.object(
            client,
            "_parse_xml_response",
            return_value=mock_gl_market_document,
        ):
            result = await client.get_actual_total_load(
                bidding_zone=valid_bidding_zone,
                period_start=valid_start_date,
                period_end=valid_end_date,
            )

            assert result == mock_gl_market_document
            mock_http_client.get.assert_called_once()

            # Verify the call arguments
            call_args = mock_http_client.get.call_args
            assert call_args[0][0] == base_url
            params = call_args[0][1]
            assert params["documentType"] == DocumentType.SYSTEM_TOTAL_LOAD.code
            assert params["processType"] == ProcessType.REALISED.code
            assert params["outBiddingZone_Domain"] == valid_bidding_zone.code

    @pytest.mark.asyncio
    async def test_get_actual_total_load_with_offset(
        self,
        client: DefaultEntsoEClient,
        mock_http_client: AsyncMock,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
        mock_gl_market_document: GlMarketDocument,
    ) -> None:
        """Test actual total load retrieval with offset parameter."""
        offset = 100

        with patch.object(
            client,
            "_parse_xml_response",
            return_value=mock_gl_market_document,
        ):
            result = await client.get_actual_total_load(
                bidding_zone=valid_bidding_zone,
                period_start=valid_start_date,
                period_end=valid_end_date,
                offset=offset,
            )

            assert result == mock_gl_market_document
            call_args = mock_http_client.get.call_args
            params = call_args[0][1]
            assert params["offset"] == str(offset)

    @pytest.mark.asyncio
    async def test_get_day_ahead_load_forecast_success(
        self,
        client: DefaultEntsoEClient,
        mock_http_client: AsyncMock,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
        mock_gl_market_document: GlMarketDocument,
    ) -> None:
        """Test successful day-ahead load forecast retrieval."""
        with patch.object(
            client,
            "_parse_xml_response",
            return_value=mock_gl_market_document,
        ):
            result = await client.get_day_ahead_load_forecast(
                bidding_zone=valid_bidding_zone,
                period_start=valid_start_date,
                period_end=valid_end_date,
            )

            assert result == mock_gl_market_document
            call_args = mock_http_client.get.call_args
            params = call_args[0][1]
            assert params["documentType"] == DocumentType.SYSTEM_TOTAL_LOAD.code
            assert params["processType"] == ProcessType.DAY_AHEAD.code

    @pytest.mark.asyncio
    async def test_get_week_ahead_load_forecast_success(
        self,
        client: DefaultEntsoEClient,
        mock_http_client: AsyncMock,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
        mock_gl_market_document: GlMarketDocument,
    ) -> None:
        """Test successful week-ahead load forecast retrieval."""
        with patch.object(
            client,
            "_parse_xml_response",
            return_value=mock_gl_market_document,
        ):
            result = await client.get_week_ahead_load_forecast(
                bidding_zone=valid_bidding_zone,
                period_start=valid_start_date,
                period_end=valid_end_date,
            )

            assert result == mock_gl_market_document
            call_args = mock_http_client.get.call_args
            params = call_args[0][1]
            assert params["documentType"] == DocumentType.SYSTEM_TOTAL_LOAD.code
            assert params["processType"] == ProcessType.WEEK_AHEAD.code

    @pytest.mark.asyncio
    async def test_get_month_ahead_load_forecast_success(
        self,
        client: DefaultEntsoEClient,
        mock_http_client: AsyncMock,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
        mock_gl_market_document: GlMarketDocument,
    ) -> None:
        """Test successful month-ahead load forecast retrieval."""
        with patch.object(
            client,
            "_parse_xml_response",
            return_value=mock_gl_market_document,
        ):
            result = await client.get_month_ahead_load_forecast(
                bidding_zone=valid_bidding_zone,
                period_start=valid_start_date,
                period_end=valid_end_date,
            )

            assert result == mock_gl_market_document
            call_args = mock_http_client.get.call_args
            params = call_args[0][1]
            assert params["documentType"] == DocumentType.SYSTEM_TOTAL_LOAD.code
            assert params["processType"] == ProcessType.MONTH_AHEAD.code

    @pytest.mark.asyncio
    async def test_get_year_ahead_load_forecast_success(
        self,
        client: DefaultEntsoEClient,
        mock_http_client: AsyncMock,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
        mock_gl_market_document: GlMarketDocument,
    ) -> None:
        """Test successful year-ahead load forecast retrieval."""
        with patch.object(
            client,
            "_parse_xml_response",
            return_value=mock_gl_market_document,
        ):
            result = await client.get_year_ahead_load_forecast(
                bidding_zone=valid_bidding_zone,
                period_start=valid_start_date,
                period_end=valid_end_date,
            )

            assert result == mock_gl_market_document
            call_args = mock_http_client.get.call_args
            params = call_args[0][1]
            assert params["documentType"] == DocumentType.SYSTEM_TOTAL_LOAD.code
            assert params["processType"] == ProcessType.YEAR_AHEAD.code

    @pytest.mark.asyncio
    async def test_get_year_ahead_forecast_margin_success(
        self,
        client: DefaultEntsoEClient,
        mock_http_client: AsyncMock,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
        mock_gl_market_document: GlMarketDocument,
    ) -> None:
        """Test successful year-ahead forecast margin retrieval."""
        with patch.object(
            client,
            "_parse_xml_response",
            return_value=mock_gl_market_document,
        ):
            result = await client.get_year_ahead_forecast_margin(
                bidding_zone=valid_bidding_zone,
                period_start=valid_start_date,
                period_end=valid_end_date,
            )

            assert result == mock_gl_market_document
            call_args = mock_http_client.get.call_args
            params = call_args[0][1]
            assert params["documentType"] == DocumentType.LOAD_FORECAST_MARGIN.code
            assert params["processType"] == ProcessType.YEAR_AHEAD.code

    @pytest.mark.asyncio
    async def test_execute_request_http_error(
        self,
        client: DefaultEntsoEClient,
        mock_http_client: AsyncMock,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
    ) -> None:
        """Test _execute_request handles HTTP client errors."""
        http_error = HttpClientError("Connection failed")
        mock_http_client.get.side_effect = http_error

        with pytest.raises(EntsoEClientError) as exc_info:
            await client.get_actual_total_load(
                bidding_zone=valid_bidding_zone,
                period_start=valid_start_date,
                period_end=valid_end_date,
            )

        assert "Failed to fetch load data" in str(exc_info.value)
        assert exc_info.value.cause == http_error

    @pytest.mark.asyncio
    async def test_execute_request_xml_parsing_error(
        self,
        client: DefaultEntsoEClient,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
    ) -> None:
        """Test _execute_request handles XML parsing errors."""
        xml_error = Exception("Invalid XML")

        with patch.object(client, "_parse_xml_response", side_effect=xml_error):
            with pytest.raises(EntsoEClientError) as exc_info:
                await client.get_actual_total_load(
                    bidding_zone=valid_bidding_zone,
                    period_start=valid_start_date,
                    period_end=valid_end_date,
                )

            assert "Failed to parse XML response" in str(exc_info.value)
            assert exc_info.value.cause == xml_error

    @pytest.mark.asyncio
    async def test_parse_xml_response_success(
        self,
        client: DefaultEntsoEClient,
        mock_gl_market_document: GlMarketDocument,
    ) -> None:
        """Test _parse_xml_response successfully parses XML."""
        xml_content = "<xml>test content</xml>"

        with patch.object(
            GlMarketDocument,
            "from_xml",
            return_value=mock_gl_market_document,
        ) as mock_from_xml:
            result = client._parse_xml_response(xml_content)

            assert result == mock_gl_market_document
            mock_from_xml.assert_called_once_with(xml_content)

    @pytest.mark.asyncio
    async def test_parse_xml_response_raises_exception(
        self,
        client: DefaultEntsoEClient,
    ) -> None:
        """Test _parse_xml_response raises exceptions properly."""
        xml_content = "<invalid>xml</invalid>"
        xml_error = Exception("Parse error")

        with patch.object(GlMarketDocument, "from_xml", side_effect=xml_error):
            with pytest.raises(Exception, match="Parse error") as exc_info:
                client._parse_xml_response(xml_content)

            assert exc_info.value == xml_error

    @pytest.mark.asyncio
    async def test_close_calls_http_client_close(
        self,
        client: DefaultEntsoEClient,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test close() method calls HTTP client close."""
        await client.close()
        mock_http_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_handles_none_http_client(
        self,
        base_url: str,
    ) -> None:
        """Test close() method handles None HTTP client gracefully."""
        client = DefaultEntsoEClient(None, base_url)

        # Should not raise an exception
        await client.close()

    @pytest.mark.asyncio
    async def test_async_context_manager(
        self,
        client: DefaultEntsoEClient,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test async context manager functionality."""
        async with client as ctx_client:
            assert ctx_client is client

        # Verify close was called on exit
        mock_http_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_methods_use_execute_request(
        self,
        client: DefaultEntsoEClient,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
        mock_gl_market_document: GlMarketDocument,
    ) -> None:
        """Test all public methods use _execute_request internally."""
        with patch.object(
            client,
            "_execute_request",
            return_value=mock_gl_market_document,
        ) as mock_execute:
            # Test all methods
            await client.get_actual_total_load(
                valid_bidding_zone,
                valid_start_date,
                valid_end_date,
            )
            await client.get_day_ahead_load_forecast(
                valid_bidding_zone,
                valid_start_date,
                valid_end_date,
            )
            await client.get_week_ahead_load_forecast(
                valid_bidding_zone,
                valid_start_date,
                valid_end_date,
            )
            await client.get_month_ahead_load_forecast(
                valid_bidding_zone,
                valid_start_date,
                valid_end_date,
            )
            await client.get_year_ahead_load_forecast(
                valid_bidding_zone,
                valid_start_date,
                valid_end_date,
            )
            await client.get_year_ahead_forecast_margin(
                valid_bidding_zone,
                valid_start_date,
                valid_end_date,
            )

            # Verify _execute_request was called 6 times
            assert mock_execute.call_count == 6

    @pytest.mark.asyncio
    async def test_logging_calls_in_methods(
        self,
        client: DefaultEntsoEClient,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
        mock_gl_market_document: GlMarketDocument,
    ) -> None:
        """Test that logging calls are made in all methods."""
        with (
            patch.object(
                client,
                "_execute_request",
                return_value=mock_gl_market_document,
            ),
            patch(
                "entsoe_client.client.default_entsoe_client.logger",
            ) as mock_logger,
        ):
            await client.get_actual_total_load(
                valid_bidding_zone,
                valid_start_date,
                valid_end_date,
            )

            # Verify debug logging was called
            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args[0]
            assert "Fetching actual total load" in call_args[0]
            assert valid_bidding_zone.code in call_args

    @pytest.mark.asyncio
    async def test_request_builder_parameters(
        self,
        client: DefaultEntsoEClient,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
        mock_gl_market_document: GlMarketDocument,
    ) -> None:
        """Test that LoadDomainRequestBuilder is called with correct parameters."""
        offset = 500

        with (
            patch.object(
                client,
                "_execute_request",
                return_value=mock_gl_market_document,
            ),
            patch(
                "entsoe_client.client.default_entsoe_client.LoadDomainRequestBuilder",
            ) as mock_builder_class,
        ):
            mock_builder = Mock()
            mock_builder.build_actual_total_load.return_value = Mock()
            mock_builder_class.return_value = mock_builder

            await client.get_actual_total_load(
                bidding_zone=valid_bidding_zone,
                period_start=valid_start_date,
                period_end=valid_end_date,
                offset=offset,
            )

            # Verify LoadDomainRequestBuilder was called with correct parameters
            mock_builder_class.assert_called_once_with(
                out_bidding_zone_domain=valid_bidding_zone,
                period_start=valid_start_date,
                period_end=valid_end_date,
                offset=offset,
            )
            mock_builder.build_actual_total_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_different_build_methods_called(
        self,
        client: DefaultEntsoEClient,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
        mock_gl_market_document: GlMarketDocument,
    ) -> None:
        """Test that different methods call corresponding build methods."""
        with (
            patch.object(
                client,
                "_execute_request",
                return_value=mock_gl_market_document,
            ),
            patch(
                "entsoe_client.client.default_entsoe_client.LoadDomainRequestBuilder",
            ) as mock_builder_class,
        ):
            mock_builder = Mock()
            mock_builder_class.return_value = mock_builder

            # Set up return values for all build methods
            mock_builder.build_actual_total_load.return_value = Mock()
            mock_builder.build_day_ahead_load_forecast.return_value = Mock()
            mock_builder.build_week_ahead_load_forecast.return_value = Mock()
            mock_builder.build_month_ahead_load_forecast.return_value = Mock()
            mock_builder.build_year_ahead_load_forecast.return_value = Mock()
            mock_builder.build_year_ahead_forecast_margin.return_value = Mock()

            # Test each method calls corresponding build method
            await client.get_actual_total_load(
                valid_bidding_zone,
                valid_start_date,
                valid_end_date,
            )
            mock_builder.build_actual_total_load.assert_called_once()

            await client.get_day_ahead_load_forecast(
                valid_bidding_zone,
                valid_start_date,
                valid_end_date,
            )
            mock_builder.build_day_ahead_load_forecast.assert_called_once()

            await client.get_week_ahead_load_forecast(
                valid_bidding_zone,
                valid_start_date,
                valid_end_date,
            )
            mock_builder.build_week_ahead_load_forecast.assert_called_once()

            await client.get_month_ahead_load_forecast(
                valid_bidding_zone,
                valid_start_date,
                valid_end_date,
            )
            mock_builder.build_month_ahead_load_forecast.assert_called_once()

            await client.get_year_ahead_load_forecast(
                valid_bidding_zone,
                valid_start_date,
                valid_end_date,
            )
            mock_builder.build_year_ahead_load_forecast.assert_called_once()

            await client.get_year_ahead_forecast_margin(
                valid_bidding_zone,
                valid_start_date,
                valid_end_date,
            )
            mock_builder.build_year_ahead_forecast_margin.assert_called_once()
