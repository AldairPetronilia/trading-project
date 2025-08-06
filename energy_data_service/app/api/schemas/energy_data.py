"""Energy data API schemas for request/response validation."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from pydantic_core.core_schema import ValidationInfo

if TYPE_CHECKING:
    from app.models.load_data import EnergyDataPoint


class EnergyDataQuery(BaseModel):
    """Query parameters for energy data endpoint."""

    area_code: str = Field(
        ...,
        description="Geographic area code (e.g., 'DE', 'FR', 'NL')",
        min_length=2,
        max_length=10,
    )
    start_time: datetime = Field(
        ...,
        description="Start time for data query (ISO 8601 format)",
    )
    end_time: datetime = Field(
        ...,
        description="End time for data query (ISO 8601 format)",
    )
    data_type: str | None = Field(
        None,
        description="Filter by energy data type",
        max_length=50,
    )
    business_type: str | None = Field(
        None,
        description="Filter by business type",
        max_length=50,
    )
    limit: int = Field(
        1000,
        ge=1,
        le=10000,
        description="Maximum number of records to return",
    )

    @field_validator("end_time")  # type: ignore[misc]
    @classmethod
    def validate_time_range(cls, v: datetime, info: ValidationInfo) -> datetime:
        """Validate that end_time is after start_time."""
        if info.data and "start_time" in info.data and v <= info.data["start_time"]:
            msg = "end_time must be after start_time"
            raise ValueError(msg)
        return v

    @field_validator("area_code")  # type: ignore[misc]
    @classmethod
    def validate_area_code(cls, v: str) -> str:
        """Validate and normalize area code."""
        return v.upper().strip()


class EnergyDataResponse(BaseModel):
    """Response model for a single energy data point."""

    timestamp: datetime = Field(
        ...,
        description="Data point timestamp",
    )
    area_code: str = Field(
        ...,
        description="Geographic area code",
    )
    data_type: str = Field(
        ...,
        description="Type of energy data",
    )
    business_type: str = Field(
        ...,
        description="Business type classification",
    )
    quantity: Decimal = Field(
        ...,
        description="Quantity value",
    )
    unit: str = Field(
        ...,
        description="Unit of measurement (e.g., 'MW')",
    )
    data_source: str = Field(
        ...,
        description="Source of the data (e.g., 'ENTSOE')",
    )
    resolution: str | None = Field(
        None,
        description="Data resolution (e.g., 'PT15M', 'PT60M')",
    )
    curve_type: str | None = Field(
        None,
        description="Curve type classification",
    )
    document_mrid: str | None = Field(
        None,
        description="Document MRID identifier",
    )
    revision_number: int | None = Field(
        None,
        description="Document revision number",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "timestamp": "2024-01-01T12:00:00Z",
                "area_code": "DE",
                "data_type": "A75",
                "business_type": "A01",
                "quantity": 1234.56,
                "unit": "MW",
                "data_source": "ENTSOE",
                "resolution": "PT15M",
            }
        },
    )

    @field_serializer("quantity")  # type: ignore[misc]
    def serialize_decimal(self, v: Decimal) -> float:
        """Serialize Decimal to float for JSON compatibility."""
        return float(v)

    @field_serializer("timestamp")  # type: ignore[misc]
    def serialize_datetime(self, v: datetime) -> str:
        """Serialize datetime to ISO format string."""
        return v.isoformat()

    @classmethod
    def from_model(cls, model: "EnergyDataPoint") -> "EnergyDataResponse":
        """Create response from database model.

        Args:
            model: EnergyDataPoint database model instance

        Returns:
            EnergyDataResponse instance
        """
        return cls(
            timestamp=model.timestamp,
            area_code=model.area_code,
            data_type=model.data_type,
            business_type=model.business_type,
            quantity=model.quantity,
            unit=model.unit,
            data_source=model.data_source,
            resolution=model.resolution,
            curve_type=model.curve_type,
            document_mrid=model.document_mrid,
            revision_number=model.revision_number,
        )
