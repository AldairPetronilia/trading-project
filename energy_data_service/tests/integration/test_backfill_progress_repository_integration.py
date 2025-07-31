"""Integration tests for BackfillProgressRepository using testcontainers.

This test suite verifies that the BackfillProgressRepository properly
resolves technical debt and works correctly with a real database.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

import pytest
import pytest_asyncio
from app.config.database import Database
from app.config.settings import DatabaseConfig, EntsoEClientConfig, Settings
from app.container import Container
from app.models.backfill_progress import BackfillProgress, BackfillStatus
from app.models.base import Base
from app.repositories.backfill_progress_repository import BackfillProgressRepository
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer


@pytest.fixture(autouse=True)
def reset_container_state() -> Generator:
    """Reset container state before and after each test for proper isolation."""
    yield
    try:
        if hasattr(Container, "_singletons"):
            Container._singletons.clear()
    except AttributeError:
        pass


@pytest.fixture
def postgres_container() -> Generator[PostgresContainer]:
    """Fixture that provides a PostgreSQL testcontainer with TimescaleDB."""
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
    """Create Settings with test database configuration."""
    return Settings(
        database=database_config,
        entsoe_client=EntsoEClientConfig(api_token="test_token_1234567890"),
        debug=True,
    )


@pytest_asyncio.fixture
async def database(settings: Settings) -> AsyncGenerator[Database]:
    """Create Database instance and initialize schema."""
    db = Database(settings)

    # Create tables
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield db

    # Cleanup
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await db.engine.dispose()


@pytest_asyncio.fixture
async def repository(database: Database) -> BackfillProgressRepository:
    """Create BackfillProgressRepository instance."""
    return BackfillProgressRepository(database)


@pytest.fixture
def sample_progress() -> BackfillProgress:
    """Create sample BackfillProgress instance."""
    return BackfillProgress(
        area_code="DE",
        endpoint_name="actual_load",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 2, tzinfo=UTC),
        status=BackfillStatus.PENDING,
        progress_percentage=Decimal("0.00"),
        completed_chunks=0,
        total_chunks=10,
        total_data_points=0,
        failed_chunks=0,
        chunk_size_days=1,
        rate_limit_delay=Decimal("1.00"),
    )


class TestBackfillProgressRepositoryIntegration:
    """Integration tests for BackfillProgressRepository with real database."""

    @pytest.mark.asyncio
    async def test_create_and_get_by_id(
        self, repository: BackfillProgressRepository, sample_progress: BackfillProgress
    ) -> None:
        """Test creating and retrieving backfill progress."""
        # Create
        created_progress = await repository.create(sample_progress)
        assert created_progress.id is not None
        assert created_progress.area_code == "DE"
        assert created_progress.endpoint_name == "actual_load"

        # Retrieve
        retrieved_progress = await repository.get_by_id(created_progress.id)
        assert retrieved_progress is not None
        assert retrieved_progress.id == created_progress.id
        assert retrieved_progress.area_code == "DE"
        assert retrieved_progress.endpoint_name == "actual_load"

    @pytest.mark.asyncio
    async def test_update_progress_without_session_merge(
        self, repository: BackfillProgressRepository, sample_progress: BackfillProgress
    ) -> None:
        """Test that updates work without session.merge() - resolves technical debt."""
        # Create initial progress
        created_progress = await repository.create(sample_progress)
        progress_id = created_progress.id

        # Update using the new method that eliminates session.merge()
        updated_progress = await repository.update_progress_by_id(
            progress_id,
            completed_chunks=5,
            progress_percentage=Decimal("50.00"),
            status=BackfillStatus.IN_PROGRESS,
        )

        assert updated_progress is not None
        assert updated_progress.id == progress_id
        assert updated_progress.completed_chunks == 5
        assert updated_progress.progress_percentage == Decimal("50.00")
        assert updated_progress.status == BackfillStatus.IN_PROGRESS

        # Verify persistence by retrieving again
        retrieved_progress = await repository.get_by_id(progress_id)
        assert retrieved_progress is not None
        assert retrieved_progress.completed_chunks == 5
        assert retrieved_progress.progress_percentage == Decimal("50.00")
        assert retrieved_progress.status == BackfillStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_get_active_backfills(
        self, repository: BackfillProgressRepository, sample_progress: BackfillProgress
    ) -> None:
        """Test retrieving active backfill operations."""
        # Create multiple progress records with different statuses
        pending_progress = sample_progress
        await repository.create(pending_progress)

        in_progress_progress = BackfillProgress(
            area_code="FR",
            endpoint_name="actual_load",
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 2, tzinfo=UTC),
            status=BackfillStatus.IN_PROGRESS,
            progress_percentage=Decimal("25.00"),
            completed_chunks=2,
            total_chunks=8,
            total_data_points=500,
            failed_chunks=0,
            chunk_size_days=1,
            rate_limit_delay=Decimal("1.00"),
        )
        await repository.create(in_progress_progress)

        completed_progress = BackfillProgress(
            area_code="ES",
            endpoint_name="actual_load",
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 2, tzinfo=UTC),
            status=BackfillStatus.COMPLETED,
            progress_percentage=Decimal("100.00"),
            completed_chunks=8,
            total_chunks=8,
            total_data_points=2000,
            failed_chunks=0,
            chunk_size_days=1,
            rate_limit_delay=Decimal("1.00"),
        )
        await repository.create(completed_progress)

        # Get active backfills (should return PENDING and IN_PROGRESS only)
        active_backfills = await repository.get_active_backfills()

        assert len(active_backfills) == 2
        statuses = {progress.status for progress in active_backfills}
        assert statuses == {BackfillStatus.PENDING, BackfillStatus.IN_PROGRESS}

    @pytest.mark.asyncio
    async def test_get_resumable_backfills(
        self, repository: BackfillProgressRepository
    ) -> None:
        """Test retrieving resumable backfill operations."""
        # Create failed progress with some completed chunks (resumable)
        resumable_progress = BackfillProgress(
            area_code="IT",
            endpoint_name="actual_load",
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 2, tzinfo=UTC),
            status=BackfillStatus.FAILED,
            progress_percentage=Decimal("40.00"),
            completed_chunks=4,
            total_chunks=10,
            total_data_points=1000,
            failed_chunks=1,
            chunk_size_days=1,
            rate_limit_delay=Decimal("1.00"),
        )
        await repository.create(resumable_progress)

        # Create failed progress with no completed chunks (not resumable)
        non_resumable_progress = BackfillProgress(
            area_code="NL",
            endpoint_name="actual_load",
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 2, tzinfo=UTC),
            status=BackfillStatus.FAILED,
            progress_percentage=Decimal("0.00"),
            completed_chunks=0,
            total_chunks=10,
            total_data_points=0,
            failed_chunks=0,
            chunk_size_days=1,
            rate_limit_delay=Decimal("1.00"),
        )
        await repository.create(non_resumable_progress)

        # Get resumable backfills
        resumable_backfills = await repository.get_resumable_backfills()

        assert len(resumable_backfills) == 1
        assert resumable_backfills[0].area_code == "IT"
        assert resumable_backfills[0].completed_chunks > 0
        assert resumable_backfills[0].status == BackfillStatus.FAILED

    @pytest.mark.asyncio
    async def test_get_by_area_endpoint(
        self, repository: BackfillProgressRepository, sample_progress: BackfillProgress
    ) -> None:
        """Test retrieving backfills by area code and endpoint name."""
        # Create progress for DE/actual_load
        await repository.create(sample_progress)

        # Create progress for FR/actual_load
        fr_progress = BackfillProgress(
            area_code="FR",
            endpoint_name="actual_load",
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 2, tzinfo=UTC),
            status=BackfillStatus.PENDING,
            progress_percentage=Decimal("0.00"),
            completed_chunks=0,
            total_chunks=10,
            total_data_points=0,
            failed_chunks=0,
            chunk_size_days=1,
            rate_limit_delay=Decimal("1.00"),
        )
        await repository.create(fr_progress)

        # Create progress for DE/day_ahead_forecast
        de_forecast_progress = BackfillProgress(
            area_code="DE",
            endpoint_name="day_ahead_forecast",
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 2, tzinfo=UTC),
            status=BackfillStatus.PENDING,
            progress_percentage=Decimal("0.00"),
            completed_chunks=0,
            total_chunks=10,
            total_data_points=0,
            failed_chunks=0,
            chunk_size_days=1,
            rate_limit_delay=Decimal("1.00"),
        )
        await repository.create(de_forecast_progress)

        # Get backfills for DE/actual_load
        de_actual_backfills = await repository.get_by_area_endpoint("DE", "actual_load")

        assert len(de_actual_backfills) == 1
        assert de_actual_backfills[0].area_code == "DE"
        assert de_actual_backfills[0].endpoint_name == "actual_load"

    @pytest.mark.asyncio
    async def test_concurrent_operations_no_session_conflicts(
        self, repository: BackfillProgressRepository
    ) -> None:
        """Test that concurrent repository operations don't have session conflicts."""
        # Create multiple progress records concurrently
        progress_records = [
            BackfillProgress(
                area_code=f"T{i}",
                endpoint_name="actual_load",
                period_start=datetime(2024, 1, 1, tzinfo=UTC),
                period_end=datetime(2024, 1, 2, tzinfo=UTC),
                status=BackfillStatus.PENDING,
                progress_percentage=Decimal("0.00"),
                completed_chunks=0,
                total_chunks=10,
                total_data_points=0,
                failed_chunks=0,
                chunk_size_days=1,
                rate_limit_delay=Decimal("1.00"),
            )
            for i in range(5)
        ]

        # Create all records concurrently
        created_records = await asyncio.gather(
            *[repository.create(progress) for progress in progress_records]
        )

        # Verify all were created successfully
        assert len(created_records) == 5
        for record in created_records:
            assert record.id is not None

        # Retrieve all records concurrently
        retrieved_records_raw: list[BackfillProgress | None] = await asyncio.gather(
            *[repository.get_by_id(record.id) for record in created_records]
        )

        # Filter out None values to create properly typed list
        valid_records: list[BackfillProgress] = [
            record for record in retrieved_records_raw if record is not None
        ]

        # Verify all were retrieved successfully
        assert len(valid_records) == 5
        for record in valid_records:
            assert isinstance(record, BackfillProgress)

    @pytest.mark.asyncio
    async def test_repository_with_container_integration(
        self, database_config: DatabaseConfig
    ) -> None:
        """Test that repository works properly when created through container."""
        # Create settings and container
        settings = Settings(
            database=database_config,
            entsoe_client=EntsoEClientConfig(api_token="test_token_1234567890"),
            debug=True,
        )

        container = Container()
        container.config.override(settings)

        # Get repository through container
        repository = container.backfill_progress_repository()
        database = container.database()

        # Initialize schema
        async with database.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        try:
            # Test basic operations
            progress = BackfillProgress(
                area_code="CN",
                endpoint_name="actual_load",
                period_start=datetime(2024, 1, 1, tzinfo=UTC),
                period_end=datetime(2024, 1, 2, tzinfo=UTC),
                status=BackfillStatus.PENDING,
                progress_percentage=Decimal("0.00"),
                completed_chunks=0,
                total_chunks=10,
                total_data_points=0,
                failed_chunks=0,
                chunk_size_days=1,
                rate_limit_delay=Decimal("1.00"),
            )

            created_progress = await repository.create(progress)
            assert created_progress.id is not None

            retrieved_progress = await repository.get_by_id(created_progress.id)
            assert retrieved_progress is not None
            assert retrieved_progress.area_code == "CN"

        finally:
            # Cleanup
            async with database.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

            await database.engine.dispose()
