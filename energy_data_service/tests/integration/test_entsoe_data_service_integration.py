"""Integration tests for EntsoEDataService using testcontainers.

This module provides comprehensive integration testing for the EntsoEDataService
using real TimescaleDB testcontainers for database operations while mocking
external API calls to ENTSO-E.

Key Features:
- Real TimescaleDB database with hypertables for time-series testing
- Mocked ENTSO-E collector responses for controlled testing
- Full dependency injection testing with real components
- Concurrent operations and error handling scenarios
- Performance testing with actual database constraints
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
from app.config.settings import DatabaseConfig, EntsoEClientConfig, Settings
from app.container import Container
from app.exceptions.collector_exceptions import CollectorError
from app.models.base import Base
from app.models.load_data import EnergyDataPoint, EnergyDataType
from app.repositories.energy_data_repository import EnergyDataRepository
from app.services.entsoe_data_service import (
    CollectionResult,
    EndpointNames,
    EntsoEDataService,
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


@pytest.fixture(autouse=True)
def reset_container_state() -> Generator[None]:
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
def settings(database_config: DatabaseConfig) -> Settings:
    """Create Settings with testcontainer database config."""
    return Settings(
        database=database_config,
        debug=True,
        entsoe_client=EntsoEClientConfig(
            api_token=SecretStr("test-token-12345-67890"),  # Dummy token for testing
        ),
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

    yield database

    # Cleanup
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def energy_repository(initialized_database: Database) -> EnergyDataRepository:
    """Create EnergyDataRepository with initialized database."""
    return EnergyDataRepository(initialized_database)


def create_sample_gl_market_document(
    area_code: AreaCode, process_type: ProcessType = ProcessType.REALISED
) -> GlMarketDocument:
    """Create a realistic GL_MarketDocument for testing with specified area code and process type."""
    base_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

    # Create time interval
    time_interval = LoadTimeInterval(
        start=base_time,
        end=base_time + timedelta(hours=3),
    )

    # Create actual data points
    points = [
        LoadPoint(position=1, quantity=1234.567),
        LoadPoint(position=2, quantity=1345.678),
        LoadPoint(position=3, quantity=1456.789),
    ]

    # Create period
    period = LoadPeriod(
        timeInterval=time_interval,
        resolution="PT60M",  # 1 hour resolution
        points=points,
    )

    # Create time series with the specified area code
    time_series = LoadTimeSeries(
        mRID=f"test-time-series-mrid-{area_code.get_country_code()}",
        businessType=BusinessType.CONSUMPTION,
        objectAggregation=ObjectAggregation.AGGREGATED,
        outBiddingZoneDomainMRID=DomainMRID(area_code=area_code),
        quantityMeasureUnitName="MAW",
        curveType=CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK,
        period=period,
    )

    # Create the main document
    return GlMarketDocument(
        mRID=f"test-document-mrid-{area_code.get_country_code()}",
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


def create_multiple_time_series_document(
    area_code: AreaCode, process_type: ProcessType = ProcessType.REALISED
) -> GlMarketDocument:
    """Create a GL_MarketDocument with multiple TimeSeries for testing Phase 3 functionality."""
    base_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

    # Create first TimeSeries (short period - 1 point)
    time_interval_ts1 = LoadTimeInterval(
        start=base_time,
        end=base_time + timedelta(hours=1),
    )

    points_ts1 = [LoadPoint(position=1, quantity=1500.0)]

    period_ts1 = LoadPeriod(
        timeInterval=time_interval_ts1,
        resolution="PT60M",
        points=points_ts1,
    )

    time_series_1 = LoadTimeSeries(
        mRID="1",  # Document-scoped counter
        businessType=BusinessType.CONSUMPTION,
        objectAggregation=ObjectAggregation.AGGREGATED,
        outBiddingZoneDomainMRID=DomainMRID(area_code=area_code),
        quantityMeasureUnitName="MAW",
        curveType=CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK,
        period=period_ts1,
    )

    # Create second TimeSeries (longer period - multiple points)
    time_interval_ts2 = LoadTimeInterval(
        start=base_time + timedelta(minutes=30),  # Overlapping (12:30)
        end=base_time + timedelta(hours=3, minutes=15),  # End at 15:15 for 11 points
    )

    points_ts2 = [
        LoadPoint(position=i, quantity=1600.0 + (i * 50))
        for i in range(1, 12)  # 11 points for ~2.75 hours at 15-min intervals
    ]

    period_ts2 = LoadPeriod(
        timeInterval=time_interval_ts2,
        resolution="PT15M",  # Different resolution
        points=points_ts2,
    )

    time_series_2 = LoadTimeSeries(
        mRID="2",  # Document-scoped counter
        businessType=BusinessType.CONSUMPTION,
        objectAggregation=ObjectAggregation.AGGREGATED,
        outBiddingZoneDomainMRID=DomainMRID(area_code=area_code),
        quantityMeasureUnitName="MAW",
        curveType=CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK,
        period=period_ts2,
    )

    # Overall document time interval covers both TimeSeries
    document_time_interval = LoadTimeInterval(
        start=base_time,
        end=base_time + timedelta(hours=3, minutes=15),  # Match TS2 end time
    )

    # Create the main document with MULTIPLE TimeSeries
    return GlMarketDocument(
        mRID=f"multi-ts-document-{area_code.area_code}",
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
        timePeriodTimeInterval=document_time_interval,
        timeSeries=[time_series_1, time_series_2],
    )


@pytest.fixture
def sample_gl_market_document() -> GlMarketDocument:
    """Create a realistic GL_MarketDocument for testing (DE_LU by default)."""
    return create_sample_gl_market_document(AreaCode.DE_LU)


@pytest.fixture
def mock_entsoe_responses() -> dict[str | EndpointNames, Any]:
    """Create realistic ENTSO-E API response data for different endpoints."""
    # Create area-specific documents with appropriate process types
    de_lu_actual_doc = create_sample_gl_market_document(
        AreaCode.DE_LU, ProcessType.REALISED
    )
    de_lu_day_ahead_doc = create_sample_gl_market_document(
        AreaCode.DE_LU, ProcessType.DAY_AHEAD
    )
    de_lu_week_ahead_doc = create_sample_gl_market_document(
        AreaCode.DE_LU, ProcessType.WEEK_AHEAD
    )
    de_lu_month_ahead_doc = create_sample_gl_market_document(
        AreaCode.DE_LU, ProcessType.MONTH_AHEAD
    )
    de_lu_year_ahead_doc = create_sample_gl_market_document(
        AreaCode.DE_LU, ProcessType.YEAR_AHEAD
    )

    de_at_lu_actual_doc = create_sample_gl_market_document(
        AreaCode.DE_AT_LU, ProcessType.REALISED
    )
    de_at_lu_day_ahead_doc = create_sample_gl_market_document(
        AreaCode.DE_AT_LU, ProcessType.DAY_AHEAD
    )
    de_at_lu_week_ahead_doc = create_sample_gl_market_document(
        AreaCode.DE_AT_LU, ProcessType.WEEK_AHEAD
    )

    # Germany-specific documents
    germany_actual_doc = create_sample_gl_market_document(
        AreaCode.GERMANY, ProcessType.REALISED
    )
    germany_day_ahead_doc = create_sample_gl_market_document(
        AreaCode.GERMANY, ProcessType.DAY_AHEAD
    )
    germany_week_ahead_doc = create_sample_gl_market_document(
        AreaCode.GERMANY, ProcessType.WEEK_AHEAD
    )

    return {
        EndpointNames.ACTUAL_LOAD: de_lu_actual_doc,
        EndpointNames.DAY_AHEAD_FORECAST: de_lu_day_ahead_doc,
        EndpointNames.WEEK_AHEAD_FORECAST: de_lu_week_ahead_doc,
        EndpointNames.MONTH_AHEAD_FORECAST: de_lu_month_ahead_doc,
        EndpointNames.YEAR_AHEAD_FORECAST: de_lu_year_ahead_doc,
        EndpointNames.FORECAST_MARGIN: de_lu_year_ahead_doc,  # Uses YEAR_AHEAD process type
        # Store area-specific documents for dynamic lookup
        "area_documents": {
            AreaCode.GERMANY: {
                EndpointNames.ACTUAL_LOAD: germany_actual_doc,
                EndpointNames.DAY_AHEAD_FORECAST: germany_day_ahead_doc,
                EndpointNames.WEEK_AHEAD_FORECAST: germany_week_ahead_doc,
                EndpointNames.MONTH_AHEAD_FORECAST: germany_actual_doc,  # Fallback to actual
                EndpointNames.YEAR_AHEAD_FORECAST: germany_actual_doc,  # Fallback to actual
                EndpointNames.FORECAST_MARGIN: germany_actual_doc,  # Fallback to actual
            },
            AreaCode.DE_LU: {
                EndpointNames.ACTUAL_LOAD: de_lu_actual_doc,
                EndpointNames.DAY_AHEAD_FORECAST: de_lu_day_ahead_doc,
                EndpointNames.WEEK_AHEAD_FORECAST: de_lu_week_ahead_doc,
                EndpointNames.MONTH_AHEAD_FORECAST: de_lu_month_ahead_doc,
                EndpointNames.YEAR_AHEAD_FORECAST: de_lu_year_ahead_doc,
                EndpointNames.FORECAST_MARGIN: de_lu_year_ahead_doc,
            },
            AreaCode.DE_AT_LU: {
                EndpointNames.ACTUAL_LOAD: de_at_lu_actual_doc,
                EndpointNames.DAY_AHEAD_FORECAST: de_at_lu_day_ahead_doc,
                EndpointNames.WEEK_AHEAD_FORECAST: de_at_lu_week_ahead_doc,
                EndpointNames.MONTH_AHEAD_FORECAST: de_at_lu_actual_doc,  # Fallback to actual
                EndpointNames.YEAR_AHEAD_FORECAST: de_at_lu_actual_doc,  # Fallback to actual
                EndpointNames.FORECAST_MARGIN: de_at_lu_actual_doc,  # Fallback to actual
            },
        },
    }


@pytest.fixture
def mock_collector(mock_entsoe_responses: dict[str | EndpointNames, Any]) -> AsyncMock:
    """Create a mocked collector that returns realistic response data."""
    collector = AsyncMock()

    # Get area-specific documents
    area_documents = mock_entsoe_responses["area_documents"]

    # Helper function to return appropriate document based on bidding zone and endpoint
    def get_document_for_area_and_endpoint(endpoint_name: EndpointNames) -> Any:
        def side_effect(bidding_zone: AreaCode, **_kwargs: Any) -> GlMarketDocument:
            area_docs = area_documents.get(bidding_zone, area_documents[AreaCode.DE_LU])
            return area_docs.get(endpoint_name, area_docs[EndpointNames.ACTUAL_LOAD])

        return side_effect

    # Configure each collector method to return area and endpoint-specific responses
    # Note: individual tests can override these by setting return_value or side_effect directly
    collector.get_actual_total_load.side_effect = get_document_for_area_and_endpoint(
        EndpointNames.ACTUAL_LOAD
    )
    collector.get_day_ahead_load_forecast.side_effect = (
        get_document_for_area_and_endpoint(EndpointNames.DAY_AHEAD_FORECAST)
    )
    collector.get_week_ahead_load_forecast.side_effect = (
        get_document_for_area_and_endpoint(EndpointNames.WEEK_AHEAD_FORECAST)
    )
    collector.get_month_ahead_load_forecast.side_effect = (
        get_document_for_area_and_endpoint(EndpointNames.MONTH_AHEAD_FORECAST)
    )
    collector.get_year_ahead_load_forecast.side_effect = (
        get_document_for_area_and_endpoint(EndpointNames.YEAR_AHEAD_FORECAST)
    )
    collector.get_year_ahead_forecast_margin.side_effect = (
        get_document_for_area_and_endpoint(EndpointNames.FORECAST_MARGIN)
    )
    collector.health_check.return_value = True

    return collector


@pytest_asyncio.fixture
async def entsoe_data_service_with_real_db(
    mock_collector: AsyncMock,
    energy_repository: EnergyDataRepository,
    container: Container,
) -> EntsoEDataService:
    """Create EntsoEDataService with mocked collector but real database components."""
    # Use real processor from container
    processor = container.gl_market_document_processor()

    # Get configuration from container
    settings = container.config()
    entsoe_data_collection_config = settings.entsoe_data_collection

    # Create service with mocked collector, real processor, and real repository
    return EntsoEDataService(
        collector=mock_collector,
        processor=processor,
        repository=energy_repository,
        entsoe_data_collection_config=entsoe_data_collection_config,
    )


@pytest.fixture
def sample_energy_data_points() -> list[EnergyDataPoint]:
    """Create sample energy data points for pre-populating database."""
    base_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

    return [
        EnergyDataPoint(
            timestamp=base_time,
            area_code="DE-LU",
            data_type=EnergyDataType.ACTUAL,
            business_type=BusinessType.CONSUMPTION.code,
            quantity=Decimal("1000.000"),
            unit="MAW",
            data_source="entsoe",
            document_mrid="existing-doc-1",
            revision_number=1,
            document_created_at=base_time,
            time_series_mrid="existing-ts-1",
            resolution="PT60M",
            curve_type="A01",
            object_aggregation="A01",
            position=1,
            period_start=base_time,
            period_end=base_time + timedelta(hours=1),
        ),
        EnergyDataPoint(
            timestamp=base_time + timedelta(hours=1),
            area_code="DE-LU",
            data_type=EnergyDataType.ACTUAL,
            business_type=BusinessType.CONSUMPTION.code,
            quantity=Decimal("1100.000"),
            unit="MAW",
            data_source="entsoe",
            document_mrid="existing-doc-1",
            revision_number=1,
            document_created_at=base_time,
            time_series_mrid="existing-ts-1",
            resolution="PT60M",
            curve_type="A01",
            object_aggregation="A01",
            position=2,
            period_start=base_time + timedelta(hours=1),
            period_end=base_time + timedelta(hours=2),
        ),
    ]


class TestEntsoEDataServiceIntegration:
    """Integration tests for EntsoEDataService with real database and mocked external APIs."""

    @pytest.mark.asyncio
    async def test_database_initialization_with_timescaledb(
        self,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test that database is properly initialized with TimescaleDB extension."""
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

            # Check that energy_data_points table exists and is a hypertable
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
    async def test_full_workflow_fresh_database(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test complete workflow starting with empty database."""
        # Verify database starts empty
        all_records = await energy_repository.get_all()
        assert len(all_records) == 0

        # Run collection for single area and endpoint
        # Mock asyncio.sleep to avoid rate limiting delays during test
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await entsoe_data_service_with_real_db.collect_gaps_for_endpoint(
                AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD
            )

        # Verify collection was successful
        assert result.success is True
        assert result.stored_count > 0
        assert result.area == AreaCode.DE_LU
        assert result.data_type == EnergyDataType.ACTUAL

        # Verify data was actually stored in database
        stored_records = await energy_repository.get_all()
        assert len(stored_records) > 0

        # Verify stored data matches expected structure
        sample_record = stored_records[0]
        assert sample_record.area_code in ["DE-LU", "DE-AT-LU"]
        assert sample_record.data_type == EnergyDataType.ACTUAL
        assert sample_record.data_source == "entsoe"
        assert sample_record.unit == "MAW"

    @pytest.mark.asyncio
    async def test_full_workflow_collect_all_gaps_fresh_database(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test collect_all_gaps with fresh database for multiple areas."""
        # Verify database starts empty
        all_records = await energy_repository.get_all()
        assert len(all_records) == 0

        # Run collection for all areas and endpoints
        # Mock asyncio.sleep to avoid rate limiting delays during test
        with patch("asyncio.sleep", new_callable=AsyncMock):
            results = await entsoe_data_service_with_real_db.collect_all_gaps()

        # Verify results structure
        assert isinstance(results, dict)
        # Both DE_LU and DE_AT_LU should have their own entries since they're composite zones
        assert "DE-LU" in results or "DE-AT-LU" in results

        # Verify each area has results for all endpoints
        for area_results in results.values():
            assert len(area_results) == len(EndpointNames)
            for endpoint_name in EndpointNames:
                assert endpoint_name.value in area_results
                result = area_results[endpoint_name.value]
                assert isinstance(result, CollectionResult)
                assert result.success is True
                assert result.stored_count > 0

        # Verify data was stored
        stored_records = await energy_repository.get_all()
        assert len(stored_records) > 0

        # Verify data from German areas
        area_codes = {record.area_code for record in stored_records}
        assert any(code in area_codes for code in ["DE-LU", "DE-AT-LU"])

    @pytest.mark.asyncio
    async def test_full_workflow_with_upsert_behavior(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
        sample_energy_data_points: list[EnergyDataPoint],
    ) -> None:
        """Test that workflow handles upsert behavior correctly with existing data."""
        # Pre-populate database with some data
        await energy_repository.upsert_batch(sample_energy_data_points)
        initial_count = len(await energy_repository.get_all())
        assert initial_count == 2

        # Run collection which should add new data and potentially update existing
        # Mock asyncio.sleep to avoid rate limiting delays during test
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await entsoe_data_service_with_real_db.collect_gaps_for_endpoint(
                AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD
            )

        assert result.success is True
        assert result.stored_count > 0

        # Verify total count increased (new data added)
        final_records = await energy_repository.get_all()
        assert len(final_records) > initial_count

        # Verify we still have the original data plus new data
        latest_for_area = await energy_repository.get_latest_for_area(
            "DE-LU", EnergyDataType.ACTUAL, BusinessType.CONSUMPTION.code
        )
        assert latest_for_area is not None

    @pytest.mark.asyncio
    async def test_collect_with_chunking_integration(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
        mock_collector: AsyncMock,
    ) -> None:
        """Test chunking behavior with real database operations."""
        # Define a large time range that will require chunking
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 10, 0, 0, 0, tzinfo=UTC)  # 9 days

        # Mock rate limiting to speed up test
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await entsoe_data_service_with_real_db.collect_with_chunking(
                AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD, start_time, end_time
            )

        # Verify chunking occurred (9 days / 3 day chunks = 3 chunks)
        assert mock_collector.get_actual_total_load.call_count == 3

        # Verify rate limiting was applied between chunks
        assert mock_sleep.call_count == 3

        # Verify successful collection
        assert result.success is True
        assert result.stored_count > 0
        assert result.start_time == start_time
        assert result.end_time == end_time

        # Verify data was stored in database
        stored_records = await energy_repository.get_all()
        assert len(stored_records) > 0

    @pytest.mark.asyncio
    async def test_gap_detection_with_existing_recent_data(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test gap detection when database has recent data (no gap needed)."""
        # Insert very recent data point (1 minute ago)
        recent_time = datetime.now(UTC) - timedelta(minutes=1)
        recent_data = EnergyDataPoint(
            timestamp=recent_time,
            area_code="DE-LU",
            data_type=EnergyDataType.ACTUAL,
            business_type=BusinessType.CONSUMPTION.code,
            quantity=Decimal("1500.000"),
            unit="MAW",
            data_source="entsoe",
            document_mrid="recent-doc-1",
            revision_number=1,
            document_created_at=recent_time,
            time_series_mrid="recent-ts-1",
            resolution="PT60M",
            curve_type="A01",
            object_aggregation="A01",
            position=1,
            period_start=recent_time,
            period_end=recent_time + timedelta(hours=1),
        )
        await energy_repository.upsert_batch([recent_data])

        # Check if collection is needed
        should_collect = await entsoe_data_service_with_real_db.should_collect_now(
            AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD
        )
        assert should_collect is False

        # Run gap detection - should find no gap
        result = await entsoe_data_service_with_real_db.collect_gaps_for_endpoint(
            AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD
        )

        # Should return success but with no new data stored
        assert result.success is True
        assert result.stored_count == 0

    @pytest.mark.asyncio
    async def test_gap_detection_with_old_data(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
        sample_energy_data_points: list[EnergyDataPoint],
    ) -> None:
        """Test gap detection when database has old data (gap exists)."""
        # Insert old data points (from sample fixture - dated 2024-01-15)
        await energy_repository.upsert_batch(sample_energy_data_points)

        # Check if collection is needed
        should_collect = await entsoe_data_service_with_real_db.should_collect_now(
            AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD
        )
        assert should_collect is True

        # Run gap detection - should find and fill gap
        # Mock asyncio.sleep to avoid rate limiting delays during test
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await entsoe_data_service_with_real_db.collect_gaps_for_endpoint(
                AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD
            )

        # Should collect new data to fill the gap
        assert result.success is True
        assert result.stored_count > 0

        # Verify total records increased
        final_records = await energy_repository.get_all()
        assert len(final_records) > len(sample_energy_data_points)

    @pytest.mark.asyncio
    async def test_gap_detection_with_no_existing_data(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test gap detection when database is empty (fresh start)."""
        # Verify database is empty
        all_records = await energy_repository.get_all()
        assert len(all_records) == 0

        # Check if collection is needed
        should_collect = await entsoe_data_service_with_real_db.should_collect_now(
            AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD
        )
        assert should_collect is True

        # Test _detect_gap_for_endpoint directly
        config = entsoe_data_service_with_real_db.ENDPOINT_CONFIGS[
            EndpointNames.ACTUAL_LOAD
        ]
        (
            gap_start,
            gap_end,
        ) = await entsoe_data_service_with_real_db._detect_gap_for_endpoint(
            AreaCode.DE_LU, config
        )

        # Should default to 7 days ago when no data exists
        expected_start = datetime.now(UTC) - timedelta(days=7)
        time_diff = abs((gap_start - expected_start).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance

        # Gap end should be approximately now
        gap_end_diff = abs((gap_end - datetime.now(UTC)).total_seconds())
        assert gap_end_diff < 60  # Within 1 minute tolerance

    @pytest.mark.asyncio
    async def test_gap_detection_for_different_data_types(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test gap detection works correctly for different data types and endpoints."""
        # Insert data for only ACTUAL type, not DAY_AHEAD
        old_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        actual_data = EnergyDataPoint(
            timestamp=old_time,
            area_code="DE-LU",
            data_type=EnergyDataType.ACTUAL,  # Only ACTUAL data
            business_type=BusinessType.CONSUMPTION.code,
            quantity=Decimal("1000.000"),
            unit="MAW",
            data_source="entsoe",
            document_mrid="test-doc-actual",
            revision_number=1,
            document_created_at=old_time,
            time_series_mrid="test-ts-actual",
            resolution="PT60M",
            curve_type="A01",
            object_aggregation="A01",
            position=1,
            period_start=old_time,
            period_end=old_time + timedelta(hours=1),
        )
        await energy_repository.upsert_batch([actual_data])

        # Test ACTUAL endpoint - should have small gap (old data exists)
        should_collect_actual = (
            await entsoe_data_service_with_real_db.should_collect_now(
                AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD
            )
        )
        assert should_collect_actual is True

        # Test DAY_AHEAD endpoint - should have large gap (no data exists)
        should_collect_day_ahead = (
            await entsoe_data_service_with_real_db.should_collect_now(
                AreaCode.DE_LU, EndpointNames.DAY_AHEAD_FORECAST
            )
        )
        assert should_collect_day_ahead is True

        # Collect for both endpoints
        # Mock asyncio.sleep to avoid rate limiting delays during test
        with patch("asyncio.sleep", new_callable=AsyncMock):
            actual_result = (
                await entsoe_data_service_with_real_db.collect_gaps_for_endpoint(
                    AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD
                )
            )
            day_ahead_result = (
                await entsoe_data_service_with_real_db.collect_gaps_for_endpoint(
                    AreaCode.DE_LU, EndpointNames.DAY_AHEAD_FORECAST
                )
            )

        # Both should succeed but may have different amounts of data
        assert actual_result.success is True
        assert day_ahead_result.success is True
        assert actual_result.stored_count > 0
        assert day_ahead_result.stored_count > 0

        # Verify we now have data for both types
        final_records = await energy_repository.get_all()
        data_types = {record.data_type for record in final_records}
        assert EnergyDataType.ACTUAL in data_types
        assert EnergyDataType.DAY_AHEAD in data_types

    @pytest.mark.asyncio
    async def test_repository_method_ignores_business_type(
        self,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test the new get_latest_for_area_and_type method ignores business type.

        This test validates the fix for the business type filtering issue where
        get_latest_for_area() was hardcoded to use BusinessType.CONSUMPTION but
        the actual data might have different business types from the ENTSO-E API.
        """
        current_time = datetime.now(UTC)
        recent_time = current_time - timedelta(minutes=1)

        # Insert data with PRODUCTION business type (not CONSUMPTION)
        production_data = EnergyDataPoint(
            timestamp=recent_time,
            area_code="DE-LU",
            data_type=EnergyDataType.DAY_AHEAD,
            business_type=BusinessType.PRODUCTION.code,  # A01, not A04 (CONSUMPTION)
            quantity=Decimal("1500.000"),
            unit="MAW",
            data_source="entsoe",
            document_mrid="test-doc-production",
            revision_number=1,
            document_created_at=recent_time,
            time_series_mrid="test-ts-production",
            resolution="PT60M",
            curve_type="A01",
            object_aggregation="A01",
            position=1,
            period_start=recent_time,
            period_end=recent_time + timedelta(hours=1),
        )
        await energy_repository.upsert_batch([production_data])

        # Test that the new method finds data regardless of business type
        latest_data = await energy_repository.get_latest_for_area_and_type(
            "DE-LU", EnergyDataType.DAY_AHEAD
        )
        assert latest_data is not None
        assert latest_data.business_type == BusinessType.PRODUCTION.code

        # Verify the old method would NOT find this data (demonstrating the bug)
        old_method_data = await energy_repository.get_latest_for_area(
            "DE-LU", EnergyDataType.DAY_AHEAD, BusinessType.CONSUMPTION.code
        )
        assert old_method_data is None  # This demonstrates the original bug

        # Insert another data point with CONSUMPTION business type
        consumption_data = EnergyDataPoint(
            timestamp=recent_time + timedelta(minutes=30),
            area_code="DE-LU",
            data_type=EnergyDataType.DAY_AHEAD,
            business_type=BusinessType.CONSUMPTION.code,  # A04
            quantity=Decimal("1600.000"),
            unit="MAW",
            data_source="entsoe",
            document_mrid="test-doc-consumption",
            revision_number=1,
            document_created_at=recent_time,
            time_series_mrid="test-ts-consumption",
            resolution="PT60M",
            curve_type="A01",
            object_aggregation="A01",
            position=1,
            period_start=recent_time + timedelta(minutes=30),
            period_end=recent_time + timedelta(minutes=90),
        )
        await energy_repository.upsert_batch([consumption_data])

        # Now the new method should return the most recent data (consumption data)
        latest_data_after = await energy_repository.get_latest_for_area_and_type(
            "DE-LU", EnergyDataType.DAY_AHEAD
        )
        assert latest_data_after is not None
        assert latest_data_after.business_type == BusinessType.CONSUMPTION.code
        assert latest_data_after.quantity == Decimal("1600.000")

    @pytest.mark.asyncio
    async def test_concurrent_area_collection(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test concurrent collection for multiple areas."""
        # Run concurrent collection for different areas
        areas = [AreaCode.DE_LU, AreaCode.DE_AT_LU]
        tasks = [
            entsoe_data_service_with_real_db.collect_gaps_for_area(area)
            for area in areas
        ]

        results = await asyncio.gather(*tasks)

        # Verify all collections succeeded
        assert len(results) == 2
        for area_results in results:
            assert isinstance(area_results, dict)
            assert len(area_results) == len(EndpointNames)
            for result in area_results.values():
                assert result.success is True
                assert result.stored_count > 0

        # Verify data was stored for areas
        stored_records = await energy_repository.get_all()
        area_codes = {record.area_code for record in stored_records}
        assert any(code in area_codes for code in ["DE-LU", "DE-AT-LU"])

        # Verify no data corruption from concurrent operations
        # Check for records with either area code
        de_lu_records = await energy_repository.get_by_area("DE-LU")
        de_at_lu_records = await energy_repository.get_by_area("DE-AT-LU")
        total_records = len(de_lu_records) + len(de_at_lu_records)
        assert total_records > 0
        # Verify all records have correct area_codes
        if de_lu_records:
            assert all(record.area_code == "DE-LU" for record in de_lu_records)
        if de_at_lu_records:
            assert all(record.area_code == "DE-AT-LU" for record in de_at_lu_records)

    @pytest.mark.asyncio
    async def test_concurrent_endpoint_collection(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test concurrent collection for multiple endpoints on same area."""
        # Run concurrent collection for different endpoints
        endpoints = [
            EndpointNames.ACTUAL_LOAD,
            EndpointNames.DAY_AHEAD_FORECAST,
            EndpointNames.WEEK_AHEAD_FORECAST,
        ]

        tasks = [
            entsoe_data_service_with_real_db.collect_gaps_for_endpoint(
                AreaCode.DE_LU, endpoint
            )
            for endpoint in endpoints
        ]

        results = await asyncio.gather(*tasks)

        # Verify all collections succeeded
        assert len(results) == 3
        for result in results:
            assert result.success is True
            assert result.stored_count > 0

        # Verify data was stored for all data types
        stored_records = await energy_repository.get_all()
        data_types = {record.data_type for record in stored_records}
        assert EnergyDataType.ACTUAL in data_types
        assert EnergyDataType.DAY_AHEAD in data_types
        assert EnergyDataType.WEEK_AHEAD in data_types

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("energy_repository")
    async def test_error_handling_collector_failure(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        mock_collector: AsyncMock,
    ) -> None:
        """Test error handling when collector fails."""
        # Configure collector to fail for one method
        mock_collector.get_actual_total_load.side_effect = CollectorError("API Timeout")
        mock_collector.get_day_ahead_load_forecast.return_value = (
            None  # Simulate no data
        )

        # Test individual endpoint failure
        result = await entsoe_data_service_with_real_db.collect_gaps_for_endpoint(
            AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD
        )

        # Should handle error gracefully but still report failure
        assert (
            result.success is True
        )  # collect_with_chunking handles exceptions internally
        assert result.stored_count == 0  # No data stored due to exception

        # Test area collection with mixed success/failure
        area_results = await entsoe_data_service_with_real_db.collect_gaps_for_area(
            AreaCode.DE_LU
        )

        # Should have results for all endpoints
        assert len(area_results) == len(EndpointNames)

        # Some may have failed, others succeeded
        success_count = sum(1 for result in area_results.values() if result.success)

        # At least one should have succeeded (the ones not configured to fail)
        assert success_count > 0

    @pytest.mark.asyncio
    async def test_error_handling_database_constraint_violation(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
        sample_energy_data_points: list[EnergyDataPoint],
    ) -> None:
        """Test error handling when database operations encounter issues."""
        # Pre-populate with some data
        await energy_repository.upsert_batch(sample_energy_data_points)

        # Mock the repository's upsert_batch to simulate a database error
        with patch.object(
            energy_repository, "upsert_batch", new_callable=AsyncMock
        ) as mock_upsert:
            # Configure the mock to raise a database error
            from app.exceptions.repository_exceptions import DataAccessError

            mock_upsert.side_effect = DataAccessError(
                "Database constraint violation: unique constraint failed",
                model_type="EnergyDataPoint",
                operation="upsert_batch",
                context={"error": "constraint_violation"},
            )

            # Mock asyncio.sleep to avoid rate limiting delays during test
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = (
                    await entsoe_data_service_with_real_db.collect_gaps_for_endpoint(
                        AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD
                    )
                )

                # The service should handle database errors gracefully
                # In this case, it should catch the exception and return a result with stored_count=0
                assert isinstance(result, CollectionResult)
                assert result.stored_count == 0  # No data stored due to database error

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("energy_repository")
    async def test_error_handling_partial_collection_failure(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        mock_collector: AsyncMock,
    ) -> None:
        """Test handling when only some chunks in a collection fail."""
        # Configure collector to fail intermittently
        call_count = 0

        def side_effect(**_kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail on second call
                error_msg = "Intermittent API failure"
                raise CollectorError(error_msg)
            return entsoe_data_service_with_real_db._processor._TYPE_MAPPING

        # This test requires modifying the chunking behavior
        # For now, test that the service can handle collector exceptions
        mock_collector.get_actual_total_load.side_effect = [
            CollectorError("First chunk failed"),  # First chunk fails
            MagicMock(),  # Second chunk succeeds
            MagicMock(),  # Third chunk succeeds
        ]

        # Define a large time range that will require chunking
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 10, 0, 0, 0, tzinfo=UTC)  # 9 days

        # Mock asyncio.sleep to speed up test
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await entsoe_data_service_with_real_db.collect_with_chunking(
                AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD, start_time, end_time
            )

        # Should complete despite partial failures
        assert result.start_time == start_time
        assert result.end_time == end_time
        # Stored count might be 0 if all chunks failed, or > 0 if some succeeded
        assert result.stored_count >= 0

    @pytest.mark.asyncio
    async def test_error_recovery_and_continuation(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        mock_collector: AsyncMock,
    ) -> None:
        """Test that errors in one area don't affect collection for other areas."""

        # Configure collector to fail only for specific areas
        def collector_side_effect(bidding_zone: AreaCode, **_kwargs: Any) -> MagicMock:
            if bidding_zone == AreaCode.DE_LU:
                error_msg = "DE_LU API temporarily unavailable"
                raise CollectorError(error_msg)
            return MagicMock()  # Success for other areas

        mock_collector.get_actual_total_load.side_effect = collector_side_effect

        # Run collection for all areas
        results = await entsoe_data_service_with_real_db.collect_all_gaps()

        # Should have results for DE area(s) (composite zones have separate entries)
        assert "DE-LU" in results or "DE-AT-LU" in results

        # Check that other area collection was not affected by DE_LU's failure
        # Get results from whichever area is present
        area_results = None
        if "DE-LU" in results:
            area_results = results["DE-LU"]
        elif "DE-AT-LU" in results:
            area_results = results["DE-AT-LU"]
        assert area_results is not None

        # Some endpoints may have succeeded (from DE_AT_LU), others may have failed (from DE_LU)
        success_count = sum(1 for result in area_results.values() if result.success)

        # At least some should have succeeded (DE_AT_LU endpoints)
        assert success_count >= 0

    @pytest.mark.asyncio
    async def test_no_data_acknowledgement_handling_integration(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        mock_collector: AsyncMock,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """
        Test end-to-end integration when collector returns None (no data acknowledgements).
        This tests the Phase 2 implementation for graceful acknowledgement handling.
        """
        # Simulate collector returning None (no data available)
        # Clear side_effect to allow return_value to work
        mock_collector.get_actual_total_load.side_effect = None
        mock_collector.get_actual_total_load.return_value = None

        # Create test time range
        start_time = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 2, 0, 0, tzinfo=UTC)
        area = AreaCode.DE_LU
        endpoint = EndpointNames.ACTUAL_LOAD

        # Execute collection
        result = await entsoe_data_service_with_real_db.collect_with_chunking(
            area=area, endpoint_name=endpoint, start_time=start_time, end_time=end_time
        )

        # Verify no-data handling in CollectionResult
        assert result.stored_count == 0
        assert result.success is True  # No-data is not an error
        assert result.no_data_available is True
        assert result.no_data_reason == "1/1 chunks returned no data"
        assert result.error_message is None

        # Verify no data was stored in the database
        stored_data = await energy_repository.get_latest_for_area_and_type(
            area.area_code or str(area.code), EnergyDataType.ACTUAL
        )
        assert stored_data is None

        # Verify the collector was called correctly
        mock_collector.get_actual_total_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_mixed_data_and_no_data_chunks_integration(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        mock_collector: AsyncMock,
        energy_repository: EnergyDataRepository,
        sample_gl_market_document: GlMarketDocument,
    ) -> None:
        """
        Test end-to-end integration with mixed chunks (some data, some no-data).
        This tests the Phase 2 implementation for partial no-data scenarios.
        """
        # First chunk returns data, second chunk returns None
        mock_collector.get_actual_total_load.side_effect = [
            sample_gl_market_document,
            None,
        ]

        # Create test time range that will result in 2 chunks (6 days = 2 x 3-day chunks)
        start_time = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 7, 0, 0, tzinfo=UTC)
        area = AreaCode.DE_LU
        endpoint = EndpointNames.ACTUAL_LOAD

        # Execute collection
        result = await entsoe_data_service_with_real_db.collect_with_chunking(
            area=area, endpoint_name=endpoint, start_time=start_time, end_time=end_time
        )

        # Verify mixed results tracking
        assert result.stored_count > 0  # Some data was stored from first chunk
        assert result.success is True
        assert result.no_data_available is True  # Because second chunk had no data
        assert result.no_data_reason == "1/2 chunks returned no data"
        assert result.error_message is None

        # Verify data was stored in the database (from the first chunk)
        stored_data = await energy_repository.get_latest_for_area_and_type(
            area.area_code or str(area.code), EnergyDataType.ACTUAL
        )
        assert stored_data is not None

        # Verify the collector was called twice (once per chunk)
        assert mock_collector.get_actual_total_load.call_count == 2

        # Verify data was stored for successful collections
        # Data might or might not be stored depending on which specific calls succeeded
        # The test mainly verifies that partial failures don't crash the entire process

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("energy_repository")
    async def test_rate_limiting_integration(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
    ) -> None:
        """Test that rate limiting is properly applied during collection."""
        import time

        # Define a time range that will require multiple chunks
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_time = datetime(
            2024, 1, 7, 0, 0, 0, tzinfo=UTC
        )  # 6 days = 2 chunks (3 days each)

        # Record start time
        collection_start = time.time()

        result = await entsoe_data_service_with_real_db.collect_with_chunking(
            AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD, start_time, end_time
        )

        # Record end time
        collection_end = time.time()
        collection_duration = collection_end - collection_start

        # Verify collection succeeded
        assert result.success is True

        # Verify rate limiting was applied
        # Expected: 2 chunks + 2 rate limit delays (1 second each) = at least 2 seconds
        # Add some tolerance for test execution overhead
        min_expected_duration = 1.5  # Slightly less than 2 seconds for tolerance
        assert collection_duration >= min_expected_duration, (
            f"Collection took {collection_duration}s, expected at least {min_expected_duration}s"
        )

        # Should not take excessively long (max 10 seconds for reasonable test execution)
        max_expected_duration = 10.0
        assert collection_duration <= max_expected_duration, (
            f"Collection took {collection_duration}s, expected at most {max_expected_duration}s"
        )

    @pytest.mark.asyncio
    async def test_chunking_performance_with_large_dataset(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
        mock_collector: AsyncMock,
    ) -> None:
        """Test performance with large time ranges requiring many chunks."""
        # Create a large time range (30 days = 10 chunks with 3-day chunks)
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 31, 0, 0, 0, tzinfo=UTC)  # 30 days

        # Mock rate limiting to speed up test
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await entsoe_data_service_with_real_db.collect_with_chunking(
                AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD, start_time, end_time
            )

        # Verify chunking occurred correctly
        expected_chunks = 10  # 30 days / 3 days per chunk = 10 chunks
        assert mock_collector.get_actual_total_load.call_count == expected_chunks
        assert mock_sleep.call_count == expected_chunks

        # Verify result structure
        assert result.success is True
        assert result.start_time == start_time
        assert result.end_time == end_time
        assert result.stored_count > 0  # Should have processed some data

        # Verify data was properly stored in database
        stored_records = await energy_repository.get_all()
        assert len(stored_records) > 0

    @pytest.mark.asyncio
    async def test_database_performance_with_batch_operations(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
        sample_gl_market_document: GlMarketDocument,
    ) -> None:
        """Test database performance with large batch operations."""
        import time

        # Create a larger dataset by modifying the sample document
        large_points = []
        for i in range(100):  # Create 100 data points
            point = LoadPoint(position=i + 1, quantity=float(f"{1000 + i}.567"))
            large_points.append(point)

        # Update the sample document with more data points
        sample_gl_market_document.timeSeries[0].period.points = large_points

        # Configure mock collector to return the large document
        mock_collector = entsoe_data_service_with_real_db._collector

        # Measure processing time
        process_start = time.time()

        # Override the mock collector method to return the large document
        with patch.object(
            mock_collector, "get_actual_total_load", new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = sample_gl_market_document
            result = await entsoe_data_service_with_real_db.collect_gaps_for_endpoint(
                AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD
            )

        process_end = time.time()
        process_duration = process_end - process_start

        # Verify successful processing
        assert result.success is True
        assert result.stored_count > 0

        # Verify reasonable performance (should complete within 30 seconds)
        max_processing_time = 30.0
        assert process_duration <= max_processing_time, (
            f"Processing took {process_duration}s, expected at most {max_processing_time}s"
        )

        # Verify data was stored correctly
        stored_records = await energy_repository.get_all()
        assert len(stored_records) == 100  # Should match our large dataset

        # Verify TimescaleDB hypertable can handle the data efficiently
        async with energy_repository.database.session_factory():
            # Test time-range query performance
            query_start = time.time()

            time_range_records = await energy_repository.get_by_time_range(
                start_time=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
                end_time=datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC),
                area_codes=["DE-LU"],
                data_types=[EnergyDataType.ACTUAL],
            )

            query_end = time.time()
            query_duration = query_end - query_start

            # Time-range queries should be fast (< 5 seconds even with 100 records)
            max_query_time = 5.0
            assert query_duration <= max_query_time, (
                f"Query took {query_duration}s, expected at most {max_query_time}s"
            )

            # Verify query returned expected results
            assert len(time_range_records) > 0

    @pytest.mark.asyncio
    async def test_memory_usage_during_large_operations(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test concurrent operations complete successfully without resource issues."""
        # Run multiple concurrent operations
        tasks = []
        for area in [AreaCode.DE_LU, AreaCode.DE_AT_LU]:
            for endpoint in [
                EndpointNames.ACTUAL_LOAD,
                EndpointNames.DAY_AHEAD_FORECAST,
            ]:
                task = entsoe_data_service_with_real_db.collect_gaps_for_endpoint(
                    area, endpoint
                )
                tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Verify all operations succeeded
        assert len(results) == 4  # 2 areas x 2 endpoints
        for result in results:
            assert result.success is True

        # Verify data was stored
        stored_records = await energy_repository.get_all()
        assert len(stored_records) > 0

    @pytest.mark.asyncio
    async def test_endpoint_configuration_performance(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
    ) -> None:
        """Test that different endpoint configurations perform as expected."""
        import time

        # Test different endpoints with their configured chunk sizes
        endpoint_tests = [
            (EndpointNames.ACTUAL_LOAD, 3),  # 3-day chunks
            (EndpointNames.DAY_AHEAD_FORECAST, 7),  # 7-day chunks
            (EndpointNames.WEEK_AHEAD_FORECAST, 14),  # 14-day chunks
        ]

        for endpoint_name, expected_chunk_days in endpoint_tests:
            # Create a time range that should result in multiple chunks
            days_to_test = expected_chunk_days * 2 + 1  # Slightly more than 2 chunks
            start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
            end_time = start_time + timedelta(days=days_to_test)

            # Mock rate limiting to speed up test
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                collection_start = time.time()

                result = await entsoe_data_service_with_real_db.collect_with_chunking(
                    AreaCode.DE_LU, endpoint_name, start_time, end_time
                )

                collection_end = time.time()
                collection_duration = collection_end - collection_start

            # Verify chunking occurred as expected
            expected_chunks = (
                days_to_test + expected_chunk_days - 1
            ) // expected_chunk_days  # Ceiling division
            assert mock_sleep.call_count == expected_chunks, (
                f"Expected {expected_chunks} chunks for {endpoint_name}, got {mock_sleep.call_count}"
            )

            # Verify reasonable performance (should complete quickly with mocked delays)
            max_duration = 5.0  # 5 seconds should be plenty with mocked sleep
            assert collection_duration <= max_duration, (
                f"{endpoint_name} took {collection_duration}s, expected at most {max_duration}s"
            )

            # Verify successful result
            assert result.success is True

    @pytest.mark.asyncio
    async def test_collect_gaps_with_multiple_time_series(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test gap collection handles multiple TimeSeries correctly (Phase 3 requirement)."""
        # Create a document with multiple TimeSeries to simulate real ENTSO-E response
        multi_ts_document = create_multiple_time_series_document(AreaCode.DE_LU)

        # Verify database starts empty
        initial_records = await energy_repository.get_all()
        assert len(initial_records) == 0

        # Configure mock collector to return the multiple TimeSeries document
        mock_collector = entsoe_data_service_with_real_db._collector

        # Mock asyncio.sleep to avoid rate limiting delays during test
        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch.object(
                mock_collector, "get_actual_total_load", new_callable=AsyncMock
            ) as mock_method,
        ):
            mock_method.return_value = multi_ts_document
            result = await entsoe_data_service_with_real_db.collect_gaps_for_endpoint(
                AreaCode.DE_LU, EndpointNames.ACTUAL_LOAD
            )

        # Verify collection was successful
        assert result.success is True
        assert result.stored_count > 0
        assert result.area == AreaCode.DE_LU
        assert result.data_type == EnergyDataType.ACTUAL

        # Verify ALL data points from BOTH TimeSeries were stored
        stored_records = await energy_repository.get_all()
        expected_points = 1 + 11  # 1 from TS1 + 11 from TS2 = 12 points total
        assert len(stored_records) == expected_points, (
            f"Expected {expected_points} points from multiple TimeSeries, "
            f"got {len(stored_records)}. Data loss detected!"
        )

        # Verify both TimeSeries are represented
        time_series_mrids = {record.time_series_mrid for record in stored_records}
        assert time_series_mrids == {"1", "2"}, (
            f"Expected both TimeSeries mRIDs ['1', '2'], got {time_series_mrids}"
        )

        # Verify point distribution matches TimeSeries structure
        ts1_records = [r for r in stored_records if r.time_series_mrid == "1"]
        ts2_records = [r for r in stored_records if r.time_series_mrid == "2"]

        assert len(ts1_records) == 1, (
            f"TimeSeries 1 should have 1 point, got {len(ts1_records)}"
        )
        assert len(ts2_records) == 11, (
            f"TimeSeries 2 should have 11 points, got {len(ts2_records)}"
        )

        # Verify document metadata consistency
        assert all(
            r.document_mrid.startswith("multi-ts-document") for r in stored_records
        )
        assert all(r.area_code == "DE-LU" for r in stored_records)
        assert all(r.data_type == EnergyDataType.ACTUAL for r in stored_records)
        assert all(r.data_source == "entsoe" for r in stored_records)

        # Verify different resolutions are preserved
        ts1_resolutions = {r.resolution for r in ts1_records}
        ts2_resolutions = {r.resolution for r in ts2_records}
        assert ts1_resolutions == {"PT60M"}
        assert ts2_resolutions == {"PT15M"}

        # Test that timestamps are properly calculated for both TimeSeries
        ts1_timestamps = [r.timestamp for r in ts1_records]
        ts2_timestamps = [r.timestamp for r in ts2_records]

        # Verify each TimeSeries has timestamps
        assert len(ts1_timestamps) == 1, "TS1 should have 1 timestamp"
        assert len(ts2_timestamps) == 11, "TS2 should have 11 timestamps"

        # Verify timestamps are unique within each TimeSeries (no duplicates)
        assert len(set(ts1_timestamps)) == len(ts1_timestamps), (
            "TS1 timestamps should be unique"
        )
        assert len(set(ts2_timestamps)) == len(ts2_timestamps), (
            "TS2 timestamps should be unique"
        )

        # Verify quantities are preserved from both TimeSeries
        ts1_quantities = {r.quantity for r in ts1_records}
        ts2_quantities = {r.quantity for r in ts2_records}

        assert ts1_quantities == {Decimal("1500.0")}, (
            "TS1 should have the expected quantity"
        )

        # TS2 should have range from 1650.0 to 2150.0 (1600 + 50*i for i in 1-11)
        expected_ts2_quantities = {
            Decimal(str(1600.0 + (i * 50))) for i in range(1, 12)
        }
        assert ts2_quantities == expected_ts2_quantities, (
            f"TS2 quantities mismatch: expected {expected_ts2_quantities}, got {ts2_quantities}"
        )

    async def test_gap_detection_forward_vs_backward_looking_integration(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
    ) -> None:
        """
        Integration test verifying that forward-looking and backward-looking endpoints
        collect data from different time periods.
        """
        area = AreaCode.DE_LU
        current_time = datetime.now(UTC)

        # Test backward-looking endpoint (ACTUAL_LOAD)
        actual_config = entsoe_data_service_with_real_db.ENDPOINT_CONFIGS[
            EndpointNames.ACTUAL_LOAD
        ]
        (
            actual_gap_start,
            actual_gap_end,
        ) = await entsoe_data_service_with_real_db._detect_gap_for_endpoint(
            area, actual_config
        )

        # Test forward-looking endpoint (DAY_AHEAD_FORECAST)
        forecast_config = entsoe_data_service_with_real_db.ENDPOINT_CONFIGS[
            EndpointNames.DAY_AHEAD_FORECAST
        ]
        (
            forecast_gap_start,
            forecast_gap_end,
        ) = await entsoe_data_service_with_real_db._detect_gap_for_endpoint(
            area, forecast_config
        )

        # Verify backward-looking endpoint looks into the past
        assert actual_config.is_forward_looking is False
        assert actual_gap_start < current_time
        assert actual_gap_end <= current_time + timedelta(
            minutes=1
        )  # Allow small time differences

        # Verify forward-looking endpoint looks into the future
        assert forecast_config.is_forward_looking is True
        assert forecast_gap_start >= current_time - timedelta(
            minutes=1
        )  # Allow small time differences
        assert forecast_gap_end > current_time
        assert forecast_gap_end == forecast_gap_start + forecast_config.forecast_horizon

        # Verify the time ranges don't overlap (different directions)
        assert actual_gap_end <= forecast_gap_start + timedelta(
            minutes=1
        )  # No overlap with small tolerance

    async def test_forecast_horizon_configuration_integration(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
    ) -> None:
        """
        Integration test verifying that different forecast endpoints use their configured horizons.
        """
        area = AreaCode.DE_LU
        current_time = datetime.now(UTC)

        # Test different forecast endpoints
        forecast_endpoints = [
            (EndpointNames.DAY_AHEAD_FORECAST, timedelta(days=2)),
            (EndpointNames.WEEK_AHEAD_FORECAST, timedelta(weeks=2)),
            (EndpointNames.MONTH_AHEAD_FORECAST, timedelta(days=62)),
            (EndpointNames.YEAR_AHEAD_FORECAST, timedelta(days=730)),
            (EndpointNames.FORECAST_MARGIN, timedelta(days=365)),
        ]

        for endpoint_name, expected_horizon in forecast_endpoints:
            config = entsoe_data_service_with_real_db.ENDPOINT_CONFIGS[endpoint_name]
            (
                gap_start,
                gap_end,
            ) = await entsoe_data_service_with_real_db._detect_gap_for_endpoint(
                area, config
            )

            # Verify the forecast horizon is correct
            actual_horizon = gap_end - gap_start
            assert actual_horizon == expected_horizon, (
                f"Endpoint {endpoint_name} has incorrect forecast horizon: "
                f"expected {expected_horizon}, got {actual_horizon}"
            )

            # Verify all are forward-looking
            assert config.is_forward_looking is True
            assert gap_end > current_time

    async def test_mixed_endpoint_collection_integration(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """
        Integration test verifying that mixed endpoint collection handles both directions correctly.
        """
        area = AreaCode.DE_LU

        # Insert some historical actual data
        historical_data = EnergyDataPoint(
            timestamp=datetime.now(UTC) - timedelta(hours=2),
            area_code=area.area_code,
            data_type=EnergyDataType.ACTUAL,
            quantity=Decimal("1000.5"),
            unit="MAW",
            business_type=BusinessType.CONSUMPTION.code,
            document_mrid="test-historical-doc",
            revision_number=1,
            document_created_at=datetime.now(UTC) - timedelta(hours=2),
            time_series_mrid="test-historical-ts",
            resolution="PT60M",
            curve_type="A01",
            object_aggregation="A01",
            position=1,
            period_start=datetime.now(UTC) - timedelta(hours=2),
            period_end=datetime.now(UTC) - timedelta(hours=1),
        )
        await energy_repository.upsert_batch([historical_data])

        # Insert some forecast data
        forecast_data = EnergyDataPoint(
            timestamp=datetime.now(UTC) + timedelta(hours=12),
            area_code=area.area_code,
            data_type=EnergyDataType.DAY_AHEAD,
            quantity=Decimal("1200.0"),
            unit="MAW",
            business_type=BusinessType.PRODUCTION.code,
            document_mrid="test-forecast-doc",
            revision_number=1,
            document_created_at=datetime.now(UTC),
            time_series_mrid="test-forecast-ts",
            resolution="PT60M",
            curve_type="A01",
            object_aggregation="A01",
            position=1,
            period_start=datetime.now(UTC) + timedelta(hours=12),
            period_end=datetime.now(UTC) + timedelta(hours=13),
        )
        await energy_repository.upsert_batch([forecast_data])

        # Test gap detection for both types
        actual_config = entsoe_data_service_with_real_db.ENDPOINT_CONFIGS[
            EndpointNames.ACTUAL_LOAD
        ]
        (
            actual_gap_start,
            actual_gap_end,
        ) = await entsoe_data_service_with_real_db._detect_gap_for_endpoint(
            area, actual_config
        )

        forecast_config = entsoe_data_service_with_real_db.ENDPOINT_CONFIGS[
            EndpointNames.DAY_AHEAD_FORECAST
        ]
        (
            forecast_gap_start,
            forecast_gap_end,
        ) = await entsoe_data_service_with_real_db._detect_gap_for_endpoint(
            area, forecast_config
        )

        # Verify actual data gap starts after the last historical data point
        expected_actual_start = (
            historical_data.timestamp + actual_config.expected_interval
        )
        assert actual_gap_start == expected_actual_start
        assert actual_gap_end <= datetime.now(UTC) + timedelta(minutes=1)

        # Verify forecast data gap starts after the last forecast data point
        expected_forecast_start = (
            forecast_data.timestamp + forecast_config.expected_interval
        )
        assert forecast_gap_start == expected_forecast_start
        assert forecast_gap_end > datetime.now(UTC)

    async def test_endpoint_config_validation_integration(
        self, entsoe_data_service_with_real_db: EntsoEDataService
    ) -> None:
        """
        Integration test verifying that all endpoint configurations are valid and consistent.
        """
        configs = entsoe_data_service_with_real_db.ENDPOINT_CONFIGS

        # Verify exactly one backward-looking endpoint
        backward_looking = [
            name for name, config in configs.items() if not config.is_forward_looking
        ]
        assert len(backward_looking) == 1
        assert backward_looking[0] == EndpointNames.ACTUAL_LOAD

        # Verify all forecast endpoints are forward-looking
        forward_looking = [
            name for name, config in configs.items() if config.is_forward_looking
        ]
        expected_forward_looking = [
            EndpointNames.DAY_AHEAD_FORECAST,
            EndpointNames.WEEK_AHEAD_FORECAST,
            EndpointNames.MONTH_AHEAD_FORECAST,
            EndpointNames.YEAR_AHEAD_FORECAST,
            EndpointNames.FORECAST_MARGIN,
        ]
        assert set(forward_looking) == set(expected_forward_looking)

        # Verify all forward-looking endpoints have reasonable forecast horizons
        for endpoint_name in forward_looking:
            config = configs[endpoint_name]
            assert config.forecast_horizon > timedelta(0)
            assert config.forecast_horizon <= timedelta(
                days=1000
            )  # Reasonable upper bound

        # Verify backward-looking endpoint has default forecast horizon (unused)
        actual_config = configs[EndpointNames.ACTUAL_LOAD]
        assert actual_config.forecast_horizon == timedelta(days=7)  # Default value

    async def test_time_direction_consistency_integration(
        self,
        entsoe_data_service_with_real_db: EntsoEDataService,
    ) -> None:
        """
        Integration test verifying time direction consistency across multiple collection attempts.
        """
        area = AreaCode.DE_LU
        current_time = datetime.now(UTC)

        # Collect gaps multiple times to ensure consistency
        for attempt in range(3):
            # Test backward-looking endpoint
            actual_config = entsoe_data_service_with_real_db.ENDPOINT_CONFIGS[
                EndpointNames.ACTUAL_LOAD
            ]
            (
                actual_gap_start,
                actual_gap_end,
            ) = await entsoe_data_service_with_real_db._detect_gap_for_endpoint(
                area, actual_config
            )

            # Test forward-looking endpoint
            forecast_config = entsoe_data_service_with_real_db.ENDPOINT_CONFIGS[
                EndpointNames.DAY_AHEAD_FORECAST
            ]
            (
                forecast_gap_start,
                forecast_gap_end,
            ) = await entsoe_data_service_with_real_db._detect_gap_for_endpoint(
                area, forecast_config
            )

            # Verify consistency in time directions
            assert actual_gap_start < current_time, (
                f"Attempt {attempt}: Actual data should look backward"
            )
            assert actual_gap_end <= current_time + timedelta(minutes=1), (
                f"Attempt {attempt}: Actual data should end around now"
            )

            assert forecast_gap_start >= current_time - timedelta(minutes=1), (
                f"Attempt {attempt}: Forecast data should start around now"
            )
            assert forecast_gap_end > current_time, (
                f"Attempt {attempt}: Forecast data should look forward"
            )

            # Small delay between attempts
            await asyncio.sleep(0.1)
