"""Unit tests for health check endpoints."""

from unittest.mock import AsyncMock, Mock

import pytest
from app.api.app import create_app
from app.api.v1.endpoints.health import DetailedHealthResponse, HealthResponse
from app.exceptions.repository_exceptions import DataAccessError
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Unit test cases for basic health check endpoint."""

    def test_health_check_success(self) -> None:
        """Test that basic health check returns healthy status."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/api/v1/health/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["message"] == "Energy Data Service API is operational"

    def test_health_check_response_schema(self) -> None:
        """Test that health check response matches expected schema."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/api/v1/health/")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "status" in data
        assert "message" in data
        assert len(data.keys()) == 2

        # Validate response can be parsed as HealthResponse
        health_response = HealthResponse(**data)
        assert health_response.status == "healthy"

    def test_health_endpoint_available_through_router(self) -> None:
        """Test that basic health endpoint is properly registered."""
        app = create_app()
        client = TestClient(app)

        # Test that the endpoint exists and responds
        response = client.get("/api/v1/health/")
        assert response.status_code == 200

    def test_health_endpoint_returns_json_content_type(self) -> None:
        """Test that health endpoint returns proper JSON content type."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/api/v1/health/")
        assert "application/json" in response.headers["content-type"]


class TestDetailedHealthEndpoint:
    """Unit test cases for detailed health check endpoint with mocked dependencies."""

    def test_detailed_health_check_success_with_mocked_dependencies(self) -> None:
        """Test detailed health check with mocked healthy dependencies."""
        from app.container import Container

        # Create app with mocked container
        app = create_app()

        # Mock the repository
        mock_repo = AsyncMock()
        mock_repo.test_connection = AsyncMock(return_value=None)

        # Create a mock container with the mocked repository
        mock_container = Mock(spec=Container)
        mock_container.config.return_value = Mock()
        mock_container.energy_data_repository.return_value = mock_repo

        # Replace the container in app state
        app.state.container = mock_container

        client = TestClient(app)
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

    def test_detailed_health_check_database_failure(self) -> None:
        """Test detailed health check when database connection fails."""
        from app.container import Container

        # Create app with mocked container
        app = create_app()

        # Mock the repository to raise an error
        mock_repo = AsyncMock()
        mock_repo.test_connection = AsyncMock(
            side_effect=DataAccessError(
                "Connection failed",
                model_type="EnergyData",
                operation="test_connection",
            )
        )

        # Create a mock container with the mocked repository
        mock_container = Mock(spec=Container)
        mock_container.config.return_value = Mock()
        mock_container.energy_data_repository.return_value = mock_repo

        # Replace the container in app state
        app.state.container = mock_container

        client = TestClient(app)
        response = client.get("/api/v1/health/detailed")

        # Should return 503 when database is unhealthy
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "Service is unhealthy" in data["detail"]

    def test_detailed_health_check_response_schema(self) -> None:
        """Test that detailed health response matches expected schema."""
        from app.container import Container

        # Create app with mocked container
        app = create_app()

        # Mock healthy dependencies
        mock_repo = AsyncMock()
        mock_repo.test_connection = AsyncMock(return_value=None)

        # Create a mock container with the mocked repository
        mock_container = Mock(spec=Container)
        mock_container.config.return_value = Mock()
        mock_container.energy_data_repository.return_value = mock_repo

        # Replace the container in app state
        app.state.container = mock_container

        client = TestClient(app)
        response = client.get("/api/v1/health/detailed")

        assert response.status_code == 200
        data = response.json()

        # Should be able to parse as DetailedHealthResponse
        detailed_response = DetailedHealthResponse(**data)
        assert detailed_response.status == "healthy"
        assert detailed_response.database == "healthy"
        assert isinstance(detailed_response.components, dict)
