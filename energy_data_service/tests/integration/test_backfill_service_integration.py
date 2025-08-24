"""Integration tests for BackfillService using testcontainers.

This module provides comprehensive integration testing for the BackfillService
using real TimescaleDB testcontainers for database operations while mocking
external API calls to ENTSO-E.

Key Features:
- Real TimescaleDB database with hypertables for time-series testing
- BackfillProgress model integration with real database operations
- Mocked ENTSO-E collector responses for controlled testing
- Full dependency injection testing with real components
- Progress tracking, resumable operations, and error handling scenarios
- Performance testing with large historical datasets
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from app.config.database import Database
from app.config.settings import (
    BackfillConfig,
    DatabaseConfig,
    EntsoEClientConfig,
    Settings,
)
from app.container import Container
from app.exceptions.collector_exceptions import CollectorError
from app.models.backfill_progress import BackfillProgress, BackfillStatus
from app.models.base import Base
from app.models.load_data import EnergyDataPoint, EnergyDataType
from app.repositories.backfill_progress_repository import BackfillProgressRepository
from app.repositories.energy_data_repository import EnergyDataRepository
from app.services.backfill_service import (
    BackfillResult,
    BackfillService,
    CoverageAnalysis,
)
from pydantic import SecretStr
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.business_type import BusinessType
from entsoe_client.model.common.curve_type import CurveType
from entsoe_client.model.common.document_type import DocumentType
from entsoe_client.model.common.domain_mrid import DomainMRID
from entsoe_client.model.common.market_role_type import MarketRoleType
from entsoe_client.model.common.object_aggregation import ObjectAggregation
from entsoe_client.model.common.process_type import ProcessType
from entsoe_client.model.load.gl_market_document import GlMarketDocument
from entsoe_client.model.load.load_period import LoadPeriod
from entsoe_client.model.load.load_point import LoadPoint
from entsoe_client.model.load.load_time_interval import LoadTimeInterval
from entsoe_client.model.load.load_time_series import LoadTimeSeries
from entsoe_client.model.load.market_participant_mrid import MarketParticipantMRID
from entsoe_client.model.market.market_domain_mrid import MarketDomainMRID
from entsoe_client.model.market.market_participant_mrid import (
    MarketParticipantMRID as MarketParticipantMRIDMarket,
)
from entsoe_client.model.market.market_period import MarketPeriod
from entsoe_client.model.market.market_point import MarketPoint
from entsoe_client.model.market.market_time_interval import MarketTimeInterval
from entsoe_client.model.market.market_time_series import MarketTimeSeries
from entsoe_client.model.market.publication_market_document import (
    PublicationMarketDocument,
)


@pytest.fixture(autouse=True)
def reset_container_state() -> Generator:
    """Reset container state before and after each test for proper isolation."""
    # Create a fresh container instance for each test
    yield
    # Reset any singleton providers after each test
    try:
        # Reset the singleton providers to ensure clean state
        if hasattr(Container, "_singletons"):
            Container._singletons.clear()
    except AttributeError:
        pass  # Container might not have this attribute in all versions


@pytest.fixture
def postgres_container() -> Generator[PostgresContainer]:
    """Fixture that provides a TimescaleDB testcontainer."""
    # Use timescale/timescaledb image for TimescaleDB support
    with PostgresContainer("timescale/timescaledb:2.16.1-pg16") as postgres:
        yield postgres


@pytest.fixture
def database_config(postgres_container: PostgresContainer) -> DatabaseConfig:
    """Create DatabaseConfig using testcontainer connection details."""
    return DatabaseConfig(
        host=postgres_container.get_container_host_ip(),
        port=postgres_container.get_exposed_port(5432),
        user=postgres_container.username,
        password=postgres_container.password,
        name=postgres_container.dbname,
    )


@pytest.fixture
def backfill_config() -> BackfillConfig:
    """Create BackfillConfig with test-appropriate settings."""
    return BackfillConfig(
        historical_years=2,
        chunk_months=1,  # Smaller chunks for faster testing
        rate_limit_delay=0.5,  # Minimum allowed rate limiting for tests
        max_concurrent_areas=2,
        enable_progress_persistence=True,
        resume_incomplete_backfills=True,
    )


@pytest.fixture
def settings(
    database_config: DatabaseConfig, backfill_config: BackfillConfig
) -> Settings:
    """Create Settings with testcontainer database config and backfill config."""
    return Settings(
        database=database_config,
        debug=True,
        entsoe_client=EntsoEClientConfig(
            api_token=SecretStr("test-token-12345-67890"),  # Dummy token for testing
        ),
        backfill=backfill_config,
    )


@pytest.fixture
def database(settings: Settings) -> Database:
    """Create Database instance with testcontainer config."""
    return Database(settings)


@pytest.fixture
def container(settings: Settings) -> Container:
    """Create dependency injection container with test settings."""
    container = Container()
    container.config.override(settings)
    return container


@pytest_asyncio.fixture
async def initialized_database(database: Database) -> AsyncGenerator[Database]:
    """Initialize database with TimescaleDB extension and tables."""
    # Initialize database with TimescaleDB extension and tables
    async with database.engine.begin() as conn:
        # Enable TimescaleDB extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        # Convert energy_data_points table to hypertable for time-series optimization
        await conn.execute(
            text(
                """
            SELECT create_hypertable('energy_data_points', 'timestamp',
                                    chunk_time_interval => INTERVAL '1 day',
                                    if_not_exists => TRUE);
        """,
            ),
        )

        # Convert energy_price_points table to hypertable for time-series optimization
        await conn.execute(
            text(
                """
            SELECT create_hypertable('energy_price_points', 'timestamp',
                                    chunk_time_interval => INTERVAL '1 day',
                                    if_not_exists => TRUE);
        """,
            ),
        )

    yield database

    # Cleanup
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def energy_repository(initialized_database: Database) -> EnergyDataRepository:
    """Create EnergyDataRepository with initialized database."""
    return EnergyDataRepository(initialized_database)


@pytest_asyncio.fixture
async def backfill_progress_repository(
    initialized_database: Database,
) -> BackfillProgressRepository:
    """Create BackfillProgressRepository with initialized database."""
    return BackfillProgressRepository(initialized_database)


def create_historical_gl_market_document(
    area_code: AreaCode,
    base_time: datetime,
    process_type: ProcessType = ProcessType.REALISED,
    hours: int = 24,
) -> GlMarketDocument:
    """Create a realistic historical GL_MarketDocument for testing with specified parameters."""
    # Create time interval for historical data
    time_interval = LoadTimeInterval(
        start=base_time,
        end=base_time + timedelta(hours=hours),
    )

    # Create historical data points (15-minute intervals for actual load)
    points = []
    for i in range(hours * 4):  # 4 points per hour (15-minute intervals)
        # Vary the load values to simulate realistic historical data
        base_load = 1000 + (i % 100) * 10  # Varied load pattern
        points.append(LoadPoint(position=i + 1, quantity=base_load + i * 5.5))

    # Create period with historical data
    period = LoadPeriod(
        timeInterval=time_interval,
        resolution="PT15M" if process_type == ProcessType.REALISED else "PT60M",
        points=points,
    )

    # Create time series with the specified area code
    area_code_str = (
        area_code.area_code if hasattr(area_code, "area_code") else str(area_code.code)
    )
    time_series = LoadTimeSeries(
        mRID=f"historical-time-series-{area_code_str}-{base_time.strftime('%Y%m%d')}",
        businessType=BusinessType.CONSUMPTION,
        objectAggregation=ObjectAggregation.AGGREGATED,
        outBiddingZoneDomainMRID=DomainMRID(area_code=area_code),
        quantityMeasureUnitName="MAW",
        curveType=CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK,
        period=period,
    )

    # Create the historical document
    return GlMarketDocument(
        mRID=f"historical-doc-{area_code_str}-{base_time.strftime('%Y%m%d%H%M')}",
        revisionNumber=1,
        type=DocumentType.SYSTEM_TOTAL_LOAD,
        processType=process_type,
        senderMarketParticipantMRID=MarketParticipantMRID(
            value="10X1001A1001A450", coding_scheme=None
        ),
        senderMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
        receiverMarketParticipantMRID=MarketParticipantMRID(
            value="10X1001A1001A450", coding_scheme=None
        ),
        receiverMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
        createdDateTime=base_time,
        timePeriodTimeInterval=time_interval,
        timeSeries=[time_series],
    )


def create_historical_publication_market_document(
    area_code: AreaCode,
    base_time: datetime,
    hours: int = 24,
) -> PublicationMarketDocument:
    """Create a realistic historical PublicationMarketDocument for price testing with specified parameters."""
    # Create time interval for historical data
    time_interval = MarketTimeInterval(
        start=base_time,
        end=base_time + timedelta(hours=hours),
    )

    # Create historical price points (hourly intervals for day-ahead prices)
    points = []
    for i in range(hours):  # 24 points for 24 hours (hourly intervals)
        # Vary the price values to simulate realistic historical data
        base_price = 50.0 + (i % 12) * 2.5  # Varied price pattern (50-80 EUR/MWh range)
        points.append(MarketPoint(position=i + 1, price_amount=base_price + i * 0.5))

    # Create period with historical price data
    period = MarketPeriod(
        timeInterval=time_interval,
        resolution="PT60M",  # Hourly resolution for day-ahead prices
        points=points,
    )

    # Create time series with the specified area code
    area_code_str = (
        area_code.area_code if hasattr(area_code, "area_code") else str(area_code.code)
    )
    time_series = MarketTimeSeries(
        mRID=f"historical-price-series-{area_code_str}-{base_time.strftime('%Y%m%d')}",
        businessType=BusinessType.DAY_AHEAD_PRICES,  # Use appropriate business type for prices
        in_domain_mRID=MarketDomainMRID(area_code=area_code),
        out_domain_mRID=MarketDomainMRID(area_code=area_code),
        currency_unit_name="EUR",
        price_measure_unit_name="MWH",
        curveType=CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK,
        period=period,
    )

    # Create the historical publication document
    return PublicationMarketDocument(
        mRID=f"historical-price-doc-{area_code_str}-{base_time.strftime('%Y%m%d%H%M')}",
        revisionNumber=1,
        type=DocumentType.PRICE_DOCUMENT,
        senderMarketParticipantMRID=MarketParticipantMRIDMarket(
            value="10X1001A1001A450", coding_scheme=None
        ),
        senderMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
        receiverMarketParticipantMRID=MarketParticipantMRIDMarket(
            value="10X1001A1001A450", coding_scheme=None
        ),
        receiverMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
        createdDateTime=base_time,
        periodTimeInterval=time_interval,
        timeSeries=[time_series],
    )


@pytest.fixture
def mock_historical_entsoe_responses() -> dict:
    """Create realistic historical ENTSO-E API response data for different areas and time periods."""
    responses: dict[
        str, dict[str, dict[str, GlMarketDocument | PublicationMarketDocument]]
    ] = {}

    # Create historical documents for different areas and time periods
    areas = [AreaCode.GERMANY, AreaCode.FRANCE, AreaCode.NETHERLANDS]

    for area in areas:
        area_code_str = area.area_code if hasattr(area, "area_code") else str(area.code)
        if area_code_str:
            responses[area_code_str] = {}

            # Create documents for different historical periods
            base_dates = [
                datetime(2022, 1, 1, 0, 0, 0, tzinfo=UTC),  # 2 years ago
                datetime(2022, 6, 1, 0, 0, 0, tzinfo=UTC),  # 1.5 years ago
                datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC),  # 1 year ago
                datetime(2023, 6, 1, 0, 0, 0, tzinfo=UTC),  # 6 months ago
                datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),  # Recent historical
            ]

            for base_date in base_dates:
                date_key = base_date.strftime("%Y%m%d")
                responses[area_code_str][date_key] = {
                    "actual_load": create_historical_gl_market_document(
                        area, base_date, ProcessType.REALISED, 24
                    ),
                    "day_ahead_forecast": create_historical_gl_market_document(
                        area, base_date, ProcessType.DAY_AHEAD, 24
                    ),
                    "week_ahead_forecast": create_historical_gl_market_document(
                        area, base_date, ProcessType.WEEK_AHEAD, 24
                    ),
                    "day_ahead_prices": create_historical_publication_market_document(
                        area, base_date, 24
                    ),
                }

    return responses


@pytest.fixture
def mock_collector(mock_historical_entsoe_responses: dict) -> AsyncMock:
    """Create a mocked collector that returns realistic historical response data."""
    collector = AsyncMock()

    # Helper function to return appropriate historical document based on bidding zone and time period
    def get_historical_document(endpoint_name: str) -> Any:
        def side_effect(
            bidding_zone: AreaCode, period_start: datetime, **_kwargs: Any
        ) -> GlMarketDocument | PublicationMarketDocument:
            area_code_str = (
                bidding_zone.area_code
                if hasattr(bidding_zone, "area_code")
                else str(bidding_zone.code)
            )
            date_key = period_start.strftime("%Y%m%d")

            area_data = mock_historical_entsoe_responses.get(area_code_str, {})
            date_data = area_data.get(date_key, {})

            # Return appropriate document or create a default one
            if endpoint_name in date_data:
                return date_data[endpoint_name]

            # Create a default document for this time period based on endpoint type
            if endpoint_name == "day_ahead_prices":
                return create_historical_publication_market_document(
                    bidding_zone, period_start, 24
                )
            return create_historical_gl_market_document(
                bidding_zone, period_start, ProcessType.REALISED, 24
            )

        return side_effect

    # Configure each collector method to return historical responses
    collector.get_actual_total_load.side_effect = get_historical_document("actual_load")
    collector.get_day_ahead_load_forecast.side_effect = get_historical_document(
        "day_ahead_forecast"
    )
    collector.get_week_ahead_load_forecast.side_effect = get_historical_document(
        "week_ahead_forecast"
    )
    collector.get_month_ahead_load_forecast.side_effect = get_historical_document(
        "actual_load"
    )  # Fallback
    collector.get_year_ahead_load_forecast.side_effect = get_historical_document(
        "actual_load"
    )  # Fallback
    collector.get_year_ahead_forecast_margin.side_effect = get_historical_document(
        "actual_load"
    )  # Fallback

    # Special handling for day_ahead_prices which has different signature
    def get_day_ahead_prices_side_effect(
        **kwargs: Any,
    ) -> PublicationMarketDocument | None:
        # Handle both calling conventions: BackfillService uses bidding_zone, but method expects in_domain/out_domain
        if "bidding_zone" in kwargs:
            # Called by BackfillService with bidding_zone
            area = kwargs["bidding_zone"]
            period_start = kwargs["period_start"]
        elif "in_domain" in kwargs:
            # Called directly with proper signature
            area = kwargs["in_domain"]
            period_start = kwargs["period_start"]
        else:
            error_msg = "No valid area parameter found"
            raise ValueError(error_msg)

        area_code_str = area.area_code if hasattr(area, "area_code") else str(area.code)
        date_key = period_start.strftime("%Y%m%d")

        area_data = mock_historical_entsoe_responses.get(area_code_str, {})
        date_data = area_data.get(date_key, {})

        # Return appropriate document or create a default one
        if "day_ahead_prices" in date_data:
            return date_data["day_ahead_prices"]

        # Create a default document for this time period
        return create_historical_publication_market_document(area, period_start, 24)

    collector.get_day_ahead_prices.side_effect = get_day_ahead_prices_side_effect
    collector.health_check.return_value = True

    return collector


@pytest_asyncio.fixture
async def backfill_service_with_real_db(
    mock_collector: AsyncMock,
    energy_repository: EnergyDataRepository,
    backfill_progress_repository: BackfillProgressRepository,
    container: Container,
    initialized_database: Database,
    backfill_config: BackfillConfig,
) -> BackfillService:
    """Create BackfillService with mocked collector but real database components."""
    # Use real processors from container
    load_processor = container.gl_market_document_processor()
    price_processor = container.publication_market_document_processor()

    # Use real repositories from container
    price_repository = container.energy_price_repository()

    # Get configuration from container
    settings = container.config()
    entsoe_data_collection_config = settings.entsoe_data_collection

    # Create service with mocked collector, real processors, real repositories, and real database
    return BackfillService(
        collector=mock_collector,
        load_processor=load_processor,
        price_processor=price_processor,
        load_repository=energy_repository,
        price_repository=price_repository,
        database=initialized_database,
        config=backfill_config,
        progress_repository=backfill_progress_repository,
        entsoe_data_collection_config=entsoe_data_collection_config,
    )


@pytest.fixture
def sample_historical_energy_data_points() -> list[EnergyDataPoint]:
    """Create sample historical energy data points for pre-populating database."""
    # Create data points from 1 year ago - use recent date to ensure it's within coverage analysis window
    base_time = datetime.now(UTC) - timedelta(days=365)  # 1 year ago from now

    data_points = []
    for i in range(96):  # 24 hours * 4 (15-minute intervals)
        timestamp = base_time + timedelta(minutes=15 * i)
        data_points.append(
            EnergyDataPoint(
                timestamp=timestamp,
                area_code="DE",
                data_type=EnergyDataType.ACTUAL,
                business_type=BusinessType.CONSUMPTION.code,
                quantity=Decimal(f"{1000 + i * 10}.000"),
                unit="MAW",
                data_source="entsoe",
                document_mrid=f"historical-doc-{i}",
                revision_number=1,
                document_created_at=timestamp,
                time_series_mrid=f"historical-ts-{i}",
                resolution="PT15M",
                curve_type="A01",
                object_aggregation="A01",
                position=i + 1,
                period_start=timestamp,
                period_end=timestamp + timedelta(minutes=15),
            )
        )

    return data_points


@pytest.fixture
def sample_backfill_progress() -> BackfillProgress:
    """Create sample BackfillProgress for testing resume functionality."""
    now = datetime.now(UTC)
    return BackfillProgress(
        area_code="DE",
        endpoint_name="actual_load",
        period_start=now - timedelta(days=730),  # 2 years ago
        period_end=now,  # Now
        status=BackfillStatus.FAILED,  # Failed status can be resumed
        total_chunks=24,  # 2 years * 12 months = 24 chunks
        completed_chunks=12,  # Half completed (required for resumable)
        chunk_size_days=30,  # Monthly chunks
        rate_limit_delay=Decimal("0.5"),  # Use valid rate limit delay
        progress_percentage=Decimal("50.00"),
        total_data_points=50000,
        failed_chunks=2,
        started_at=now - timedelta(hours=1),  # Started 1 hour ago
        last_error="Simulated failure for testing resume functionality",
    )


class TestBackfillServiceIntegration:
    """Integration tests for BackfillService with real database and mocked external APIs."""

    @pytest.mark.asyncio
    async def test_database_initialization_with_backfill_progress_table(
        self,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test that database is properly initialized with BackfillProgress table."""
        async with energy_repository.database.session_factory() as session:
            # Check TimescaleDB extension is installed
            result = await session.execute(
                text(
                    """
                SELECT extname FROM pg_extension WHERE extname = 'timescaledb';
            """,
                ),
            )
            extension = result.fetchone()
            assert extension is not None
            assert extension.extname == "timescaledb"

            # Check that backfill_progress table exists
            result = await session.execute(
                text(
                    """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'backfill_progress';
            """,
                ),
            )
            table = result.fetchone()
            assert table is not None
            assert table.table_name == "backfill_progress"

            # Check that energy_data_points table is a hypertable
            result = await session.execute(
                text(
                    """
                SELECT hypertable_name FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'energy_data_points';
            """,
                ),
            )
            hypertable = result.fetchone()
            assert hypertable is not None
            assert hypertable.hypertable_name == "energy_data_points"

    @pytest.mark.asyncio
    async def test_coverage_analysis_fresh_database(
        self,
        backfill_service_with_real_db: BackfillService,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test coverage analysis starting with empty database."""
        # Verify database starts empty
        all_records = await energy_repository.get_all()
        assert len(all_records) == 0

        # Run coverage analysis for limited scope
        areas = [AreaCode.GERMANY]
        endpoints = ["actual_load"]

        coverage_results = await backfill_service_with_real_db.analyze_coverage(
            areas=areas, endpoints=endpoints, years_back=1
        )

        # Verify coverage analysis results
        assert len(coverage_results) == 1
        coverage = coverage_results[0]
        assert isinstance(coverage, CoverageAnalysis)
        assert coverage.area_code == "DE"
        assert coverage.endpoint_name == "actual_load"
        assert coverage.needs_backfill is True  # Empty database needs backfill
        assert coverage.coverage_percentage < 95.0  # Should be very low or 0
        assert coverage.total_missing_points > 0

    @pytest.mark.asyncio
    async def test_coverage_analysis_partial_historical_data(
        self,
        backfill_service_with_real_db: BackfillService,
        energy_repository: EnergyDataRepository,
        sample_historical_energy_data_points: list[EnergyDataPoint],
    ) -> None:
        """Test coverage analysis with some existing historical data."""
        # Pre-populate database with some historical data
        await energy_repository.upsert_batch(sample_historical_energy_data_points)

        # Verify data was stored
        stored_records = await energy_repository.get_all()
        assert len(stored_records) == 96  # 24 hours * 4 points per hour

        # Run coverage analysis
        areas = [AreaCode.GERMANY]
        endpoints = ["actual_load"]

        coverage_results = await backfill_service_with_real_db.analyze_coverage(
            areas=areas, endpoints=endpoints, years_back=2
        )

        # Verify coverage analysis detected the existing data
        assert len(coverage_results) == 1
        coverage = coverage_results[0]
        assert coverage.area_code == "DE"
        assert coverage.endpoint_name == "actual_load"
        assert coverage.actual_data_points == 96  # Found our pre-populated data
        assert coverage.coverage_percentage > 0  # Some coverage exists
        assert coverage.needs_backfill is True  # Still needs more historical data

    @pytest.mark.asyncio
    async def test_coverage_analysis_with_price_endpoints(
        self,
        backfill_service_with_real_db: BackfillService,
    ) -> None:
        """Test coverage analysis specifically for price endpoints with real database."""
        # Test coverage analysis for price endpoints
        results = await backfill_service_with_real_db.analyze_coverage(
            areas=[AreaCode.GERMANY],
            endpoints=["day_ahead_prices"],
            years_back=1,
        )

        # Should get one result for the price endpoint
        assert len(results) == 1
        result = results[0]

        # Verify price endpoint characteristics
        assert result.endpoint_name == "day_ahead_prices"
        assert result.area_code == "DE"
        assert isinstance(result, CoverageAnalysis)

        # For fresh database, should show 0% coverage and need backfill
        assert result.coverage_percentage == 0.0
        assert result.needs_backfill is True
        assert result.actual_data_points == 0
        assert result.expected_data_points > 0

    @pytest.mark.asyncio
    async def test_start_backfill_operation_with_price_endpoint(
        self,
        backfill_service_with_real_db: BackfillService,
    ) -> None:
        """Test complete backfill workflow specifically for price endpoints.

        This test verifies the full integration of price data collection, processing,
        and database storage using the fixed PublicationMarketDocumentProcessor.
        """
        # Define the backfill operation for day-ahead price data
        area_code = "DE"
        endpoint_name = "day_ahead_prices"
        period_start = datetime(2024, 1, 15, tzinfo=UTC)
        period_end = datetime(2024, 1, 16, tzinfo=UTC)

        # Start the backfill operation
        result = await backfill_service_with_real_db.start_backfill(
            area_code=area_code,
            endpoint_name=endpoint_name,
            period_start=period_start,
            period_end=period_end,
            chunk_size_days=1,
        )

        # Verify backfill was created and executed
        assert result is not None
        assert isinstance(result, BackfillResult)

        # The mock should provide successful results
        assert result.success is True
        assert result.data_points_collected > 0
        assert result.chunks_processed > 0

        # Verify price data was inserted into database
        energy_price_repo = backfill_service_with_real_db._price_repository

        # Check that price data points were created with all required fields
        price_points = await energy_price_repo.get_by_time_range(
            area_codes=[area_code], start_time=period_start, end_time=period_end
        )

        # Should have price points from the mock data
        assert len(price_points) > 0

        # Verify all required fields are properly populated (this was the bug we fixed)
        for point in price_points[:3]:  # Check first 3 points
            assert point.document_mrid is not None, "document_mrid should not be None"
            assert point.time_series_mrid is not None, (
                "time_series_mrid should not be None"
            )
            assert point.resolution is not None, "resolution should not be None"
            assert point.document_created_at is not None, (
                "document_created_at should not be None"
            )
            assert point.position is not None, "position should not be None"
            assert point.period_start is not None, "period_start should not be None"
            assert point.period_end is not None, "period_end should not be None"

            # Verify field values make sense
            assert point.area_code == area_code
            assert point.data_type == EnergyDataType.DAY_AHEAD
            assert point.currency_unit_name == "EUR"
            assert point.price_measure_unit_name in [
                "EUR/MWh",
                "MWH",
            ]  # Allow both formats
            assert isinstance(point.price_amount, Decimal)
            assert point.price_amount > 0

        # Price endpoint backfill integration test successful:
        # Created price points with all required fields properly mapped

    @pytest.mark.asyncio
    async def test_mock_collector_price_endpoint_direct_call(
        self,
        mock_collector: AsyncMock,
    ) -> None:
        """Test that mock collector directly handles price endpoint calls correctly."""
        # Test that the mock can handle the BackfillService calling style (bidding_zone)
        result = await mock_collector.get_day_ahead_prices(
            bidding_zone=AreaCode.GERMANY,
            period_start=datetime(2022, 1, 1, 0, 0, 0, tzinfo=UTC),
            period_end=datetime(2022, 1, 2, 0, 0, 0, tzinfo=UTC),
        )

        # Should return a PublicationMarketDocument
        assert result is not None
        assert isinstance(result, PublicationMarketDocument)
        assert len(result.timeSeries) > 0
        assert result.timeSeries[0].period is not None
        assert len(result.timeSeries[0].period.points) > 0

    @pytest.mark.asyncio
    async def test_price_processor_with_mock_document(
        self,
        mock_collector: AsyncMock,
        container: Container,
    ) -> None:
        """Test that the price processor can handle our mock PublicationMarketDocument."""
        # Get the mock document from our collector
        mock_doc = await mock_collector.get_day_ahead_prices(
            bidding_zone=AreaCode.GERMANY,
            period_start=datetime(2022, 1, 1, 0, 0, 0, tzinfo=UTC),
            period_end=datetime(2022, 1, 2, 0, 0, 0, tzinfo=UTC),
        )

        assert mock_doc is not None

        # Get the actual processor that BackfillService uses
        price_processor = container.publication_market_document_processor()

        # Test that the processor can handle the mock document
        try:
            data_points = await price_processor.process([mock_doc])
            assert len(data_points) > 0
            # Verify first data point has expected attributes
            first_point = data_points[0]
            assert hasattr(first_point, "timestamp")
            assert hasattr(first_point, "area_code")
        except (ValueError, AttributeError) as e:
            pytest.fail(f"Price processor failed to handle mock document: {e}")

    @pytest.mark.asyncio
    async def test_processor_and_repository_selection_integration(
        self,
        backfill_service_with_real_db: BackfillService,
    ) -> None:
        """Test that the correct processors and repositories are selected for different endpoint types."""
        # Test load endpoint - should use load processor and repository
        load_processor = backfill_service_with_real_db._get_processor_for_endpoint(
            "actual_load"
        )
        load_repository = backfill_service_with_real_db._get_repository_for_endpoint(
            "actual_load"
        )

        assert load_processor == backfill_service_with_real_db._load_processor
        assert load_repository == backfill_service_with_real_db._load_repository

        # Test price endpoint - should use price processor and repository
        price_processor = backfill_service_with_real_db._get_processor_for_endpoint(
            "day_ahead_prices"
        )
        price_repository = backfill_service_with_real_db._get_repository_for_endpoint(
            "day_ahead_prices"
        )

        assert price_processor == backfill_service_with_real_db._price_processor
        assert price_repository == backfill_service_with_real_db._price_repository

        # Verify processors and repositories are different instances
        assert load_processor != price_processor
        assert load_repository != price_repository

        # Test collector method selection
        load_collector_method = backfill_service_with_real_db._get_collector_method(
            "actual_load"
        )
        price_collector_method = backfill_service_with_real_db._get_collector_method(
            "day_ahead_prices"
        )

        # Should be different methods
        assert load_collector_method != price_collector_method

        # Verify PRICE_ENDPOINTS constant
        assert "day_ahead_prices" in backfill_service_with_real_db.PRICE_ENDPOINTS
        assert "actual_load" not in backfill_service_with_real_db.PRICE_ENDPOINTS

    @pytest.mark.asyncio
    async def test_start_backfill_operation_full_workflow(
        self,
        backfill_service_with_real_db: BackfillService,
        energy_repository: EnergyDataRepository,
        mock_collector: AsyncMock,
    ) -> None:
        """Test complete backfill workflow from start to completion."""
        # Define backfill parameters for a small historical period
        area_code = "DE"
        endpoint_name = "actual_load"
        period_start = datetime(2023, 12, 1, 0, 0, 0, tzinfo=UTC)
        period_end = datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC)  # 1 month

        # Mock rate limiting to speed up test
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await backfill_service_with_real_db.start_backfill(
                area_code=area_code,
                endpoint_name=endpoint_name,
                period_start=period_start,
                period_end=period_end,
                chunk_size_days=7,  # Weekly chunks
            )

        # Verify backfill completed successfully
        assert isinstance(result, BackfillResult)
        assert result.success is True
        assert result.area_code == area_code
        assert result.endpoint_name == endpoint_name
        assert result.data_points_collected > 0
        assert result.chunks_processed > 0
        assert result.chunks_failed == 0
        assert result.end_time is not None
        assert result.duration_seconds > 0

        # Verify data was actually stored in database
        stored_records = await energy_repository.get_all()
        assert len(stored_records) > 0

        # Verify stored data has correct area and type
        sample_record = stored_records[0]
        assert sample_record.area_code == area_code
        assert sample_record.data_type == EnergyDataType.ACTUAL
        assert sample_record.data_source == "entsoe"

        # Verify collector was called with correct parameters
        assert mock_collector.get_actual_total_load.call_count > 0
        # Check that collector was called with the correct area
        call_args = mock_collector.get_actual_total_load.call_args_list[0]
        assert call_args[1]["bidding_zone"] == AreaCode.GERMANY

    @pytest.mark.asyncio
    async def test_backfill_progress_tracking_and_persistence(
        self,
        backfill_service_with_real_db: BackfillService,
        initialized_database: Database,
    ) -> None:
        """Test that backfill progress is properly tracked and persisted to database."""
        # Define backfill parameters
        area_code = "FR"
        endpoint_name = "actual_load"
        period_start = datetime(2023, 11, 1, 0, 0, 0, tzinfo=UTC)
        period_end = datetime(2023, 11, 30, 23, 59, 59, tzinfo=UTC)  # 1 month

        # Mock rate limiting to speed up test
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await backfill_service_with_real_db.start_backfill(
                area_code=area_code,
                endpoint_name=endpoint_name,
                period_start=period_start,
                period_end=period_end,
                chunk_size_days=7,  # Weekly chunks - should create ~4 chunks
            )

        # Verify backfill succeeded
        assert result.success is True

        # Query database directly for backfill progress record
        async with initialized_database.session_factory() as session:
            from app.models.backfill_progress import (
                BackfillProgress as BackfillProgressModel,
            )
            from sqlalchemy import select

            stmt = select(BackfillProgressModel).where(
                BackfillProgressModel.area_code == area_code,
                BackfillProgressModel.endpoint_name == endpoint_name,
            )
            result_db = await session.execute(stmt)
            progress_record = result_db.scalar_one_or_none()

        # Verify progress record exists and has correct data
        assert progress_record is not None
        assert progress_record.area_code == area_code
        assert progress_record.endpoint_name == endpoint_name
        assert progress_record.status == BackfillStatus.COMPLETED
        assert progress_record.progress_percentage == Decimal("100.00")
        assert progress_record.period_start == period_start
        assert progress_record.period_end == period_end
        assert progress_record.total_chunks > 0
        assert progress_record.completed_chunks == progress_record.total_chunks
        assert progress_record.started_at is not None
        assert progress_record.completed_at is not None
        assert progress_record.total_data_points > 0

    @pytest.mark.asyncio
    async def test_resume_backfill_operation(
        self,
        backfill_service_with_real_db: BackfillService,
        initialized_database: Database,
        sample_backfill_progress: BackfillProgress,
    ) -> None:
        """Test resuming an interrupted backfill operation from database state."""
        # First, persist a partially completed backfill progress record
        async with initialized_database.session_factory() as session:
            session.add(sample_backfill_progress)
            await session.commit()
            # Get the ID that was assigned
            backfill_id = sample_backfill_progress.id

        # Mock rate limiting to speed up test
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await backfill_service_with_real_db.resume_backfill(backfill_id)

        # Verify resume operation succeeded
        assert isinstance(result, BackfillResult)
        assert result.success is True
        assert result.backfill_id == backfill_id
        assert result.area_code == "DE"
        assert result.endpoint_name == "actual_load"
        assert result.data_points_collected > 0
        assert result.chunks_processed > 0  # Should have processed remaining chunks

        # Verify progress record was updated to completed
        async with initialized_database.session_factory() as session:
            from app.models.backfill_progress import (
                BackfillProgress as BackfillProgressModel,
            )
            from sqlalchemy import select

            stmt = select(BackfillProgressModel).where(
                BackfillProgressModel.id == backfill_id
            )
            result_db = await session.execute(stmt)
            updated_progress = result_db.scalar_one_or_none()

        assert updated_progress is not None
        assert updated_progress.status == BackfillStatus.COMPLETED
        assert updated_progress.progress_percentage == Decimal("100.00")
        assert updated_progress.completed_at is not None

    @pytest.mark.asyncio
    async def test_backfill_status_monitoring(
        self,
        backfill_service_with_real_db: BackfillService,
        initialized_database: Database,
        sample_backfill_progress: BackfillProgress,
    ) -> None:
        """Test backfill status monitoring and reporting."""
        # Persist a backfill progress record
        async with initialized_database.session_factory() as session:
            session.add(sample_backfill_progress)
            await session.commit()
            backfill_id = sample_backfill_progress.id

        # Get backfill status
        status = await backfill_service_with_real_db.get_backfill_status(backfill_id)

        # Verify status information
        assert isinstance(status, dict)
        assert status["backfill_id"] == backfill_id
        assert status["area_code"] == "DE"
        assert status["endpoint_name"] == "actual_load"
        assert status["status"] == "failed"
        assert status["progress_percentage"] == 50.0
        assert status["total_chunks"] == 24
        assert status["completed_chunks"] == 12
        assert status["failed_chunks"] == 2
        assert status["remaining_chunks"] == 12
        assert status["total_data_points"] == 50000
        assert status["success_rate"] > 0  # Should calculate success rate
        assert status["is_active"] is False  # Failed backfills are not active
        assert status["can_be_resumed"] is True
        assert status["started_at"] is not None

    @pytest.mark.asyncio
    async def test_list_active_backfills(
        self,
        backfill_service_with_real_db: BackfillService,
        initialized_database: Database,
    ) -> None:
        """Test listing all currently active backfill operations."""
        # Create multiple backfill progress records with different statuses
        async with initialized_database.session_factory() as session:
            # Active backfill 1
            active_backfill_1 = BackfillProgress(
                area_code="DE",
                endpoint_name="actual_load",
                period_start=datetime(2022, 1, 1, 0, 0, 0, tzinfo=UTC),
                period_end=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
                status=BackfillStatus.IN_PROGRESS,
                total_chunks=24,
                completed_chunks=10,
                chunk_size_days=30,
                rate_limit_delay=Decimal("0.1"),
                progress_percentage=Decimal("41.67"),
                started_at=datetime.now(UTC),
            )

            # Active backfill 2
            active_backfill_2 = BackfillProgress(
                area_code="FR",
                endpoint_name="day_ahead_forecast",
                period_start=datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC),
                period_end=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
                status=BackfillStatus.PENDING,
                total_chunks=12,
                completed_chunks=0,
                chunk_size_days=30,
                rate_limit_delay=Decimal("0.1"),
                progress_percentage=Decimal("0.00"),
            )

            # Completed backfill (should not appear in active list)
            completed_backfill = BackfillProgress(
                area_code="NL",
                endpoint_name="actual_load",
                period_start=datetime(2023, 6, 1, 0, 0, 0, tzinfo=UTC),
                period_end=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
                status=BackfillStatus.COMPLETED,
                total_chunks=6,
                completed_chunks=6,
                chunk_size_days=30,
                rate_limit_delay=Decimal("0.1"),
                progress_percentage=Decimal("100.00"),
                completed_at=datetime.now(UTC),
            )

            session.add_all([active_backfill_1, active_backfill_2, completed_backfill])
            await session.commit()

        # List active backfills
        active_backfills = await backfill_service_with_real_db.list_active_backfills()

        # Verify only active backfills are returned
        assert len(active_backfills) == 2

        # Check first active backfill
        backfill_1 = next(b for b in active_backfills if b["area_code"] == "DE")
        assert backfill_1["endpoint_name"] == "actual_load"
        assert backfill_1["status"] == "in_progress"
        assert backfill_1["progress_percentage"] == 41.67

        # Check second active backfill
        backfill_2 = next(b for b in active_backfills if b["area_code"] == "FR")
        assert backfill_2["endpoint_name"] == "day_ahead_forecast"
        assert backfill_2["status"] == "pending"
        assert backfill_2["progress_percentage"] == 0.0

    @pytest.mark.asyncio
    async def test_concurrent_backfill_resource_limits(
        self,
        backfill_service_with_real_db: BackfillService,
    ) -> None:
        """Test that concurrent backfill operations respect resource limits."""
        # The test config has max_concurrent_areas=2

        # Test parameters for resource limits

        period_start = datetime(2023, 12, 15, 0, 0, 0, tzinfo=UTC)
        period_end = datetime(2023, 12, 16, 23, 59, 59, tzinfo=UTC)  # 2 days

        # Test the resource limit check directly by adding to active operations
        # Simulate 2 active operations already running
        backfill_service_with_real_db._active_operations["DE_actual_load_1"] = (
            MagicMock()
        )
        backfill_service_with_real_db._active_operations["FR_actual_load_2"] = (
            MagicMock()
        )

        # Now try to start a third operation - this should fail
        from app.exceptions import BackfillResourceError

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(
                BackfillResourceError,
                match="Maximum concurrent backfill operations exceeded",
            ),
        ):
            await backfill_service_with_real_db.start_backfill(
                area_code="NL",
                endpoint_name="actual_load",
                period_start=period_start,
                period_end=period_end,
                chunk_size_days=1,
            )

        # Clear active operations and test that normal operation works
        backfill_service_with_real_db._active_operations.clear()

        # Now a single operation should succeed
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await backfill_service_with_real_db.start_backfill(
                area_code="DE",
                endpoint_name="actual_load",
                period_start=period_start,
                period_end=period_end,
                chunk_size_days=1,
            )
            assert result.success is True

    @pytest.mark.asyncio
    async def test_error_handling_collector_failure_during_backfill(
        self,
        backfill_service_with_real_db: BackfillService,
        mock_collector: AsyncMock,
    ) -> None:
        """Test error handling when collector fails during backfill operations."""
        # Configure collector to fail for specific calls
        mock_collector.get_actual_total_load.side_effect = [
            CollectorError("API temporarily unavailable"),  # First chunk fails
            MagicMock(),  # Second chunk succeeds
            CollectorError("Rate limit exceeded"),  # Third chunk fails
        ]

        # Start backfill operation
        area_code = "DE"
        endpoint_name = "actual_load"
        period_start = datetime(2023, 12, 1, 0, 0, 0, tzinfo=UTC)
        period_end = datetime(2023, 12, 3, 23, 59, 59, tzinfo=UTC)  # 3 days

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await backfill_service_with_real_db.start_backfill(
                area_code=area_code,
                endpoint_name=endpoint_name,
                period_start=period_start,
                period_end=period_end,
                chunk_size_days=1,  # Daily chunks - should create 3 chunks
            )

        # Verify backfill handled errors but completed what it could
        assert isinstance(result, BackfillResult)
        assert result.area_code == area_code
        assert result.endpoint_name == endpoint_name
        assert result.chunks_failed > 0  # Some chunks should have failed
        assert len(result.error_messages) > 0  # Should have error messages

        # Success depends on whether any chunks succeeded
        # The service should continue processing even if some chunks fail

    @pytest.mark.asyncio
    async def test_backfill_data_integrity_and_quality(
        self,
        backfill_service_with_real_db: BackfillService,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test that backfilled data maintains integrity and quality."""
        # Start backfill for a specific time period
        area_code = "DE"
        endpoint_name = "actual_load"
        period_start = datetime(2023, 12, 1, 0, 0, 0, tzinfo=UTC)
        period_end = datetime(2023, 12, 2, 23, 59, 59, tzinfo=UTC)  # 2 days

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await backfill_service_with_real_db.start_backfill(
                area_code=area_code,
                endpoint_name=endpoint_name,
                period_start=period_start,
                period_end=period_end,
                chunk_size_days=1,
            )

        assert result.success is True

        # Verify data quality and integrity
        stored_records = await energy_repository.get_all()
        assert len(stored_records) > 0

        # Check data consistency
        for record in stored_records:
            assert record.area_code == area_code
            assert record.data_type == EnergyDataType.ACTUAL
            assert record.data_source == "entsoe"
            assert record.timestamp >= period_start
            assert record.timestamp <= period_end + timedelta(
                days=1
            )  # Allow some tolerance
            assert record.quantity > 0  # Energy values should be positive
            assert record.unit == "MAW"
            assert record.document_mrid is not None
            assert record.time_series_mrid is not None

        # Check for timestamp continuity (no major gaps)
        sorted_records = sorted(stored_records, key=lambda x: x.timestamp)
        for i in range(1, len(sorted_records)):
            time_gap = (
                sorted_records[i].timestamp - sorted_records[i - 1].timestamp
            ).total_seconds() / 60
            # Allow for reasonable gaps (up to 1 hour for testing flexibility)
            assert time_gap <= 60, f"Time gap too large: {time_gap} minutes"

    @pytest.mark.asyncio
    async def test_backfill_performance_with_large_dataset(
        self,
        backfill_service_with_real_db: BackfillService,
        energy_repository: EnergyDataRepository,
        mock_collector: AsyncMock,
    ) -> None:
        """Test backfill performance with a larger historical dataset."""
        import time

        # Create a larger historical period (3 months)
        area_code = "DE"
        endpoint_name = "actual_load"
        period_start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
        period_end = datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC)  # 3 months

        # Configure mock to return larger datasets
        def create_large_historical_document(**kwargs: Any) -> GlMarketDocument:
            bidding_zone = kwargs.get("bidding_zone", AreaCode.GERMANY)
            period_start_arg = kwargs.get("period_start", datetime.now(UTC))
            return create_historical_gl_market_document(
                bidding_zone, period_start_arg, ProcessType.REALISED, 24
            )

        mock_collector.get_actual_total_load.side_effect = (
            create_large_historical_document
        )

        # Measure backfill performance
        start_time = time.time()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await backfill_service_with_real_db.start_backfill(
                area_code=area_code,
                endpoint_name=endpoint_name,
                period_start=period_start,
                period_end=period_end,
                chunk_size_days=30,  # Monthly chunks
            )

        end_time = time.time()
        duration = end_time - start_time

        # Verify performance and results
        assert result.success is True
        assert result.data_points_collected > 0
        assert result.chunks_processed > 0

        # Should complete within reasonable time (30 seconds for this test size)
        max_duration = 30.0
        assert duration <= max_duration, (
            f"Backfill took {duration}s, expected <= {max_duration}s"
        )

        # Verify data was stored efficiently
        stored_records = await energy_repository.get_all()
        assert len(stored_records) > 0

        # Calculate data processing rate
        data_rate = len(stored_records) / duration if duration > 0 else float("inf")
        min_rate = 100  # At least 100 records per second
        assert data_rate >= min_rate, (
            f"Data rate {data_rate:.1f} records/sec too slow, expected >= {min_rate}"
        )

    @pytest.mark.asyncio
    async def test_multiple_area_backfill_coordination(
        self,
        backfill_service_with_real_db: BackfillService,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test coordinated backfill across multiple areas."""
        # Define backfill parameters for multiple areas
        areas = ["DE", "FR"]
        endpoint_name = "actual_load"
        period_start = datetime(2023, 12, 28, 0, 0, 0, tzinfo=UTC)
        period_end = datetime(2023, 12, 29, 23, 59, 59, tzinfo=UTC)  # 2 days

        # Run backfills for multiple areas
        results = []
        with patch("asyncio.sleep", new_callable=AsyncMock):
            for area_code in areas:
                result = await backfill_service_with_real_db.start_backfill(
                    area_code=area_code,
                    endpoint_name=endpoint_name,
                    period_start=period_start,
                    period_end=period_end,
                    chunk_size_days=1,
                )
                results.append(result)

        # Verify all backfills succeeded
        assert len(results) == 2
        for result in results:
            assert result.success is True
            assert result.data_points_collected > 0

        # Verify data was stored for both areas
        stored_records = await energy_repository.get_all()
        area_codes = {record.area_code for record in stored_records}
        assert "DE" in area_codes
        assert "FR" in area_codes

        # Verify data isolation - each area's data is separate
        de_records = [r for r in stored_records if r.area_code == "DE"]
        fr_records = [r for r in stored_records if r.area_code == "FR"]

        assert len(de_records) > 0
        assert len(fr_records) > 0

        # Verify no cross-contamination
        assert all(r.area_code == "DE" for r in de_records)
        assert all(r.area_code == "FR" for r in fr_records)

    @pytest.mark.asyncio
    async def test_timescaledb_hypertable_performance_with_backfill_data(
        self,
        backfill_service_with_real_db: BackfillService,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test TimescaleDB hypertable performance with backfilled data."""
        import time

        # Perform a backfill to populate data
        area_code = "DE"
        endpoint_name = "actual_load"
        period_start = datetime(2023, 12, 1, 0, 0, 0, tzinfo=UTC)
        period_end = datetime(2023, 12, 5, 23, 59, 59, tzinfo=UTC)  # 5 days

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await backfill_service_with_real_db.start_backfill(
                area_code=area_code,
                endpoint_name=endpoint_name,
                period_start=period_start,
                period_end=period_end,
                chunk_size_days=1,
            )

        assert result.success is True

        # Test time-series query performance
        query_start = time.time()

        time_range_records = await energy_repository.get_by_time_range(
            start_time=period_start,
            end_time=period_end,
            area_codes=[area_code],
            data_types=[EnergyDataType.ACTUAL],
        )

        query_end = time.time()
        query_duration = query_end - query_start

        # Verify query performance
        assert len(time_range_records) > 0
        max_query_time = 5.0  # Should complete within 5 seconds
        assert query_duration <= max_query_time, (
            f"Time-range query took {query_duration}s, expected <= {max_query_time}s"
        )

        # Test TimescaleDB-specific functionality
        async with energy_repository.database.session_factory() as session:
            # Test hypertable chunk information
            result_chunks = await session.execute(
                text(
                    """
                SELECT chunk_name, range_start, range_end
                FROM timescaledb_information.chunks
                WHERE hypertable_name = 'energy_data_points'
                ORDER BY range_start;
                """,
                ),
            )
            chunks = result_chunks.fetchall()

            # Should have created at least one chunk
            assert len(chunks) > 0

            # Test chunk exclusion (should be fast)
            chunk_query_start = time.time()

            await session.execute(
                text(
                    """
                SELECT count(*) FROM energy_data_points
                WHERE timestamp >= :start_time AND timestamp <= :end_time
                AND area_code = :area_code;
                """,
                ),
                {
                    "start_time": period_start,
                    "end_time": period_end,
                    "area_code": area_code,
                },
            )

            chunk_query_end = time.time()
            chunk_query_duration = chunk_query_end - chunk_query_start

            # Chunk-optimized queries should be very fast
            max_chunk_query_time = 1.0
            assert chunk_query_duration <= max_chunk_query_time, (
                f"Chunk query took {chunk_query_duration}s, expected <= {max_chunk_query_time}s"
            )
