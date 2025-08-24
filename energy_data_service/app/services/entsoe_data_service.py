import asyncio
import logging
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import ClassVar

from app.collectors.entsoe_collector import EntsoeCollector
from app.config.settings import EntsoEDataCollectionConfig
from app.exceptions.collector_exceptions import (
    CollectorError,
    map_http_error_to_collector_error,
)
from app.exceptions.processor_exceptions import ProcessorError
from app.exceptions.repository_exceptions import RepositoryError
from app.models.load_data import EnergyDataPoint, EnergyDataType
from app.processors.gl_market_document_processor import GlMarketDocumentProcessor
from app.processors.publication_market_document_processor import (
    PublicationMarketDocumentProcessor,
)
from app.repositories.energy_data_repository import EnergyDataRepository
from app.repositories.energy_price_repository import EnergyPriceRepository

from entsoe_client.client.entsoe_client_error import EntsoEClientError
from entsoe_client.http_client.exceptions import HttpClientError
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.business_type import BusinessType
from entsoe_client.model.load.gl_market_document import GlMarketDocument
from entsoe_client.model.market.publication_market_document import (
    PublicationMarketDocument,
)


class EndpointNames(Enum):
    """Enum for ENTSO-E endpoint names with type safety."""

    ACTUAL_LOAD = "actual_load"
    DAY_AHEAD_FORECAST = "day_ahead_forecast"
    WEEK_AHEAD_FORECAST = "week_ahead_forecast"
    MONTH_AHEAD_FORECAST = "month_ahead_forecast"
    YEAR_AHEAD_FORECAST = "year_ahead_forecast"
    FORECAST_MARGIN = "forecast_margin"

    # Price endpoints
    DAY_AHEAD_PRICES = "day_ahead_prices"


class CollectionResult:
    """Result of a data collection operation."""

    def __init__(
        self,
        area: AreaCode,
        data_type: EnergyDataType,
        *,
        stored_count: int = 0,
        success: bool = True,
        error_message: str | None = None,
        no_data_available: bool = False,
        no_data_reason: str | None = None,
    ) -> None:
        self.stored_count = stored_count
        self.start_time = datetime.now(UTC)
        self.end_time = datetime.now(UTC)
        self.area = area
        self.data_type = data_type
        self.success = success
        self.error_message = error_message
        self.no_data_available = no_data_available
        self.no_data_reason = no_data_reason

    def set_time_range(self, start_time: datetime, end_time: datetime) -> None:
        """Set the time range for this collection result."""
        self.start_time = start_time
        self.end_time = end_time


class EndpointConfig:
    """Configuration for ENTSO-E endpoint collection behavior."""

    def __init__(
        self,
        *,
        data_type: EnergyDataType,
        expected_interval: timedelta,
        max_chunk_days: int,
        rate_limit_delay: float,
        is_forward_looking: bool,
        forecast_horizon: timedelta | None = None,
    ) -> None:
        """
        Initialize endpoint configuration.

        Args:
            data_type: Type of energy data this endpoint provides
            expected_interval: How often to check for new data
            max_chunk_days: Maximum days per API request chunk
            rate_limit_delay: Seconds to wait between API calls
            is_forward_looking: True for forecast data, False for historical data
            forecast_horizon: How far into future to collect (required for forward-looking)
        """
        self.data_type = data_type
        self.expected_interval = expected_interval
        self.max_chunk_days = max_chunk_days
        self.rate_limit_delay = rate_limit_delay
        self.is_forward_looking = is_forward_looking

        if is_forward_looking and forecast_horizon is None:
            msg = f"forecast_horizon is required for forward-looking endpoint: {data_type}"
            raise ValueError(msg)

        self.forecast_horizon = forecast_horizon or timedelta(days=7)


