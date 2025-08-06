"""Tests for FastAPI application factory and structure."""

import pytest
from app.api.app import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestCreateApp:
    """Test cases for FastAPI application factory."""

    def test_create_app_returns_fastapi_instance(self) -> None:
        """Test that create_app returns a FastAPI instance with correct configuration."""
        app = create_app()

        assert isinstance(app, FastAPI)
        assert app.title == "Energy Data Service API"
        assert app.version == "1.0.0"
        assert "REST API for energy data collection" in app.description

    def test_app_has_dependency_container(self) -> None:
        """Test that the app has a dependency injection container in state."""
        app = create_app()

        assert hasattr(app.state, "container")
        assert app.state.container is not None

    def test_app_includes_v1_router(self) -> None:
        """Test that the app includes the v1 API router."""
        app = create_app()

        # Check that v1 routes are registered
        route_paths = [route.path for route in app.routes]
        v1_routes = [path for path in route_paths if path.startswith("/api/v1")]

        assert len(v1_routes) > 0, "No v1 API routes found"

    def test_health_endpoint_accessible(self) -> None:
        """Test that basic health endpoint is accessible."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/api/v1/health/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "Energy Data Service API is operational" in data["message"]
