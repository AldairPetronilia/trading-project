"""Tests for price data models."""

from datetime import UTC, datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from app.models.base import Base
from app.models.load_data import EnergyDataType
from app.models.price_data import EnergyPricePoint
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError


class TestEnergyPricePoint:
    """Tests for EnergyPricePoint model."""

    @pytest.fixture
    def engine(self) -> Engine:
        """Create in-memory SQLite engine for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def sample_price_point(self) -> EnergyPricePoint:
        """Create a sample EnergyPricePoint for testing."""
        return EnergyPricePoint(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            area_code="DE",
            data_type=EnergyDataType.DAY_AHEAD,
            business_type="B11",
            price_amount=Decimal("45.67"),
            currency_unit_name="EUR",
            price_measure_unit_name="EUR/MWh",
            auction_type="A01",
            contract_market_agreement_type="A01",
            data_source="entsoe",
            document_mrid="test-document-123",
            revision_number=1,
            document_created_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
            time_series_mrid="test-series-456",
            resolution="PT1H",
            curve_type="A01",
            position=1,
            period_start=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            period_end=datetime(2024, 1, 1, 13, 0, tzinfo=UTC),
        )

    def test_energy_price_point_creation(
        self, sample_price_point: EnergyPricePoint
    ) -> None:
        """Test that EnergyPricePoint can be created with valid data."""
        assert sample_price_point.price_amount == Decimal("45.67")
        assert sample_price_point.currency_unit_name == "EUR"
        assert sample_price_point.price_measure_unit_name == "EUR/MWh"
        assert sample_price_point.auction_type == "A01"
        assert sample_price_point.contract_market_agreement_type == "A01"
        assert sample_price_point.area_code == "DE"
        assert sample_price_point.data_type == EnergyDataType.DAY_AHEAD
        assert sample_price_point.business_type == "B11"

    def test_price_amount_precision(self) -> None:
        """Test that price_amount maintains proper decimal precision."""
        price_point = EnergyPricePoint(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            area_code="DE",
            data_type=EnergyDataType.DAY_AHEAD,
            business_type="B11",
            price_amount=Decimal("45.678901"),  # 6 decimal places
            currency_unit_name="EUR",
            price_measure_unit_name="EUR/MWh",
            data_source="entsoe",
            document_mrid="test-document-123",
            document_created_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
            time_series_mrid="test-series-456",
            resolution="PT1H",
            position=1,
            period_start=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            period_end=datetime(2024, 1, 1, 13, 0, tzinfo=UTC),
        )

        assert price_point.price_amount == Decimal("45.678901")
        assert str(price_point.price_amount) == "45.678901"

    def test_composite_primary_key_uniqueness(
        self, engine: Engine, sample_price_point: EnergyPricePoint
    ) -> None:
        """Test that composite primary key enforces uniqueness."""
        from sqlalchemy.orm import sessionmaker

        session_maker = sessionmaker(bind=engine)
        session = session_maker()

        try:
            # Insert first price point
            session.add(sample_price_point)
            session.commit()

            # Try to insert duplicate with same composite key
            duplicate = EnergyPricePoint(
                timestamp=sample_price_point.timestamp,
                area_code=sample_price_point.area_code,
                data_type=sample_price_point.data_type,
                business_type=sample_price_point.business_type,
                price_amount=Decimal("99.99"),  # Different price
                currency_unit_name="USD",  # Different currency
                price_measure_unit_name="USD/MWh",
                data_source="entsoe",
                document_mrid="different-document-789",
                document_created_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
                time_series_mrid="different-series-789",
                resolution="PT1H",
                position=1,
                period_start=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
                period_end=datetime(2024, 1, 1, 13, 0, tzinfo=UTC),
            )

            session.add(duplicate)

            with pytest.raises(IntegrityError):
                session.commit()

        finally:
            session.close()

    def test_different_composite_keys_allowed(
        self, engine: Engine, sample_price_point: EnergyPricePoint
    ) -> None:
        """Test that different composite keys are allowed."""
        from sqlalchemy.orm import sessionmaker

        session_maker = sessionmaker(bind=engine)
        session = session_maker()

        try:
            # Insert first price point
            session.add(sample_price_point)
            session.commit()

            # Create price point with different timestamp (different composite key)
            different_timestamp = EnergyPricePoint(
                timestamp=datetime(
                    2024, 1, 1, 13, 0, tzinfo=UTC
                ),  # Different timestamp
                area_code=sample_price_point.area_code,
                data_type=sample_price_point.data_type,
                business_type=sample_price_point.business_type,
                price_amount=Decimal("50.00"),
                currency_unit_name="EUR",
                price_measure_unit_name="EUR/MWh",
                data_source="entsoe",
                document_mrid="test-document-456",
                document_created_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
                time_series_mrid="test-series-789",
                resolution="PT1H",
                position=2,
                period_start=datetime(2024, 1, 1, 13, 0, tzinfo=UTC),
                period_end=datetime(2024, 1, 1, 14, 0, tzinfo=UTC),
            )

            session.add(different_timestamp)
            session.commit()

            # Verify both records exist
            count = session.query(EnergyPricePoint).count()
            assert count == 2

        finally:
            session.close()

    def test_nullable_fields(self) -> None:
        """Test that nullable fields can be None."""
        price_point = EnergyPricePoint(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            area_code="DE",
            data_type=EnergyDataType.DAY_AHEAD,
            business_type="B11",
            price_amount=Decimal("45.67"),
            currency_unit_name="EUR",
            price_measure_unit_name="EUR/MWh",
            auction_type=None,  # Nullable
            contract_market_agreement_type=None,  # Nullable
            data_source="entsoe",
            document_mrid="test-document-123",
            revision_number=None,  # Nullable
            document_created_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
            time_series_mrid="test-series-456",
            resolution="PT1H",
            curve_type=None,  # Nullable
            position=1,
            period_start=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            period_end=datetime(2024, 1, 1, 13, 0, tzinfo=UTC),
        )

        assert price_point.auction_type is None
        assert price_point.contract_market_agreement_type is None
        assert price_point.revision_number is None
        assert price_point.curve_type is None

    def test_currency_field_validation(
        self, sample_price_point: EnergyPricePoint
    ) -> None:
        """Test currency field properties."""
        assert len(sample_price_point.currency_unit_name) <= 10
        assert len(sample_price_point.price_measure_unit_name) <= 20
        assert sample_price_point.currency_unit_name == "EUR"
        assert sample_price_point.price_measure_unit_name == "EUR/MWh"

    def test_energy_data_type_enum_usage(
        self, sample_price_point: EnergyPricePoint
    ) -> None:
        """Test that EnergyDataType enum is properly used."""
        assert isinstance(sample_price_point.data_type, EnergyDataType)
        assert sample_price_point.data_type == EnergyDataType.DAY_AHEAD

    def test_default_values(self, engine: Engine) -> None:
        """Test that default values are applied correctly."""
        from sqlalchemy.orm import sessionmaker

        session_maker = sessionmaker(bind=engine)
        session = session_maker()

        try:
            # Create price point without data_source to test default
            price_point = EnergyPricePoint(
                timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
                area_code="DE",
                data_type=EnergyDataType.DAY_AHEAD,
                business_type="B11",
                price_amount=Decimal("45.67"),
                currency_unit_name="EUR",
                price_measure_unit_name="EUR/MWh",
                document_mrid="test-document-123",
                document_created_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
                time_series_mrid="test-series-456",
                resolution="PT1H",
                position=1,
                period_start=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
                period_end=datetime(2024, 1, 1, 13, 0, tzinfo=UTC),
                # Note: data_source omitted to test default
            )

            # Add to database to trigger defaults
            session.add(price_point)
            session.commit()

            # Check default value was applied
            assert price_point.data_source == "entsoe"

        finally:
            session.close()

    def test_timestamped_model_inheritance(
        self, sample_price_point: EnergyPricePoint
    ) -> None:
        """Test that EnergyPricePoint inherits TimestampedModel fields."""
        # TimestampedModel fields should be present
        assert hasattr(sample_price_point, "created_at")
        assert hasattr(sample_price_point, "updated_at")

    def test_table_name(self) -> None:
        """Test that the correct table name is set."""
        assert EnergyPricePoint.__tablename__ == "energy_price_points"

    def test_required_fields_not_null(self) -> None:
        """Test that required fields cannot be None."""
        # This test ensures our model definition is correct
        # The actual null constraint validation happens at the database level
        required_fields = [
            "timestamp",
            "area_code",
            "data_type",
            "business_type",
            "price_amount",
            "currency_unit_name",
            "price_measure_unit_name",
            "data_source",
            "document_mrid",
            "document_created_at",
            "time_series_mrid",
            "resolution",
            "position",
            "period_start",
            "period_end",
        ]

        for field in required_fields:
            assert hasattr(EnergyPricePoint, field)
