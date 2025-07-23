from collections.abc import Generator
from datetime import UTC, datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from app.models.base import Base
from app.models.load_data import EnergyDataPoint, EnergyDataType
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def in_memory_db() -> Generator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def sample_energy_data_point() -> dict[str, Any]:
    return {
        "timestamp": datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        "area_code": "10YCZ-CEPS-----N",
        "data_type": EnergyDataType.ACTUAL,
        "business_type": "A04",
        "quantity": Decimal("6363.000"),
        "unit": "MAW",
        "data_source": "entsoe",
        "document_mrid": "8086330c19054ec18d7cb023f1541062",
        "revision_number": 1,
        "document_created_at": datetime(2024, 1, 1, 8, 8, 24, tzinfo=UTC),
        "time_series_mrid": "1",
        "resolution": "PT60M",
        "curve_type": "A01",
        "object_aggregation": "A01",
        "position": 1,
        "period_start": datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        "period_end": datetime(2024, 1, 2, 0, 0, tzinfo=UTC),
    }


class TestEnergyDataType:
    def test_enum_values(self) -> None:
        assert EnergyDataType.ACTUAL.value == "actual"
        assert EnergyDataType.DAY_AHEAD.value == "day_ahead"
        assert EnergyDataType.WEEK_AHEAD.value == "week_ahead"
        assert EnergyDataType.MONTH_AHEAD.value == "month_ahead"
        assert EnergyDataType.YEAR_AHEAD.value == "year_ahead"
        assert EnergyDataType.FORECAST_MARGIN.value == "forecast_margin"

    def test_enum_string_representation(self) -> None:
        assert EnergyDataType.ACTUAL.value == "actual"
        assert EnergyDataType.DAY_AHEAD.value == "day_ahead"

    def test_enum_membership(self) -> None:
        assert "actual" in [e.value for e in EnergyDataType]
        assert "invalid_type" not in [e.value for e in EnergyDataType]


class TestEnergyDataPoint:
    def test_create_valid_instance(
        self,
        in_memory_db: Session,
        sample_energy_data_point: dict[str, Any],
    ) -> None:
        data_point = EnergyDataPoint(**sample_energy_data_point)
        in_memory_db.add(data_point)
        in_memory_db.commit()

        assert data_point.timestamp.replace(tzinfo=None) == sample_energy_data_point[
            "timestamp"
        ].replace(tzinfo=None)
        assert data_point.area_code == sample_energy_data_point["area_code"]
        assert data_point.data_type == sample_energy_data_point["data_type"]
        assert data_point.business_type == sample_energy_data_point["business_type"]
        assert data_point.quantity == sample_energy_data_point["quantity"]
        assert data_point.created_at is not None
        assert data_point.updated_at is not None

    def test_default_values(
        self,
        in_memory_db: Session,
        sample_energy_data_point: dict[str, Any],
    ) -> None:
        sample_energy_data_point.pop("unit")
        sample_energy_data_point.pop("data_source")

        data_point = EnergyDataPoint(**sample_energy_data_point)
        in_memory_db.add(data_point)
        in_memory_db.commit()

        assert data_point.unit == "MAW"
        assert data_point.data_source == "entsoe"

    def test_composite_primary_key_uniqueness(
        self,
        in_memory_db: Session,
        sample_energy_data_point: dict[str, Any],
    ) -> None:
        data_point1 = EnergyDataPoint(**sample_energy_data_point)
        in_memory_db.add(data_point1)
        in_memory_db.commit()

        data_point2 = EnergyDataPoint(**sample_energy_data_point)
        in_memory_db.add(data_point2)

        with pytest.raises(IntegrityError):
            in_memory_db.commit()

    def test_different_composite_keys_allowed(
        self,
        in_memory_db: Session,
        sample_energy_data_point: dict[str, Any],
    ) -> None:
        data_point1 = EnergyDataPoint(**sample_energy_data_point)
        in_memory_db.add(data_point1)
        in_memory_db.commit()

        sample_energy_data_point["business_type"] = "A05"
        data_point2 = EnergyDataPoint(**sample_energy_data_point)
        in_memory_db.add(data_point2)
        in_memory_db.commit()

        assert in_memory_db.query(EnergyDataPoint).count() == 2

    def test_decimal_precision(
        self,
        in_memory_db: Session,
        sample_energy_data_point: dict[str, Any],
    ) -> None:
        sample_energy_data_point["quantity"] = Decimal("123456789012.123")

        data_point = EnergyDataPoint(**sample_energy_data_point)
        in_memory_db.add(data_point)
        in_memory_db.commit()

        retrieved = in_memory_db.query(EnergyDataPoint).first()
        assert retrieved.quantity == Decimal("123456789012.123")

    def test_required_fields_validation(
        self,
        in_memory_db: Session,
        sample_energy_data_point: dict[str, Any],
    ) -> None:
        sample_energy_data_point.pop("quantity")

        data_point = EnergyDataPoint(**sample_energy_data_point)
        in_memory_db.add(data_point)

        with pytest.raises(IntegrityError):
            in_memory_db.commit()

    def test_nullable_fields(
        self,
        in_memory_db: Session,
        sample_energy_data_point: dict[str, Any],
    ) -> None:
        sample_energy_data_point["revision_number"] = None

        data_point = EnergyDataPoint(**sample_energy_data_point)
        in_memory_db.add(data_point)
        in_memory_db.commit()

        assert data_point.revision_number is None

    def test_timezone_aware_datetime_fields_exist(
        self,
        in_memory_db: Session,
        sample_energy_data_point: dict[str, Any],
    ) -> None:
        data_point = EnergyDataPoint(**sample_energy_data_point)
        in_memory_db.add(data_point)
        in_memory_db.commit()

        assert hasattr(data_point, "timestamp")
        assert hasattr(data_point, "document_created_at")
        assert hasattr(data_point, "period_start")
        assert hasattr(data_point, "period_end")
        assert isinstance(data_point.timestamp, datetime)
        assert isinstance(data_point.document_created_at, datetime)

    def test_inheritance_from_timestamped_model(
        self,
        in_memory_db: Session,
        sample_energy_data_point: dict[str, Any],
    ) -> None:
        data_point = EnergyDataPoint(**sample_energy_data_point)
        in_memory_db.add(data_point)
        in_memory_db.commit()

        assert hasattr(data_point, "created_at")
        assert hasattr(data_point, "updated_at")
        assert data_point.created_at is not None
        assert data_point.updated_at is not None
        assert data_point.created_at == data_point.updated_at

    def test_table_name(self) -> None:
        assert EnergyDataPoint.__tablename__ == "energy_data_points"

    def test_indexes_are_defined(self) -> None:
        indexes = EnergyDataPoint.__table_args__
        index_names = [idx.name for idx in indexes if hasattr(idx, "name")]

        expected_indexes = [
            "ix_energy_data_timestamp_area",
            "ix_energy_data_type_timestamp",
            "ix_energy_data_document_mrid",
            "ix_energy_data_area_type_timestamp",
        ]

        for expected_index in expected_indexes:
            assert expected_index in index_names
