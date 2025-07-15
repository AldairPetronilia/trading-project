import logging
from datetime import datetime

from entsoe_client.api.load_domain_request_builder import LoadDomainRequestBuilder
from entsoe_client.client.entsoe_client import EntsoEClient
from entsoe_client.client.entsoe_client_error import EntsoEClientError
from entsoe_client.http.exceptions import HttpClientError
from entsoe_client.http.http_client import HttpClient
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.entsoe_api_request import EntsoEApiRequest
from entsoe_client.model.load.gl_market_document import GlMarketDocument

logger = logging.getLogger(__name__)


class DefaultEntsoEClient(EntsoEClient):
    """
    Default implementation of EntsoEClient for ENTSO-E Transparency Platform Load Domain API.
    Provides HTTP-based access to load data and forecasts with XML response parsing.
    """

    def __init__(self, http_client: HttpClient, base_url: str) -> None:
        """
        Create a new DefaultEntsoEClient.

        Args:
            http_client: HTTP client for making requests
            base_url: Base URL of the ENTSO-E API endpoint
        """
        self.http_client = http_client
        self.base_url = base_url

    async def get_actual_total_load(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument:
        logger.debug(
            "Fetching actual total load for zone: %s, period: %s to %s, offset: %s",
            bidding_zone.code,
            period_start,
            period_end,
            offset,
        )

        request_builder = LoadDomainRequestBuilder(
            out_bidding_zone_domain=bidding_zone,
            period_start=period_start,
            period_end=period_end,
            offset=offset,
        )

        request = request_builder.build_actual_total_load()
        return await self._execute_request(request)

    async def get_day_ahead_load_forecast(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument:
        logger.debug(
            "Fetching day-ahead load forecast for zone: %s, period: %s to %s, offset: %s",
            bidding_zone.code,
            period_start,
            period_end,
            offset,
        )

        request_builder = LoadDomainRequestBuilder(
            out_bidding_zone_domain=bidding_zone,
            period_start=period_start,
            period_end=period_end,
            offset=offset,
        )

        request = request_builder.build_day_ahead_load_forecast()
        return await self._execute_request(request)

    async def get_week_ahead_load_forecast(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument:
        logger.debug(
            "Fetching week-ahead load forecast for zone: %s, period: %s to %s, offset: %s",
            bidding_zone.code,
            period_start,
            period_end,
            offset,
        )

        request_builder = LoadDomainRequestBuilder(
            out_bidding_zone_domain=bidding_zone,
            period_start=period_start,
            period_end=period_end,
            offset=offset,
        )

        request = request_builder.build_week_ahead_load_forecast()
        return await self._execute_request(request)

    async def get_month_ahead_load_forecast(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument:
        logger.debug(
            "Fetching month-ahead load forecast for zone: %s, period: %s to %s, offset: %s",
            bidding_zone.code,
            period_start,
            period_end,
            offset,
        )

        request_builder = LoadDomainRequestBuilder(
            out_bidding_zone_domain=bidding_zone,
            period_start=period_start,
            period_end=period_end,
            offset=offset,
        )

        request = request_builder.build_month_ahead_load_forecast()
        return await self._execute_request(request)

    async def get_year_ahead_load_forecast(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument:
        logger.debug(
            "Fetching year-ahead load forecast for zone: %s, period: %s to %s, offset: %s",
            bidding_zone.code,
            period_start,
            period_end,
            offset,
        )

        request_builder = LoadDomainRequestBuilder(
            out_bidding_zone_domain=bidding_zone,
            period_start=period_start,
            period_end=period_end,
            offset=offset,
        )

        request = request_builder.build_year_ahead_load_forecast()
        return await self._execute_request(request)

    async def get_year_ahead_forecast_margin(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument:
        logger.debug(
            "Fetching year-ahead forecast margin for zone: %s, period: %s to %s, offset: %s",
            bidding_zone.code,
            period_start,
            period_end,
            offset,
        )

        request_builder = LoadDomainRequestBuilder(
            out_bidding_zone_domain=bidding_zone,
            period_start=period_start,
            period_end=period_end,
            offset=offset,
        )

        request = request_builder.build_year_ahead_forecast_margin()
        return await self._execute_request(request)

    async def _execute_request(self, request: EntsoEApiRequest) -> GlMarketDocument:
        """
        Common method to execute any API request and parse the XML response.

        Args:
            request: The API request to execute

        Returns:
            Parsed market document

        Raises:
            EntsoEClientException: If the request fails or response cannot be parsed
        """
        try:
            query_params = request.to_parameter_map()
            xml_response = await self.http_client.get(self.base_url, query_params)

            logger.debug("Received XML response, parsing...")
            return self._parse_xml_response(xml_response)

        except HttpClientError as e:
            logger.exception("HTTP request failed for request: %s", request)
            raise EntsoEClientError.http_request_failed(e) from e
        except Exception as e:
            logger.exception("XML parsing failed")
            raise EntsoEClientError.xml_parsing_failed(e) from e

    def _parse_xml_response(self, xml_content: str) -> GlMarketDocument:
        """
        Parse XML response into GlMarketDocument.

        Args:
            xml_content: XML content to parse

        Returns:
            Parsed market document

        Raises:
            Exception: If XML parsing fails
        """
        return GlMarketDocument.from_xml(xml_content)

    async def close(self) -> None:
        """Close the client and release any underlying resources."""
        if self.http_client:
            await self.http_client.close()
            logger.debug("EntsoE client closed")
