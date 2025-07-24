"""Integration tests for repository layer using testcontainers."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from app.config.database import Database
from app.config.settings import DatabaseConfig, EntsoEClientConfig, Settings
from app.container import Container
from app.models.base import Base
from app.models.load_data import EnergyDataPoint, EnergyDataType
from app.repositories.energy_data_repository import EnergyDataRepository
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer


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
    """Fixture that provides a PostgreSQL testcontainer with TimescaleDB."""
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
    from pydantic import SecretStr

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


@pytest.fixture
def sample_energy_data() -> list[EnergyDataPoint]:
    """Create sample energy data points for testing."""
    base_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

    return [
        EnergyDataPoint(
            timestamp=base_time,
            area_code="DE",
            data_type=EnergyDataType.ACTUAL,
            business_type="A65",
            quantity=Decimal("1234.567"),
            unit="MAW",
            data_source="entsoe",
            document_mrid="test-doc-1",
            revision_number=1,
            document_created_at=base_time,
            time_series_mrid="test-ts-1",
            resolution="PT60M",
            curve_type="A01",
            object_aggregation="A01",
            position=1,
            period_start=base_time,
            period_end=datetime(2024, 1, 15, 13, 0, 0, tzinfo=UTC),
        ),
        EnergyDataPoint(
            timestamp=datetime(2024, 1, 15, 13, 0, 0, tzinfo=UTC),
            area_code="DE",
            data_type=EnergyDataType.ACTUAL,
            business_type="A65",
            quantity=Decimal("1345.678"),
            unit="MAW",
            data_source="entsoe",
            document_mrid="test-doc-1",
            revision_number=1,
            document_created_at=base_time,
            time_series_mrid="test-ts-1",
            resolution="PT60M",
            curve_type="A01",
            object_aggregation="A01",
            position=2,
            period_start=datetime(2024, 1, 15, 13, 0, 0, tzinfo=UTC),
            period_end=datetime(2024, 1, 15, 14, 0, 0, tzinfo=UTC),
        ),
        EnergyDataPoint(
            timestamp=base_time,
            area_code="FR",
            data_type=EnergyDataType.DAY_AHEAD,
            business_type="A65",
            quantity=Decimal("2234.567"),
            unit="MAW",
            data_source="entsoe",
            document_mrid="test-doc-2",
            revision_number=1,
            document_created_at=base_time,
            time_series_mrid="test-ts-2",
            resolution="PT60M",
            curve_type="A01",
            object_aggregation="A01",
            position=1,
            period_start=base_time,
            period_end=datetime(2024, 1, 15, 13, 0, 0, tzinfo=UTC),
        ),
    ]


class TestRepositoryIntegration:
    """Integration tests for repository layer with real database."""

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

            # Check that energy_data_points table exists
            result = await session.execute(
                text(
                    """
                SELECT table_name FROM information_schema.tables
                WHERE table_name = 'energy_data_points';
            """,
                ),
            )
            table = result.fetchone()
            assert table is not None
            assert table.table_name == "energy_data_points"

            # Check that hypertable was created
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
    async def test_create_and_get_energy_data_point(
        self,
        energy_repository: EnergyDataRepository,
        sample_energy_data: list[EnergyDataPoint],
    ) -> None:
        """Test creating and retrieving a single energy data point."""
        data_point = sample_energy_data[0]

        # Create the data point
        created = await energy_repository.create(data_point)
        assert created.timestamp == data_point.timestamp
        assert created.area_code == data_point.area_code
        assert created.quantity == data_point.quantity

        # Retrieve by composite key
        retrieved = await energy_repository.get_by_composite_key(
            timestamp=data_point.timestamp,
            area_code=data_point.area_code,
            data_type=data_point.data_type,
            business_type=data_point.business_type,
        )
        assert retrieved is not None
        assert retrieved.timestamp == data_point.timestamp
        assert retrieved.quantity == data_point.quantity

    @pytest.mark.asyncio
    async def test_batch_upsert_operations(
        self,
        energy_repository: EnergyDataRepository,
        sample_energy_data: list[EnergyDataPoint],
    ) -> None:
        """Test batch upsert operations with conflict resolution."""
        # Initial batch insert
        upserted = await energy_repository.upsert_batch(sample_energy_data)
        assert len(upserted) == len(sample_energy_data)

        # Verify all records were inserted
        all_records = await energy_repository.get_all()
        assert len(all_records) == len(sample_energy_data)

        # Update quantities and upsert again
        for data_point in sample_energy_data:
            data_point.quantity = data_point.quantity + Decimal("100.0")

        updated = await energy_repository.upsert_batch(sample_energy_data)
        assert len(updated) == len(sample_energy_data)

        # Verify quantities were updated, not duplicated
        all_records_after_update = await energy_repository.get_all()
        assert len(all_records_after_update) == len(sample_energy_data)

        # Check that quantities were actually updated
        for record in all_records_after_update:
            original_data = next(
                dp
                for dp in sample_energy_data
                if (
                    dp.timestamp == record.timestamp
                    and dp.area_code == record.area_code
                    and dp.data_type == record.data_type
                    and dp.business_type == record.business_type
                )
            )
            assert record.quantity == original_data.quantity

    @pytest.mark.asyncio
    async def test_time_range_queries(
        self,
        energy_repository: EnergyDataRepository,
        sample_energy_data: list[EnergyDataPoint],
    ) -> None:
        """Test time-range queries with various filters."""
        # Insert test data
        await energy_repository.upsert_batch(sample_energy_data)

        # Test basic time range query
        start_time = datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, 15, 14, 0, 0, tzinfo=UTC)

        results = await energy_repository.get_by_time_range(start_time, end_time)
        assert len(results) == 3  # All sample data should be in range

        # Test time range with area filter
        de_results = await energy_repository.get_by_time_range(
            start_time,
            end_time,
            area_codes=["DE"],
        )
        assert len(de_results) == 2  # Only DE records
        assert all(r.area_code == "DE" for r in de_results)

        # Test time range with data type filter
        actual_results = await energy_repository.get_by_time_range(
            start_time,
            end_time,
            data_types=[EnergyDataType.ACTUAL],
        )
        assert len(actual_results) == 2  # Only ACTUAL records
        assert all(r.data_type == EnergyDataType.ACTUAL for r in actual_results)

        # Test combined filters
        de_actual_results = await energy_repository.get_by_time_range(
            start_time,
            end_time,
            area_codes=["DE"],
            data_types=[EnergyDataType.ACTUAL],
        )
        assert len(de_actual_results) == 2  # DE + ACTUAL records
        assert all(
            r.area_code == "DE" and r.data_type == EnergyDataType.ACTUAL
            for r in de_actual_results
        )

    @pytest.mark.asyncio
    async def test_area_specific_queries(
        self,
        energy_repository: EnergyDataRepository,
        sample_energy_data: list[EnergyDataPoint],
    ) -> None:
        """Test area-specific query methods."""
        # Insert test data
        await energy_repository.upsert_batch(sample_energy_data)

        # Test get_by_area
        de_results = await energy_repository.get_by_area("DE")
        assert len(de_results) == 2
        assert all(r.area_code == "DE" for r in de_results)
        # Results should be ordered by timestamp desc
        assert de_results[0].timestamp >= de_results[1].timestamp

        # Test get_by_area with data type filter
        de_actual_results = await energy_repository.get_by_area(
            "DE",
            data_type=EnergyDataType.ACTUAL,
        )
        assert len(de_actual_results) == 2
        assert all(
            r.area_code == "DE" and r.data_type == EnergyDataType.ACTUAL
            for r in de_actual_results
        )

        # Test get_by_area with limit
        limited_results = await energy_repository.get_by_area("DE", limit=1)
        assert len(limited_results) == 1

        # Test get_latest_for_area
        latest = await energy_repository.get_latest_for_area(
            "DE",
            EnergyDataType.ACTUAL,
            "A65",
        )
        assert latest is not None
        assert latest.area_code == "DE"
        assert latest.data_type == EnergyDataType.ACTUAL
        # Should be the latest timestamp for DE ACTUAL A65
        expected_latest = datetime(2024, 1, 15, 13, 0, 0, tzinfo=UTC)
        assert latest.timestamp == expected_latest

    @pytest.mark.asyncio
    async def test_delete_operations(
        self,
        energy_repository: EnergyDataRepository,
        sample_energy_data: list[EnergyDataPoint],
    ) -> None:
        """Test delete operations with composite keys."""
        # Insert test data
        await energy_repository.upsert_batch(sample_energy_data)

        # Verify initial count
        all_records = await energy_repository.get_all()
        assert len(all_records) == 3

        # Delete by composite key
        data_point = sample_energy_data[0]
        deleted = await energy_repository.delete_by_composite_key(
            timestamp=data_point.timestamp,
            area_code=data_point.area_code,
            data_type=data_point.data_type,
            business_type=data_point.business_type,
        )
        assert deleted is True

        # Verify record was deleted
        remaining_records = await energy_repository.get_all()
        assert len(remaining_records) == 2

        # Try to delete non-existent record
        non_existent_deleted = await energy_repository.delete_by_composite_key(
            timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
            area_code="XX",
            data_type=EnergyDataType.ACTUAL,
            business_type="A99",
        )
        assert non_existent_deleted is False

        # Verify count unchanged
        final_records = await energy_repository.get_all()
        assert len(final_records) == 2

    @pytest.mark.asyncio
    async def test_concurrent_operations(
        self,
        energy_repository: EnergyDataRepository,
        sample_energy_data: list[EnergyDataPoint],
    ) -> None:
        """Test concurrent repository operations."""

        async def insert_batch(batch_id: int) -> int:
            """Insert a batch of data with unique identifiers."""
            # Create unique data points for this batch
            batch_data = []
            for i, data_point in enumerate(sample_energy_data):
                new_data = EnergyDataPoint(
                    timestamp=datetime(
                        2024,
                        1,
                        15,
                        12 + batch_id,
                        i,
                        0,
                        tzinfo=UTC,
                    ),
                    area_code=f"T{batch_id}",  # Unique area codes per batch
                    data_type=data_point.data_type,
                    business_type=data_point.business_type,
                    quantity=data_point.quantity + Decimal(str(batch_id * 100)),
                    unit=data_point.unit,
                    data_source=data_point.data_source,
                    document_mrid=f"test-doc-{batch_id}-{i}",
                    revision_number=data_point.revision_number,
                    document_created_at=data_point.document_created_at,
                    time_series_mrid=f"test-ts-{batch_id}-{i}",
                    resolution=data_point.resolution,
                    curve_type=data_point.curve_type,
                    object_aggregation=data_point.object_aggregation,
                    position=data_point.position,
                    period_start=data_point.period_start,
                    period_end=data_point.period_end,
                )
                batch_data.append(new_data)

            await energy_repository.upsert_batch(batch_data)
            return batch_id

        # Run multiple concurrent inserts
        tasks = [insert_batch(i) for i in range(3)]
        results = await asyncio.gather(*tasks)

        assert results == [0, 1, 2]

        # Verify all data was inserted
        all_records = await energy_repository.get_all()
        assert len(all_records) == 9  # 3 batches * 3 records each

        # Verify unique area codes were maintained
        area_codes = {record.area_code for record in all_records}
        assert area_codes == {"T0", "T1", "T2"}

    @pytest.mark.asyncio
    async def test_repository_exception_handling(
        self,
        energy_repository: EnergyDataRepository,
    ) -> None:
        """Test repository exception handling with database constraints."""
        # Test invalid composite key format
        with pytest.raises(ValueError, match="must be a tuple"):
            await energy_repository.get_by_id("invalid-key")

        with pytest.raises(ValueError, match="must be a tuple"):
            await energy_repository.get_by_id((1, 2))  # Wrong length

        with pytest.raises(ValueError, match="must be a tuple"):
            await energy_repository.delete("invalid-key")
