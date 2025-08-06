"""Integration tests for health check endpoints using testcontainers."""

from collections.abc import Generator

import pytest
from app.api.app import create_app
from app.api.v1.endpoints.health import DetailedHealthResponse
from app.config.database import Database
from app.config.settings import DatabaseConfig, EntsoEClientConfig, Settings
from app.container import Container
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
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
def app_with_test_db(settings: Settings) -> FastAPI:
    """Create FastAPI app with test database configuration."""
    app = create_app()
    # Override the container's settings
    container = Container()
    container.config.override(settings)
    app.state.container = container
    return app


class TestHealthEndpointsIntegration:
    """Integration tests for health check endpoints with real database."""

    def test_detailed_health_check_with_database(
        self, app_with_test_db: FastAPI
    ) -> None:
        """Test detailed health check with real test database."""
        client = TestClient(app_with_test_db)
        response = client.get("/api/v1/health/detailed")

        assert response.status_code == 200
        data = response.json()

        # Healthy response
        assert data["status"] == "healthy"
        assert data["database"] == "healthy"
        assert "components" in data
        assert "energy_data_repository" in data["components"]
        assert data["components"]["energy_data_repository"] == "healthy"
        assert "dependency_container" in data["components"]
        assert data["components"]["dependency_container"] == "healthy"

    def test_detailed_health_check_response_schema_with_database(
        self, app_with_test_db: FastAPI
    ) -> None:
        """Test that detailed health response matches expected schema with real database."""
        client = TestClient(app_with_test_db)
        response = client.get("/api/v1/health/detailed")

        assert response.status_code == 200
        data = response.json()

        # Should be able to parse as DetailedHealthResponse
        detailed_response = DetailedHealthResponse(**data)
        assert detailed_response.status == "healthy"
        assert detailed_response.database == "healthy"
        assert isinstance(detailed_response.components, dict)

    def test_health_endpoints_return_json_content_type_with_database(
        self, app_with_test_db: FastAPI
    ) -> None:
        """Test that health endpoints return proper JSON content type with real database."""
        client = TestClient(app_with_test_db)

        # Test basic health endpoint
        response = client.get("/api/v1/health/")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        # Test detailed health endpoint with database
        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "healthy"

    def test_health_endpoints_available_through_router_with_database(
        self, app_with_test_db: FastAPI
    ) -> None:
        """Test that all health endpoints are properly registered and accessible."""
        client = TestClient(app_with_test_db)

        # Test basic health endpoint
        response = client.get("/api/v1/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

        # Test detailed health endpoint with database
        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "healthy"
