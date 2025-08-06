"""Integration tests for energy data API endpoints."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from app.api.app import create_app
from app.config.settings import DatabaseConfig, EntsoEClientConfig, Settings
from app.container import Container
from app.models.load_data import EnergyDataPoint
from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from testcontainers.postgres import PostgresContainer


@pytest.fixture
def postgres_container() -> Generator[PostgresContainer]:
    """Fixture that provides a PostgreSQL testcontainer."""
    with PostgresContainer("postgres:16") as postgres:
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
        entsoe_client=EntsoEClientConfig(api_token=SecretStr("test_token_1234567890")),
    )


@pytest.fixture
def container(settings: Settings) -> Generator[Container]:
    """Create a test container with test database."""
    container = Container()
    container.config.override(settings)
    container.init_resources()

    # Create tables
    from app.config.database import Database

    database = container.database()
    database.create_all_tables()

    yield container
    container.shutdown_resources()


class TestEnergyDataAPIIntegration:
    """Integration tests for energy data API with real database."""

    @pytest_asyncio.fixture
    async def app_client(self, container: Container) -> AsyncGenerator[AsyncClient]:
        """Create test client with real app and database."""
        app = create_app()
        app.container = container

        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    @pytest_asyncio.fixture
    async def sample_data(self, container: Container) -> list[EnergyDataPoint]:
        """Create sample energy data in the database."""
        db_session_factory = container.db_session_factory()
        async with db_session_factory() as session:
            data_points = []
            base_time = datetime(2024, 1, 1, tzinfo=UTC)

            # Create data for multiple areas and types
            areas = ["DE", "FR", "NL"]
            data_types = ["A75", "A74"]
            business_types = ["A01", "A02"]

            for area in areas:
                for hour in range(24):
                    for data_type in data_types:
                        for business_type in business_types:
                            point = EnergyDataPoint(
                                timestamp=base_time + timedelta(hours=hour),
                                area_code=area,
                                data_type=data_type,
                                business_type=business_type,
                                quantity=Decimal(f"{1000 + hour * 10}.50"),
                                unit="MW",
                                data_source="ENTSOE",
                                resolution="PT60M",
                                curve_type="A01",
                                document_mrid=f"doc-{area}-{hour}-{data_type}",
                                revision_number=1,
                                document_created_at=base_time,
                                time_series_mrid=f"ts-{area}-{data_type}",
                                object_aggregation="A01",
                                position=hour + 1,
                                period_start=base_time,
                                period_end=base_time + timedelta(days=1),
                            )
                            session.add(point)
                            data_points.append(point)

            await session.commit()
            return data_points

    async def test_get_energy_data_basic(
        self,
        app_client: AsyncClient,
        sample_data: list[EnergyDataPoint],  # noqa: ARG002
    ) -> None:
        """Test basic energy data retrieval."""
        response = await app_client.get(
            "/api/v1/energy-data/",
            params={
                "area_code": "DE",
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T12:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should have data for 12 hours * 2 data types * 2 business types
        assert len(data) > 0
        assert all(item["area_code"] == "DE" for item in data)

        # Verify timestamp range
        timestamps = [datetime.fromisoformat(item["timestamp"]) for item in data]
        assert min(timestamps) >= datetime(2024, 1, 1, tzinfo=UTC)
        assert max(timestamps) <= datetime(2024, 1, 1, 12, tzinfo=UTC)

    async def test_get_energy_data_with_filters(
        self,
        app_client: AsyncClient,
        sample_data: list[EnergyDataPoint],  # noqa: ARG002
    ) -> None:
        """Test energy data retrieval with data type and business type filters."""
        response = await app_client.get(
            "/api/v1/energy-data/",
            params={
                "area_code": "FR",
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T06:00:00Z",
                "data_type": "A75",
                "business_type": "A01",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all results match filters
        assert all(item["area_code"] == "FR" for item in data)
        assert all(item["data_type"] == "A75" for item in data)
        assert all(item["business_type"] == "A01" for item in data)

    async def test_get_energy_data_with_limit(
        self,
        app_client: AsyncClient,
        sample_data: list[EnergyDataPoint],  # noqa: ARG002
    ) -> None:
        """Test energy data retrieval with limit parameter."""
        response = await app_client.get(
            "/api/v1/energy-data/",
            params={
                "area_code": "NL",
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-02T00:00:00Z",
                "limit": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10

    async def test_get_energy_data_empty_result(
        self,
        app_client: AsyncClient,
        sample_data: list[EnergyDataPoint],  # noqa: ARG002
    ) -> None:
        """Test energy data retrieval with no matching data."""
        response = await app_client.get(
            "/api/v1/energy-data/",
            params={
                "area_code": "ES",  # No data for Spain
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-02T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []

    async def test_get_energy_data_invalid_time_range(
        self, app_client: AsyncClient
    ) -> None:
        """Test that invalid time range returns 400 error."""
        response = await app_client.get(
            "/api/v1/energy-data/",
            params={
                "area_code": "DE",
                "start_time": "2024-01-02T00:00:00Z",
                "end_time": "2024-01-01T00:00:00Z",  # End before start
            },
        )

        assert response.status_code == 400
        assert "end_time must be after start_time" in response.json()["detail"]

    async def test_get_energy_data_missing_params(
        self, app_client: AsyncClient
    ) -> None:
        """Test that missing required parameters returns 422 error."""
        response = await app_client.get("/api/v1/energy-data/")

        assert response.status_code == 422
        error_detail = response.json()["detail"]

        # Check that all required fields are reported as missing
        missing_fields = {error["loc"][-1] for error in error_detail}
        assert "area_code" in missing_fields
        assert "start_time" in missing_fields
        assert "end_time" in missing_fields

    async def test_get_energy_data_invalid_limit(self, app_client: AsyncClient) -> None:
        """Test that invalid limit values return 422 error."""
        # Test limit too high
        response = await app_client.get(
            "/api/v1/energy-data/",
            params={
                "area_code": "DE",
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-02T00:00:00Z",
                "limit": 10001,  # Above maximum
            },
        )

        assert response.status_code == 422

        # Test limit too low
        response = await app_client.get(
            "/api/v1/energy-data/",
            params={
                "area_code": "DE",
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-02T00:00:00Z",
                "limit": 0,  # Below minimum
            },
        )

        assert response.status_code == 422

    async def test_get_energy_data_case_insensitive_area(
        self,
        app_client: AsyncClient,
        sample_data: list[EnergyDataPoint],  # noqa: ARG002
    ) -> None:
        """Test that area codes are case-insensitive."""
        # Test with lowercase
        response_lower = await app_client.get(
            "/api/v1/energy-data/",
            params={
                "area_code": "de",
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T01:00:00Z",
            },
        )

        # Test with uppercase
        response_upper = await app_client.get(
            "/api/v1/energy-data/",
            params={
                "area_code": "DE",
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T01:00:00Z",
            },
        )

        assert response_lower.status_code == 200
        assert response_upper.status_code == 200
        assert len(response_lower.json()) == len(response_upper.json())

    async def test_get_energy_data_response_format(
        self,
        app_client: AsyncClient,
        sample_data: list[EnergyDataPoint],  # noqa: ARG002
    ) -> None:
        """Test that response format matches schema."""
        response = await app_client.get(
            "/api/v1/energy-data/",
            params={
                "area_code": "DE",
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T01:00:00Z",
                "limit": 1,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

        # Verify response structure
        item = data[0]
        required_fields = {
            "timestamp",
            "area_code",
            "data_type",
            "business_type",
            "quantity",
            "unit",
            "data_source",
        }
        assert all(field in item for field in required_fields)

        # Verify data types
        assert isinstance(item["timestamp"], str)
        assert isinstance(item["quantity"], int | float)
        assert isinstance(item["unit"], str)

    async def test_get_energy_data_concurrent_requests(
        self,
        app_client: AsyncClient,
        sample_data: list[EnergyDataPoint],  # noqa: ARG002
    ) -> None:
        """Test handling of concurrent requests."""
        # Create multiple concurrent requests
        tasks = []
        for area in ["DE", "FR", "NL"]:
            task = app_client.get(
                "/api/v1/energy-data/",
                params={
                    "area_code": area,
                    "start_time": "2024-01-01T00:00:00Z",
                    "end_time": "2024-01-01T06:00:00Z",
                },
            )
            tasks.append(task)

        # Execute concurrently
        responses = await asyncio.gather(*tasks)

        # Verify all succeeded
        for response in responses:
            assert response.status_code == 200
            assert len(response.json()) > 0
