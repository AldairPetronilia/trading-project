"""Unit tests for energy data API endpoints."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.api.v1.endpoints.energy_data import get_energy_data
from app.exceptions.repository_exceptions import RepositoryError
from app.models.load_data import EnergyDataPoint
from fastapi import HTTPException
from fastapi.testclient import TestClient


class TestEnergyDataEndpoints:
    """Test suite for energy data endpoints."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create a mock energy data repository."""
        return AsyncMock()

    @pytest.fixture
    def sample_energy_data(self) -> list[Mock]:
        """Create sample energy data points."""
        data_points = []
        for i in range(5):
            mock_point = Mock(spec=EnergyDataPoint)
            mock_point.timestamp = datetime(2024, 1, 1, i, 0, tzinfo=UTC)
            mock_point.area_code = "DE"
            mock_point.data_type = "A75"
            mock_point.business_type = "A01"
            mock_point.quantity = Decimal(f"100{i}.50")
            mock_point.unit = "MW"
            mock_point.data_source = "ENTSOE"
            mock_point.resolution = "PT15M"
            mock_point.curve_type = "A01"
            mock_point.document_mrid = f"doc-{i}"
            mock_point.revision_number = 1
            data_points.append(mock_point)
        return data_points

    async def test_get_energy_data_success(
        self, mock_repository: AsyncMock, sample_energy_data: list[Mock]
    ) -> None:
        """Test successful energy data retrieval."""
        # Setup mock
        mock_repository.get_by_time_range.return_value = sample_energy_data

        # Call endpoint
        result = await get_energy_data(
            area_code="DE",
            start_time=datetime(2024, 1, 1, tzinfo=UTC),
            end_time=datetime(2024, 1, 2, tzinfo=UTC),
            data_type=None,
            business_type=None,
            limit=1000,
            repository=mock_repository,
        )

        # Verify
        assert len(result) == 5
        assert result[0].area_code == "DE"
        assert result[0].data_type == "A75"
        assert result[0].quantity == Decimal("1000.50")

        # Verify repository was called correctly
        mock_repository.get_by_time_range.assert_called_once_with(
            area_codes=["DE"],
            start_time=datetime(2024, 1, 1, tzinfo=UTC),
            end_time=datetime(2024, 1, 2, tzinfo=UTC),
        )

    async def test_get_energy_data_with_filters(
        self, mock_repository: AsyncMock, sample_energy_data: list[Mock]
    ) -> None:
        """Test energy data retrieval with data_type and business_type filters."""
        # Setup mock with mixed data types
        mixed_data = sample_energy_data.copy()
        mixed_data[2].data_type = "A74"  # Different data type
        mixed_data[3].business_type = "A02"  # Different business type
        mock_repository.get_by_time_range.return_value = mixed_data

        # Call endpoint with filters
        result = await get_energy_data(
            area_code="DE",
            start_time=datetime(2024, 1, 1, tzinfo=UTC),
            end_time=datetime(2024, 1, 2, tzinfo=UTC),
            data_type="A75",
            business_type="A01",
            limit=1000,
            repository=mock_repository,
        )

        # Verify filtering worked
        assert len(result) == 3  # Only items matching both filters
        assert all(r.data_type == "A75" for r in result)
        assert all(r.business_type == "A01" for r in result)

    async def test_get_energy_data_area_code_normalization(
        self, mock_repository: AsyncMock, sample_energy_data: list[Mock]
    ) -> None:
        """Test that area codes are normalized to uppercase."""
        mock_repository.get_by_time_range.return_value = sample_energy_data

        # Call with lowercase area code
        await get_energy_data(
            area_code="de",
            start_time=datetime(2024, 1, 1, tzinfo=UTC),
            end_time=datetime(2024, 1, 2, tzinfo=UTC),
            data_type=None,
            business_type=None,
            limit=1000,
            repository=mock_repository,
        )

        # Verify uppercase was used
        mock_repository.get_by_time_range.assert_called_once()
        call_args = mock_repository.get_by_time_range.call_args
        assert call_args.kwargs["area_codes"] == ["DE"]

    async def test_get_energy_data_invalid_time_range(
        self, mock_repository: AsyncMock
    ) -> None:
        """Test that invalid time range raises HTTP 400 error."""
        with pytest.raises(HTTPException) as exc_info:
            await get_energy_data(
                area_code="DE",
                start_time=datetime(2024, 1, 2, tzinfo=UTC),
                end_time=datetime(2024, 1, 1, tzinfo=UTC),  # Before start
                data_type=None,
                business_type=None,
                limit=1000,
                repository=mock_repository,
            )

        assert exc_info.value.status_code == 400
        assert "end_time must be after start_time" in exc_info.value.detail

    async def test_get_energy_data_limit_applied(
        self, mock_repository: AsyncMock, sample_energy_data: list[Mock]
    ) -> None:
        """Test that limit parameter is correctly applied."""
        mock_repository.get_by_time_range.return_value = sample_energy_data

        # Request with limit of 2
        result = await get_energy_data(
            area_code="DE",
            start_time=datetime(2024, 1, 1, tzinfo=UTC),
            end_time=datetime(2024, 1, 2, tzinfo=UTC),
            data_type=None,
            business_type=None,
            limit=2,
            repository=mock_repository,
        )

        # Verify only 2 results returned
        assert len(result) == 2

    async def test_get_energy_data_repository_error(
        self, mock_repository: AsyncMock
    ) -> None:
        """Test that repository errors are handled correctly."""
        mock_repository.get_by_time_range.side_effect = RepositoryError(
            "Database connection failed"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_energy_data(
                area_code="DE",
                start_time=datetime(2024, 1, 1, tzinfo=UTC),
                end_time=datetime(2024, 1, 2, tzinfo=UTC),
                data_type=None,
                business_type=None,
                limit=1000,
                repository=mock_repository,
            )

        assert exc_info.value.status_code == 500
        assert "Database error" in exc_info.value.detail

    async def test_get_energy_data_empty_result(
        self, mock_repository: AsyncMock
    ) -> None:
        """Test handling of empty query results."""
        mock_repository.get_by_time_range.return_value = []

        result = await get_energy_data(
            area_code="DE",
            start_time=datetime(2024, 1, 1, tzinfo=UTC),
            end_time=datetime(2024, 1, 2, tzinfo=UTC),
            data_type=None,
            business_type=None,
            limit=1000,
            repository=mock_repository,
        )

        assert result == []

    async def test_get_energy_data_sqlalchemy_error(
        self, mock_repository: AsyncMock
    ) -> None:
        """Test that SQLAlchemy errors are handled correctly."""
        from sqlalchemy.exc import SQLAlchemyError

        mock_repository.get_by_time_range.side_effect = SQLAlchemyError(
            "Connection pool exhausted"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_energy_data(
                area_code="DE",
                start_time=datetime(2024, 1, 1, tzinfo=UTC),
                end_time=datetime(2024, 1, 2, tzinfo=UTC),
                data_type=None,
                business_type=None,
                limit=1000,
                repository=mock_repository,
            )

        assert exc_info.value.status_code == 500
        assert "Internal database error" in exc_info.value.detail

    async def test_get_energy_data_unexpected_error(
        self, mock_repository: AsyncMock
    ) -> None:
        """Test that unexpected errors are handled correctly."""
        mock_repository.get_by_time_range.side_effect = ValueError("Unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            await get_energy_data(
                area_code="DE",
                start_time=datetime(2024, 1, 1, tzinfo=UTC),
                end_time=datetime(2024, 1, 2, tzinfo=UTC),
                data_type=None,
                business_type=None,
                limit=1000,
                repository=mock_repository,
            )

        assert exc_info.value.status_code == 500
        assert "unexpected error occurred" in exc_info.value.detail
