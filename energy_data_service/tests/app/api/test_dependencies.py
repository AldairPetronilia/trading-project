"""Tests for FastAPI dependency injection bridge."""

from unittest.mock import Mock

import pytest
from app.api.dependencies import (
    get_backfill_progress_repository,
    get_backfill_service,
    get_container,
    get_energy_data_repository,
    get_entsoe_data_service,
)
from app.container import Container
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


class TestGetContainer:
    """Test cases for get_container dependency provider."""

    def test_get_container_returns_app_state_container(self) -> None:
        """Test that get_container returns the container from app state."""
        # Create mock request with container in app state
        mock_app = Mock()
        mock_container = Mock(spec=Container)
        mock_app.state.container = mock_container

        mock_request = Mock(spec=Request)
        mock_request.app = mock_app

        result = get_container(mock_request)

        assert result is mock_container


class TestRepositoryDependencies:
    """Test cases for repository dependency providers."""

    def test_get_energy_data_repository(self) -> None:
        """Test that get_energy_data_repository returns repository from container."""
        mock_container = Mock(spec=Container)
        mock_repository = Mock()
        mock_container.energy_data_repository.return_value = mock_repository

        result = get_energy_data_repository(mock_container)

        assert result is mock_repository
        mock_container.energy_data_repository.assert_called_once()

    def test_get_backfill_progress_repository(self) -> None:
        """Test that get_backfill_progress_repository returns repository from container."""
        mock_container = Mock(spec=Container)
        mock_repository = Mock()
        mock_container.backfill_progress_repository.return_value = mock_repository

        result = get_backfill_progress_repository(mock_container)

        assert result is mock_repository
        mock_container.backfill_progress_repository.assert_called_once()


class TestServiceDependencies:
    """Test cases for service dependency providers."""

    def test_get_entsoe_data_service(self) -> None:
        """Test that get_entsoe_data_service returns service from container."""
        mock_container = Mock(spec=Container)
        mock_service = Mock()
        mock_container.entsoe_data_service.return_value = mock_service

        result = get_entsoe_data_service(mock_container)

        assert result is mock_service
        mock_container.entsoe_data_service.assert_called_once()

    def test_get_backfill_service(self) -> None:
        """Test that get_backfill_service returns service from container."""
        mock_container = Mock(spec=Container)
        mock_service = Mock()
        mock_container.backfill_service.return_value = mock_service

        result = get_backfill_service(mock_container)

        assert result is mock_service
        mock_container.backfill_service.assert_called_once()


class TestDependencyIntegration:
    """Integration tests for dependency injection with FastAPI."""

    def test_dependencies_work_in_fastapi_context(self) -> None:
        """Test that dependencies can be resolved in actual FastAPI context."""
        from app.api.app import create_app

        app = create_app()
        client = TestClient(app)

        # Test that health endpoint works (uses dependencies)
        response = client.get("/api/v1/health/")

        assert response.status_code == 200
        # If dependencies were broken, this would fail with 500 error
