import logging
from datetime import datetime

from pydantic import HttpUrl

from entsoe_client.api.load_domain_request_builder import LoadDomainRequestBuilder
from entsoe_client.client.entsoe_client import EntsoEClient
from entsoe_client.client.entsoe_client_error import EntsoEClientError
from entsoe_client.client.xml_document_detector import (
    XmlDocumentDetector,
    XmlDocumentType,
)
from entsoe_client.http_client.exceptions import HttpClientError
from entsoe_client.http_client.http_client import HttpClient
from entsoe_client.model.acknowledgement.acknowledgement_market_document import (
    AcknowledgementMarketDocument,
)
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.entsoe_api_request import EntsoEApiRequest
from entsoe_client.model.load.gl_market_document import GlMarketDocument

logger = logging.getLogger(__name__)


class DefaultEntsoEClient(EntsoEClient):
    """
    Default implementation of EntsoEClient for ENTSO-E Transparency Platform Load Domain API.
    Provides HTTP-based access to load data and forecasts with XML response parsing.
    """

    def __init__(self, http_client: HttpClient | None, base_url: str) -> None:
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
    ) -> GlMarketDocument | None:
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
    ) -> GlMarketDocument | None:
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
    ) -> GlMarketDocument | None:
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
    ) -> GlMarketDocument | None:
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
    ) -> GlMarketDocument | None:
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
    ) -> GlMarketDocument | None:
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

    async def _execute_request(
        self, request: EntsoEApiRequest
    ) -> GlMarketDocument | None:
        """
        Common method to execute any API request and parse the XML response.
        Enhanced with document type detection for graceful acknowledgement handling.

        Args:
            request: The API request to execute

        Returns:
            Parsed market document, or None if no data is available (acknowledgement with reason code 999)

        Raises:
            EntsoEClientException: If the request fails or response cannot be parsed
        """
        try:
            self._ensure_http_client()

            query_params = request.to_parameter_map()
            # Type assertion safe after _ensure_http_client()
            assert self.http_client is not None  # noqa: S101
            xml_response = await self.http_client.get(
                HttpUrl(self.base_url), query_params
            )

            # Detect document type before parsing
            document_type = XmlDocumentDetector.detect_document_type(xml_response)

            if document_type == XmlDocumentType.ACKNOWLEDGEMENT_MARKET_DOCUMENT:
                ack_doc = AcknowledgementMarketDocument.from_xml(xml_response)
                if ack_doc.is_no_data_available():
                    logger.info(
                        "No data available for request: %s", ack_doc.reason_text
                    )
                    return None  # Graceful no-data return
                logger.warning(
                    "Received acknowledgement with reason: %s", ack_doc.reason_text
                )
                return None

            logger.debug("Received GL_MarketDocument, parsing...")
            return GlMarketDocument.from_xml(xml_response)

        except HttpClientError as e:
            logger.exception("HTTP request failed for request: %s", request)
            raise EntsoEClientError.http_request_failed(e) from e
        except Exception as e:
            logger.exception("Document parsing failed")
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

    def _ensure_http_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self.http_client is None:
            msg = "HTTP client not initialized"
            raise EntsoEClientError(msg)
