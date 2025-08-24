from datetime import datetime
from types import TracebackType
from typing import Protocol

from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.load.gl_market_document import GlMarketDocument
from entsoe_client.model.market.publication_market_document import (
    PublicationMarketDocument,
)


class EntsoEClient(Protocol):
    """
    Client interface for ENTSO-E Transparency Platform Load Domain API.
    Provides access to load data and forecasts according to ENTSO-E specifications.
    """

    async def get_actual_total_load(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument | None:
        """
        Retrieve actual total load data [6.1.A].
        Returns real-time load consumption data for a specified bidding zone and time period.
        One year range limit applies, minimum time interval is one MTU period.

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
        ...

    async def get_day_ahead_load_forecast(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument | None:
        """
        Retrieve day-ahead total load forecast [6.1.B].
        Returns load forecasts published one day ahead for planning purposes.
        One year range limit applies, minimum time interval is one day.

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
        ...

    async def get_week_ahead_load_forecast(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument | None:
        """
        Retrieve week-ahead total load forecast [6.1.C].
        Returns load forecasts published one week ahead for medium-term planning.
        One year range limit applies, minimum time interval is one week.

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
        ...

    async def get_month_ahead_load_forecast(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument | None:
        """
        Retrieve month-ahead total load forecast [6.1.D].
        Returns load forecasts published one month ahead for long-term planning.
        One year range limit applies, minimum time interval is one month.

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
        ...

    async def get_year_ahead_load_forecast(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument | None:
        """
        Retrieve year-ahead total load forecast [6.1.E].
        Returns load forecasts published one year ahead for strategic planning.
        One year range limit applies, minimum time interval is one year.

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
        ...

    async def get_year_ahead_forecast_margin(
        self,
        bidding_zone: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> GlMarketDocument | None:
        """
        Retrieve year-ahead forecast margin [8.1].
        Returns forecast margin data indicating the uncertainty/confidence level
        of year-ahead load forecasts for capacity planning.
        One year range limit applies, minimum time interval is one year.

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
        ...

    async def get_day_ahead_prices(
        self,
        in_domain: AreaCode,
        out_domain: AreaCode,
        period_start: datetime,
        period_end: datetime,
        offset: int | None = None,
    ) -> PublicationMarketDocument | None:
        """
        Retrieve day-ahead prices [4.2.10].
        Returns day-ahead electricity prices published for bidding zones.
        One year range limit applies, minimum time interval is one day.

        Args:
            in_domain: The bidding zone/domain area code for input
            out_domain: The bidding zone/domain area code for output (must match in_domain)
            period_start: Start of the time period (inclusive)
            period_end: End of the time period (exclusive)
            offset: Optional pagination offset for large result sets

        Returns:
            Market document containing day-ahead price data

        Raises:
            EntsoEClientException: If the request fails or parameters are invalid
        """
        ...

    async def close(self) -> None:
        """Close the client and release any underlying resources."""
        ...

    async def __aenter__(self) -> "EntsoEClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()