class EntsoEDataService:
    """
    Smart gap-filling orchestration service for ENTSO-E data collection.

    Provides intelligent, near real-time data collection by detecting gaps in the database
    and filling them using the appropriate collector methods. Handles chunking for large
    date ranges and implements rate limiting to respect API constraints.
    """

    ENDPOINT_CONFIGS: ClassVar[dict[EndpointNames, EndpointConfig]] = {
        EndpointNames.ACTUAL_LOAD: EndpointConfig(
            data_type=EnergyDataType.ACTUAL,
            expected_interval=timedelta(minutes=5),
            max_chunk_days=3,
            rate_limit_delay=1.0,
            is_forward_looking=False,
        ),
        EndpointNames.DAY_AHEAD_FORECAST: EndpointConfig(
            data_type=EnergyDataType.DAY_AHEAD,
            expected_interval=timedelta(minutes=15),
            max_chunk_days=7,
            rate_limit_delay=1.0,
            is_forward_looking=True,
            forecast_horizon=timedelta(days=2),
        ),
        EndpointNames.WEEK_AHEAD_FORECAST: EndpointConfig(
            data_type=EnergyDataType.WEEK_AHEAD,
            expected_interval=timedelta(minutes=30),
            max_chunk_days=14,
            rate_limit_delay=1.0,
            is_forward_looking=True,
            forecast_horizon=timedelta(weeks=2),
        ),
        EndpointNames.MONTH_AHEAD_FORECAST: EndpointConfig(
            data_type=EnergyDataType.MONTH_AHEAD,
            expected_interval=timedelta(hours=2),
            max_chunk_days=30,
            rate_limit_delay=1.0,
            is_forward_looking=True,
            forecast_horizon=timedelta(days=62),
        ),
        EndpointNames.YEAR_AHEAD_FORECAST: EndpointConfig(
            data_type=EnergyDataType.YEAR_AHEAD,
            expected_interval=timedelta(hours=6),
            max_chunk_days=90,
            rate_limit_delay=1.0,
            is_forward_looking=True,
            forecast_horizon=timedelta(days=730),
        ),
        EndpointNames.FORECAST_MARGIN: EndpointConfig(
            data_type=EnergyDataType.FORECAST_MARGIN,
            expected_interval=timedelta(hours=12),
            max_chunk_days=30,
            rate_limit_delay=1.0,
            is_forward_looking=True,
            forecast_horizon=timedelta(days=365),
        ),
        # Price endpoints
        EndpointNames.DAY_AHEAD_PRICES: EndpointConfig(
            data_type=EnergyDataType.DAY_AHEAD,  # Reuse existing enum
            expected_interval=timedelta(hours=1),  # Hourly price updates
            max_chunk_days=7,  # Same as load forecasts
            rate_limit_delay=1.0,
            is_forward_looking=False,  # Price data is historical
        ),
    }

    # Define which endpoints use price vs load processing
    PRICE_ENDPOINTS: ClassVar[set[EndpointNames]] = {
        EndpointNames.DAY_AHEAD_PRICES
    }  # Expandable for future price endpoints

    def __init__(
        self,
        collector: EntsoeCollector,
        load_processor: GlMarketDocumentProcessor,  # ← Load data processor
        price_processor: PublicationMarketDocumentProcessor,  # ← Price data processor
        load_repository: EnergyDataRepository,  # ← Load data repository
        price_repository: EnergyPriceRepository,  # ← Price data repository
        entsoe_data_collection_config: EntsoEDataCollectionConfig,
    ) -> None:
        """
        Initialize the EntsoE data service.

        Args:
            collector: ENTSO-E data collector instance
            load_processor: GL market document processor instance for load data
            price_processor: Publication market document processor instance for price data
            load_repository: Energy data repository instance for load data
            price_repository: Energy price repository instance for price data
            entsoe_data_collection_config: ENTSO-E data collection configuration
        """
        self._collector = collector
        self._load_processor = load_processor
        self._price_processor = price_processor
        self._load_repository = load_repository
        self._price_repository = price_repository
        self._entsoe_data_collection_config = entsoe_data_collection_config
        self._logger = logging.getLogger(self.__class__.__name__)

    def _get_processor_for_endpoint(
        self, endpoint: EndpointNames
    ) -> GlMarketDocumentProcessor | PublicationMarketDocumentProcessor:
        """Select appropriate processor based on endpoint type."""
        if endpoint in self.PRICE_ENDPOINTS:
            return self._price_processor
        return self._load_processor

    def _get_repository_for_endpoint(
        self, endpoint: EndpointNames
    ) -> EnergyDataRepository | EnergyPriceRepository:
        """Select appropriate repository based on endpoint type."""
        if endpoint in self.PRICE_ENDPOINTS:
            return self._price_repository
        return self._load_repository

    async def collect_gaps_for_area(
        self, area: AreaCode
    ) -> dict[str, CollectionResult]:
        """
        Collect missing data for all endpoints for a specific area.

        Args:
            area: The area code to collect data for

        Returns:
            Dictionary mapping endpoint names to collection results
        """
        area_name = area.area_code or str(area.code)
        self._logger.info(
            "Starting gap collection for area %s across %d endpoints",
            area_name,
            len(self.ENDPOINT_CONFIGS),
        )

        results: dict[str, CollectionResult] = {}

        for endpoint_name in self.ENDPOINT_CONFIGS:
            try:
                result = await self.collect_gaps_for_endpoint(area, endpoint_name)
                results[endpoint_name.value] = result
            except EntsoEClientError as e:
                if isinstance(e.cause, HttpClientError):
                    self._logger.exception(
                        "EntsoE HTTP client error for area %s, endpoint %s: status=%s, body=%s",
                        area_name,
                        endpoint_name.value,
                        e.cause.status_code,
                        e.cause.response_body,
                    )
                    collector_error = map_http_error_to_collector_error(
                        status_code=e.cause.status_code or 500,
                        response_body=e.cause.response_body,
                        headers=getattr(e.cause, "headers", None),
                        data_source="entsoe",
                        operation=endpoint_name.value,
                        original_error=e,
                    )
                else:
                    self._logger.exception(
                        "EntsoE client error for area %s, endpoint %s",
                        area_name,
                        endpoint_name.value,
                    )
                    collector_error = CollectorError(
                        f"EntsoE client error: {e}",
                        data_source="entsoe",
                        operation=endpoint_name.value,
                        context={"original_error": str(e)},
                    )
                results[endpoint_name.value] = CollectionResult(
                    area=area,
                    data_type=self.ENDPOINT_CONFIGS[endpoint_name].data_type,
                    success=False,
                    error_message=str(collector_error),
                )
            except (CollectorError, ProcessorError, RepositoryError) as e:
                self._logger.exception(
                    "Service error for area %s, endpoint %s",
                    area_name,
                    endpoint_name.value,
                )
                results[endpoint_name.value] = CollectionResult(
                    area=area,
                    data_type=self.ENDPOINT_CONFIGS[endpoint_name].data_type,
                    success=False,
                    error_message=str(e),
                )

        successful_endpoints = sum(1 for result in results.values() if result.success)
        total_stored = sum(result.stored_count for result in results.values())
        self._logger.info(
            "Completed gap collection for area %s: %d/%d endpoints successful, %d total records stored",
            area_name,
            successful_endpoints,
            len(results),
            total_stored,
        )

        return results

    async def collect_gaps_for_endpoint(
        self, area: AreaCode, endpoint_name: EndpointNames
    ) -> CollectionResult:
        """
        Fill gaps for specific endpoint/area combination.

        Args:
            area: The area code to collect data for
            endpoint_name: Name of the endpoint configuration

        Returns:
            Result of the collection operation
        """
        if endpoint_name not in self.ENDPOINT_CONFIGS:
            msg = f"Unknown endpoint: {endpoint_name}"
            raise ValueError(msg)

        area_name = area.area_code or str(area.code)
        config = self.ENDPOINT_CONFIGS[endpoint_name]

        self._logger.debug(
            "Detecting gaps for area %s, endpoint %s (data_type=%s)",
            area_name,
            endpoint_name.value,
            config.data_type.value,
        )

        gap_start, gap_end = await self._detect_gap_for_endpoint(
            area, endpoint_name, config
        )

        if gap_start >= gap_end:
            self._logger.info(
                "No gap detected for area %s, endpoint %s - data is up to date",
                area_name,
                endpoint_name.value,
            )
            result = CollectionResult(
                area=area,
                data_type=config.data_type,
            )
            result.set_time_range(gap_start, gap_end)
            return result

        gap_duration = gap_end - gap_start
        self._logger.info(
            "Gap detected for area %s, endpoint %s: %s to %s (duration: %s)",
            area_name,
            endpoint_name.value,
            gap_start.isoformat(),
            gap_end.isoformat(),
            str(gap_duration),
        )

        return await self.collect_with_chunking(area, endpoint_name, gap_start, gap_end)

    async def collect_all_gaps(self) -> dict[str, dict[str, CollectionResult]]:
        """
        Fill gaps for all configured areas and endpoints.

        Returns:
            Nested dictionary mapping area codes to endpoint results
        """
        areas = self._get_configured_areas()
        results = {}

        for area in areas:
            area_key = area.area_code or str(area.code)
            results[area_key] = await self.collect_gaps_for_area(area)

        return results

    async def collect_with_chunking(
        self,
        area: AreaCode,
        endpoint_name: EndpointNames,
        start_time: datetime,
        end_time: datetime,
    ) -> CollectionResult:
        """
        Collect large date ranges with API-friendly chunking and rate limiting.

        Args:
            area: The area code to collect data for
            endpoint_name: Name of the endpoint configuration
            start_time: Start of the collection period
            end_time: End of the collection period

        Returns:
            Result of the collection operation
        """
        area_name = area.area_code or str(area.code)
        config = self.ENDPOINT_CONFIGS[endpoint_name]
        repository = self._get_repository_for_endpoint(
            endpoint_name
        )  # ← Dynamic selection
        total_stored = 0
        no_data_chunks = 0

        chunks = self._create_time_chunks(start_time, end_time, config.max_chunk_days)

        self._logger.info(
            "Starting chunked collection for area %s, endpoint %s: %d chunks, rate_limit=%.1fs",
            area_name,
            endpoint_name.value,
            len(chunks),
            config.rate_limit_delay,
        )

        for i, (chunk_start, chunk_end) in enumerate(chunks, 1):
            self._logger.debug(
                "Processing chunk %d/%d for area %s, endpoint %s: %s to %s",
                i,
                len(chunks),
                area_name,
                endpoint_name.value,
                chunk_start.isoformat(),
                chunk_end.isoformat(),
            )

            try:
                raw_document = await self._collect_raw_data(
                    area, endpoint_name, chunk_start, chunk_end
                )

                if raw_document:
                    # Handle different document types with proper type safety
                    if endpoint_name in self.PRICE_ENDPOINTS:
                        # Type narrow to PublicationMarketDocument for price endpoints
                        if isinstance(raw_document, PublicationMarketDocument):
                            # Type is now narrowed to PublicationMarketDocument
                            data_points = await self._price_processor.process(
                                [raw_document]
                            )
                        else:
                            self._logger.error(
                                "Expected PublicationMarketDocument for price endpoint %s but got %s",
                                endpoint_name.value,
                                type(raw_document).__name__,
                            )
                            continue
                    # Type narrow to GlMarketDocument for load endpoints
                    elif isinstance(raw_document, GlMarketDocument):
                        # Type is now narrowed to GlMarketDocument
                        data_points = await self._load_processor.process([raw_document])
                    else:
                        self._logger.error(
                            "Expected GlMarketDocument for load endpoint %s but got %s",
                            endpoint_name.value,
                            type(raw_document).__name__,
                        )
                        continue

                    point_count = len(data_points)

                    self._logger.debug(
                        "Processed %d data points from chunk %d/%d for area %s, endpoint %s",
                        point_count,
                        i,
                        len(chunks),
                        area_name,
                        endpoint_name.value,
                    )

                    stored_models = await repository.upsert_batch(
                        data_points
                    )  # ← Uses correct repository
                    stored_count = len(stored_models)
                    total_stored += stored_count

                    self._logger.debug(
                        "Stored %d records from chunk %d/%d for area %s, endpoint %s",
                        stored_count,
                        i,
                        len(chunks),
                        area_name,
                        endpoint_name.value,
                    )
                else:
                    no_data_chunks += 1
                    self._logger.info(
                        "No data available for chunk %d/%d (area %s, endpoint %s) - acknowledgement received",
                        i,
                        len(chunks),
                        area_name,
                        endpoint_name.value,
                    )

                await asyncio.sleep(config.rate_limit_delay)

            except EntsoEClientError as e:
                if isinstance(e.cause, HttpClientError):
                    self._logger.exception(
                        "EntsoE HTTP error in chunk %d/%d for area %s, endpoint %s: status=%s, body=%s",
                        i,
                        len(chunks),
                        area_name,
                        endpoint_name.value,
                        e.cause.status_code,
                        e.cause.response_body,
                    )
                    map_http_error_to_collector_error(
                        status_code=e.cause.status_code or 500,
                        response_body=e.cause.response_body,
                        headers=getattr(e.cause, "headers", None),
                        data_source="entsoe",
                        operation=endpoint_name.value,
                        original_error=e,
                    )
                else:
                    self._logger.exception(
                        "EntsoE client error in chunk %d/%d for area %s, endpoint %s",
                        i,
                        len(chunks),
                        area_name,
                        endpoint_name.value,
                    )
                    CollectorError(
                        f"EntsoE client error: {e}",
                        data_source="entsoe",
                        operation=endpoint_name.value,
                        context={"original_error": str(e)},
                    )
                continue
            except (CollectorError, ProcessorError, RepositoryError):
                self._logger.exception(
                    "Service error in chunk %d/%d for area %s, endpoint %s",
                    i,
                    len(chunks),
                    area_name,
                    endpoint_name.value,
                )
                continue

        self._logger.info(
            "Completed chunked collection for area %s, endpoint %s: %d total records stored from %d chunks (%d no-data chunks)",
            area_name,
            endpoint_name.value,
            total_stored,
            len(chunks),
            no_data_chunks,
        )

        result = CollectionResult(
            area=area,
            data_type=config.data_type,
            stored_count=total_stored,
            no_data_available=no_data_chunks > 0,
            no_data_reason=f"{no_data_chunks}/{len(chunks)} chunks returned no data"
            if no_data_chunks > 0
            else None,
        )
        result.set_time_range(start_time, end_time)
        return result

    async def should_collect_now(
        self, area: AreaCode, endpoint_name: EndpointNames
    ) -> bool:
        """
        Determine if collection is due based on last update and expected intervals.

        Args:
            area: The area code to check
            endpoint_name: Name of the endpoint configuration

        Returns:
            True if collection should happen now, False otherwise
        """
        if endpoint_name not in self.ENDPOINT_CONFIGS:
            return False

        config = self.ENDPOINT_CONFIGS[endpoint_name]
        repository = self._get_repository_for_endpoint(
            endpoint_name
        )  # ← Dynamic selection

        latest_point = (
            await repository.get_latest_for_area_and_type(  # ← Use dynamic repository
                area.area_code or str(area.code),
                config.data_type,
            )
        )

        if not latest_point:
            return True

        next_collection_time = latest_point.timestamp + config.expected_interval
        return datetime.now(latest_point.timestamp.tzinfo) >= next_collection_time

    def _get_configured_areas(self) -> list[AreaCode]:
        """Get configured ENTSO-E areas from settings."""
        areas = []
        for area_code in self._entsoe_data_collection_config.target_areas:
            # Try to find by area_code attribute first
            for area_enum in AreaCode:
                if area_enum.area_code == area_code:
                    areas.append(area_enum)
                    break
            else:
                # Fallback to from_code method
                try:
                    areas.append(AreaCode.from_code(area_code))
                except Exception:  # noqa: BLE001
                    # Log warning and skip invalid area code
                    self._logger.warning(
                        "Skipping invalid ENTSO-E area code: %s", area_code
                    )
        return areas

    async def _detect_gap_for_endpoint(
        self, area: AreaCode, endpoint_name: EndpointNames, config: EndpointConfig
    ) -> tuple[datetime, datetime]:
        """
        Identify missing data periods based on expected collection intervals.
        Handles both backward-looking (historical) and forward-looking (forecast) data types.

        Args:
            area: The area code to check
            endpoint_name: Name of the endpoint to determine correct repository
            config: Endpoint configuration containing direction and horizon information

        Returns:
            Tuple of (gap_start, gap_end) datetimes
        """
        area_name = area.area_code or str(area.code)
        repository = self._get_repository_for_endpoint(
            endpoint_name
        )  # ← Dynamic selection

        latest_point = (
            await repository.get_latest_for_area_and_type(  # ← Use dynamic repository
                area_name,
                config.data_type,
            )
        )

        current_time = datetime.now(UTC)

        if config.is_forward_looking:
            if not latest_point:
                gap_start = current_time
                gap_end = current_time + config.forecast_horizon

                self._logger.debug(
                    "No existing forecast data found for area %s, data_type %s - collecting future data: %s to %s (horizon: %s)",
                    area_name,
                    config.data_type.value,
                    gap_start.isoformat(),
                    gap_end.isoformat(),
                    str(config.forecast_horizon),
                )
            else:
                gap_start = latest_point.timestamp + config.expected_interval
                gap_end = current_time + config.forecast_horizon

                self._logger.debug(
                    "Latest forecast data for area %s, data_type %s found at %s - gap analysis: %s to %s (horizon: %s)",
                    area_name,
                    config.data_type.value,
                    latest_point.timestamp.isoformat(),
                    gap_start.isoformat(),
                    gap_end.isoformat(),
                    str(config.forecast_horizon),
                )
        elif not latest_point:
            gap_start = current_time - timedelta(days=7)
            gap_end = current_time

            self._logger.debug(
                "No existing actual data found for area %s, data_type %s - starting from 7 days ago: %s to %s",
                area_name,
                config.data_type.value,
                gap_start.isoformat(),
                gap_end.isoformat(),
            )
        else:
            gap_start = latest_point.timestamp + config.expected_interval
            gap_end = current_time

            self._logger.debug(
                "Latest actual data for area %s, data_type %s found at %s - gap analysis: %s to %s",
                area_name,
                config.data_type.value,
                latest_point.timestamp.isoformat(),
                gap_start.isoformat(),
                gap_end.isoformat(),
            )

        return gap_start, gap_end

    async def _collect_raw_data(
        self,
        area: AreaCode,
        endpoint_name: EndpointNames,
        start_time: datetime,
        end_time: datetime,
    ) -> GlMarketDocument | PublicationMarketDocument | None:  # ← Updated return type
        """
        Collect raw data from the appropriate collector method.

        Args:
            area: The area code to collect data for
            endpoint_name: Name of the endpoint configuration
            start_time: Start of the collection period
            end_time: End of the collection period

        Returns:
            Raw GL market document or Publication market document or None if no data
        """
        area_name = area.area_code or str(area.code)

        collector_methods = {
            # Existing load methods
            EndpointNames.ACTUAL_LOAD: self._collector.get_actual_total_load,
            EndpointNames.DAY_AHEAD_FORECAST: self._collector.get_day_ahead_load_forecast,
            EndpointNames.WEEK_AHEAD_FORECAST: self._collector.get_week_ahead_load_forecast,
            EndpointNames.MONTH_AHEAD_FORECAST: self._collector.get_month_ahead_load_forecast,
            EndpointNames.YEAR_AHEAD_FORECAST: self._collector.get_year_ahead_load_forecast,
            EndpointNames.FORECAST_MARGIN: self._collector.get_year_ahead_forecast_margin,
            # NEW: Price method
            EndpointNames.DAY_AHEAD_PRICES: self._collector.get_day_ahead_prices,  # ← Add this
        }

        if endpoint_name not in collector_methods:
            msg = f"Unknown endpoint: {endpoint_name}"
            raise ValueError(msg)

        collector_method = collector_methods[endpoint_name]

        self._logger.debug(
            "Making ENTSO-E API request: area=%s, endpoint=%s, period=%s to %s",
            area_name,
            endpoint_name.value,
            start_time.isoformat(),
            end_time.isoformat(),
        )

        result = await collector_method(
            bidding_zone=area,
            period_start=start_time,
            period_end=end_time,
            offset=None,  # Add offset parameter with default None
        )

        if result:
            # Handle different document types for logging
            if hasattr(result, "timeSeries"):  # GlMarketDocument
                time_series_count = len(result.timeSeries) if result.timeSeries else 0
                point_counts = [
                    len(ts.period.points) if ts.period and ts.period.points else 0
                    for ts in (result.timeSeries or [])
                ]
                total_points = sum(point_counts)
            else:  # PublicationMarketDocument - has different structure
                # For PublicationMarketDocument, the structure may be different
                # Use a generic approach for logging
                time_series_count = 0
                total_points = 0
                # Try to access timeSeries if it exists in this document type
                if hasattr(result, "timeSeries") and result.timeSeries:
                    time_series_count = len(result.timeSeries)
                    for ts in result.timeSeries:
                        if (
                            hasattr(ts, "period")
                            and ts.period
                            and hasattr(ts.period, "points")
                            and ts.period.points
                        ):
                            total_points += len(ts.period.points)

            self._logger.debug(
                "ENTSO-E API response received: area=%s, endpoint=%s, time_series=%d, total_points=%d",
                area_name,
                endpoint_name.value,
                time_series_count,
                total_points,
            )
        else:
            self._logger.debug(
                "ENTSO-E API returned no data: area=%s, endpoint=%s, period=%s to %s",
                area_name,
                endpoint_name.value,
                start_time.isoformat(),
                end_time.isoformat(),
            )

        return result

    def _create_time_chunks(
        self, start_time: datetime, end_time: datetime, max_chunk_days: int
    ) -> list[tuple[datetime, datetime]]:
        """
        Split time range into API-friendly chunks.

        Args:
            start_time: Start of the overall period
            end_time: End of the overall period
            max_chunk_days: Maximum days per chunk

        Returns:
            List of (chunk_start, chunk_end) tuples
        """
        chunks = []
        current_start = start_time
        chunk_delta = timedelta(days=max_chunk_days)

        while current_start < end_time:
            chunk_end = min(current_start + chunk_delta, end_time)
            chunks.append((current_start, chunk_end))
            current_start = chunk_end

        return chunks
