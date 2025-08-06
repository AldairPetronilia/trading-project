"""Unit tests for energy data API schemas."""

from datetime import UTC, datetime, timezone
from decimal import Decimal

import pytest
from app.api.schemas.energy_data import EnergyDataQuery, EnergyDataResponse
from pydantic import ValidationError
from pydantic_core.core_schema import ValidationInfo


class TestEnergyDataQuery:
    """Test suite for EnergyDataQuery schema."""

    def test_valid_query_minimal(self) -> None:
        """Test valid query with minimal required fields."""
        query = EnergyDataQuery(
            area_code="DE",
            start_time=datetime(2024, 1, 1, tzinfo=UTC),
            end_time=datetime(2024, 1, 2, tzinfo=UTC),
        )

        assert query.area_code == "DE"
        assert query.start_time == datetime(2024, 1, 1, tzinfo=UTC)
        assert query.end_time == datetime(2024, 1, 2, tzinfo=UTC)
        assert query.limit == 1000  # default value
        assert query.data_type is None
        assert query.business_type is None

    def test_valid_query_all_fields(self) -> None:
        """Test valid query with all fields specified."""
        query = EnergyDataQuery(
            area_code="fr",  # lowercase to test normalization
            start_time=datetime(2024, 1, 1, tzinfo=UTC),
            end_time=datetime(2024, 1, 2, tzinfo=UTC),
            data_type="A75",
            business_type="A01",
            limit=500,
        )

        assert query.area_code == "FR"  # normalized to uppercase
        assert query.data_type == "A75"
        assert query.business_type == "A01"
        assert query.limit == 500

    def test_area_code_normalization(self) -> None:
        """Test that area codes are normalized to uppercase."""
        query = EnergyDataQuery(
            area_code="  nl  ",  # with whitespace
            start_time=datetime(2024, 1, 1, tzinfo=UTC),
            end_time=datetime(2024, 1, 2, tzinfo=UTC),
        )

        assert query.area_code == "NL"

    def test_invalid_time_range(self) -> None:
        """Test that end_time must be after start_time."""
        with pytest.raises(ValidationError) as exc_info:
            EnergyDataQuery(
                area_code="DE",
                start_time=datetime(2024, 1, 2, tzinfo=UTC),
                end_time=datetime(2024, 1, 1, tzinfo=UTC),
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "end_time must be after start_time" in str(errors[0]["ctx"]["error"])

    def test_invalid_limit_too_low(self) -> None:
        """Test that limit must be at least 1."""
        with pytest.raises(ValidationError) as exc_info:
            EnergyDataQuery(
                area_code="DE",
                start_time=datetime(2024, 1, 1, tzinfo=UTC),
                end_time=datetime(2024, 1, 2, tzinfo=UTC),
                limit=0,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("limit",)

    def test_invalid_limit_too_high(self) -> None:
        """Test that limit cannot exceed 10000."""
        with pytest.raises(ValidationError) as exc_info:
            EnergyDataQuery(
                area_code="DE",
                start_time=datetime(2024, 1, 1, tzinfo=UTC),
                end_time=datetime(2024, 1, 2, tzinfo=UTC),
                limit=10001,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("limit",)

    def test_invalid_area_code_too_short(self) -> None:
        """Test that area code must be at least 2 characters."""
        with pytest.raises(ValidationError) as exc_info:
            EnergyDataQuery(
                area_code="D",
                start_time=datetime(2024, 1, 1, tzinfo=UTC),
                end_time=datetime(2024, 1, 2, tzinfo=UTC),
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("area_code",)

    def test_missing_required_fields(self) -> None:
        """Test that required fields must be provided."""
        with pytest.raises(ValidationError) as exc_info:
            EnergyDataQuery()

        errors = exc_info.value.errors()
        assert len(errors) == 3
        required_fields = {error["loc"][0] for error in errors}
        assert required_fields == {"area_code", "start_time", "end_time"}


class TestEnergyDataResponse:
    """Test suite for EnergyDataResponse schema."""

    def test_valid_response_minimal(self) -> None:
        """Test valid response with minimal required fields."""
        response = EnergyDataResponse(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            area_code="DE",
            data_type="A75",
            business_type="A01",
            quantity=Decimal("1234.56"),
            unit="MW",
            data_source="ENTSOE",
        )

        assert response.timestamp == datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        assert response.area_code == "DE"
        assert response.data_type == "A75"
        assert response.business_type == "A01"
        assert response.quantity == Decimal("1234.56")
        assert response.unit == "MW"
        assert response.data_source == "ENTSOE"
        assert response.resolution is None
        assert response.curve_type is None

    def test_valid_response_all_fields(self) -> None:
        """Test valid response with all fields specified."""
        response = EnergyDataResponse(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            area_code="DE",
            data_type="A75",
            business_type="A01",
            quantity=Decimal("1234.56"),
            unit="MW",
            data_source="ENTSOE",
            resolution="PT15M",
            curve_type="A01",
            document_mrid="test-mrid-123",
            revision_number=1,
        )

        assert response.resolution == "PT15M"
        assert response.curve_type == "A01"
        assert response.document_mrid == "test-mrid-123"
        assert response.revision_number == 1

    def test_json_serialization(self) -> None:
        """Test that response can be serialized to JSON correctly."""
        response = EnergyDataResponse(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            area_code="DE",
            data_type="A75",
            business_type="A01",
            quantity=Decimal("1234.56"),
            unit="MW",
            data_source="ENTSOE",
        )

        # Test model_dump without serialization (raw Python objects)
        raw_data = response.model_dump(mode="python")
        assert raw_data["quantity"] == 1234.56  # Serialized to float
        assert (
            raw_data["timestamp"] == "2024-01-01T12:00:00+00:00"
        )  # Serialized to ISO string

        # Test JSON mode serialization
        json_str = response.model_dump_json()
        assert "1234.56" in json_str
        assert "2024-01-01T12:00:00" in json_str

    def test_from_model(self) -> None:
        """Test creating response from a mock database model."""

        # Create a mock model object
        class MockModel:
            timestamp = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
            area_code = "DE"
            data_type = "A75"
            business_type = "A01"
            quantity = Decimal("1234.56")
            unit = "MW"
            data_source = "ENTSOE"
            resolution = "PT15M"
            curve_type = "A01"
            document_mrid = "test-mrid"
            revision_number = 1

        response = EnergyDataResponse.from_model(MockModel())

        assert response.timestamp == MockModel.timestamp
        assert response.area_code == MockModel.area_code
        assert response.data_type == MockModel.data_type
        assert response.business_type == MockModel.business_type
        assert response.quantity == MockModel.quantity
        assert response.unit == MockModel.unit
        assert response.data_source == MockModel.data_source
        assert response.resolution == MockModel.resolution
        assert response.curve_type == MockModel.curve_type
        assert response.document_mrid == MockModel.document_mrid
        assert response.revision_number == MockModel.revision_number

    def test_missing_required_fields(self) -> None:
        """Test that required fields must be provided."""
        with pytest.raises(ValidationError) as exc_info:
            EnergyDataResponse()

        errors = exc_info.value.errors()
        required_fields = {error["loc"][0] for error in errors}
        assert required_fields == {
            "timestamp",
            "area_code",
            "data_type",
            "business_type",
            "quantity",
            "unit",
            "data_source",
        }

    def test_from_attributes_config(self) -> None:
        """Test that from_attributes config allows ORM model conversion."""
        assert EnergyDataResponse.model_config["from_attributes"] is True
