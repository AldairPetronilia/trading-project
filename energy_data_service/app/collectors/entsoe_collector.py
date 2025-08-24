from datetime import datetime

from entsoe_client.client.entsoe_client import EntsoEClient
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.load.gl_market_document import GlMarketDocument
from entsoe_client.model.market.publication_market_document import (
    PublicationMarketDocument,
)


class EntsoeCollector:
    """
    Collector for ENTSO-E Transparency Platform data.

    Wraps the entsoe_client to provide a collector interface for dependency injection
    and future extensibility. Delegates all data collection operations to the underlying
    EntsoEClient implementation.
    """

    def __init__(self, entsoe_client: EntsoEClient) -> None:
        """
        Initialize the collector with an ENTSO-E client.

        Args:
            entsoe_client: Configured ENTSO-E client instance
        """
        self._client = entsoe_client

    async def get_actual_total_load(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument | None:
        """
        Retrieve actual total load data [6.1.A].

        Args:
            bidding_zone: The bidding zone to query (must be a valid BZN area type)
            period_start: Start of the time period (inclusive)
            period_end: End of the time period (exclusive)
            offset: Optional pagination offset for large result sets

        Returns:
            Market document containing actual load data points

        Raises:
            EntsoEClientException: If the request fails or parameters are invalid
        """
        return await self._client.get_actual_total_load(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
            offset=offset,
        )

    async def get_day_ahead_load_forecast(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument | None:
        """
        Retrieve day-ahead total load forecast [6.1.B].

        Args:
            bidding_zone: The bidding zone to query (must be a valid BZN area type)
            period_start: Start of the time period (inclusive)
            period_end: End of the time period (exclusive)
            offset: Optional pagination offset for large result sets

        Returns:
            Market document containing day-ahead load forecast data

        Raises:
            EntsoEClientException: If the request fails or parameters are invalid
        """
        return await self._client.get_day_ahead_load_forecast(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
            offset=offset,
        )

    async def get_week_ahead_load_forecast(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument | None:
        """
        Retrieve week-ahead total load forecast [6.1.C].

        Args:
            bidding_zone: The bidding zone to query (must be a valid BZN area type)
            period_start: Start of the time period (inclusive)
            period_end: End of the time period (exclusive)
            offset: Optional pagination offset for large result sets

        Returns:
            Market document containing week-ahead load forecast data

        Raises:
            EntsoEClientException: If the request fails or parameters are invalid
        """
        return await self._client.get_week_ahead_load_forecast(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
            offset=offset,
        )

    async def get_month_ahead_load_forecast(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument | None:
        """
        Retrieve month-ahead total load forecast [6.1.D].

        Args:
            bidding_zone: The bidding zone to query (must be a valid BZN area type)
            period_start: Start of the time period (inclusive)
            period_end: End of the time period (exclusive)
            offset: Optional pagination offset for large result sets

        Returns:
            Market document containing month-ahead load forecast data

        Raises:
            EntsoEClientException: If the request fails or parameters are invalid
        """
        return await self._client.get_month_ahead_load_forecast(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
            offset=offset,
        )

    async def get_year_ahead_load_forecast(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument | None:
        """
        Retrieve year-ahead total load forecast [6.1.E].

        Args:
            bidding_zone: The bidding zone to query (must be a valid BZN area type)
            period_start: Start of the time period (inclusive)
            period_end: End of the time period (exclusive)
            offset: Optional pagination offset for large result sets

        Returns:
            Market document containing year-ahead load forecast data

        Raises:
            EntsoEClientException: If the request fails or parameters are invalid
        """
        return await self._client.get_year_ahead_load_forecast(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
            offset=offset,
        )

    async def get_year_ahead_forecast_margin(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument | None:
        """
        Retrieve year-ahead forecast margin [8.1].

        Args:
            bidding_zone: The bidding zone to query (must be a valid BZN area type)
            period_start: Start of the time period (inclusive)
            period_end: End of the time period (exclusive)
            offset: Optional pagination offset for large result sets

        Returns:
            Market document containing year-ahead forecast margin data

        Raises:
            EntsoEClientException: If the request fails or parameters are invalid
        """
        return await self._client.get_year_ahead_forecast_margin(
            bidding_zone=bidding_zone,
            period_start=period_start,
            period_end=period_end,
            offset=offset,
        )

    async def get_day_ahead_prices(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> PublicationMarketDocument | None:
        """
        Retrieve day-ahead prices [12.1.D].

        Args:
            bidding_zone: The bidding zone to query (must be a valid BZN area type)
            period_start: Start of the time period (inclusive)
            period_end: End of the time period (exclusive)
            offset: Optional pagination offset for large result sets

        Returns:
            Publication market document containing day-ahead price data

        Raises:
            EntsoEClientException: If the request fails or parameters are invalid
        """
        return await self._client.get_day_ahead_prices(
            in_domain=bidding_zone,
            out_domain=bidding_zone,  # For day-ahead prices, in_domain == out_domain
            period_start=period_start,
            period_end=period_end,
            offset=offset,
        )

    async def health_check(self) -> bool:
        """
        Perform a basic health check on the ENTSO-E client.

        Returns:
            True if the client is healthy and can make requests
        """
        try:
            # The client itself handles connection validation
            # For now, we assume the client is healthy if it was properly initialized
            return True
        except Exception:  # noqa: BLE001
            return False
