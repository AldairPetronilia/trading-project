"""Tests for EnergyPriceRepository."""

import uuid
from datetime import UTC, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.config.database import Database
from app.exceptions.repository_exceptions import (
    DataAccessError,
)
from app.models.load_data import EnergyDataType
from app.models.price_data import EnergyPricePoint
from app.repositories.energy_price_repository import (
    EnergyPriceRepository,
)
from sqlalchemy.exc import SQLAlchemyError


def setup_session_mock(mock_database: Database, mock_session: AsyncMock) -> None:
    """Helper to setup session factory mock properly."""
    async_context_mock = AsyncMock()
    async_context_mock.__aenter__ = AsyncMock(return_value=mock_session)
    async_context_mock.__aexit__ = AsyncMock(return_value=None)
    mock_database.session_factory.return_value = async_context_mock


def create_test_price_point(
    timestamp: datetime | None = None,
    area_code: str = "DE",
    data_type: EnergyDataType = EnergyDataType.DAY_AHEAD,
    business_type: str = "A01",
    price_amount: Decimal = Decimal("45.67"),
    currency_unit_name: str = "EUR",
    price_measure_unit_name: str = "EUR/MWh",
    auction_type: str = "A01",
    contract_market_agreement_type: str = "A01",
) -> EnergyPricePoint:
    """Create a test EnergyPricePoint instance."""
    if timestamp is None:
        timestamp = datetime.now(UTC)

    return EnergyPricePoint(
        timestamp=timestamp,
        area_code=area_code,
        data_type=data_type,
        business_type=business_type,
        price_amount=price_amount,
        currency_unit_name=currency_unit_name,
        price_measure_unit_name=price_measure_unit_name,
        auction_type=auction_type,
        contract_market_agreement_type=contract_market_agreement_type,
        data_source="entsoe",
        document_mrid=f"test-doc-{uuid.uuid4()}",
        revision_number=1,
        document_created_at=datetime.now(UTC),
        time_series_mrid=f"test-ts-{uuid.uuid4()}",
        resolution="PT1H",
        curve_type="A01",
        position=1,
        period_start=timestamp,
        period_end=timestamp,
    )


@pytest.fixture
def mock_database() -> Database:
    """Create a mock database instance."""
    database = MagicMock(spec=Database)
    database.session_factory = MagicMock()
    return database


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def repository(mock_database: Database) -> EnergyPriceRepository:
    """Create an EnergyPriceRepository instance with mocked database."""
    return EnergyPriceRepository(mock_database)


@pytest.fixture
def sample_price_point() -> EnergyPricePoint:
    """Create a sample energy price point for testing."""
    return create_test_price_point()


@pytest.fixture
def multiple_price_points() -> list[EnergyPricePoint]:
    """Create multiple energy price points for batch testing."""
    base_time = datetime(2025, 1, 24, 12, 0, tzinfo=UTC)
    return [
        create_test_price_point(
            timestamp=base_time.replace(hour=12 + i),
            area_code="DE",
            price_amount=Decimal(f"45.{i}7"),
        )
        for i in range(3)
    ]


class TestEnergyPriceRepository:
    """Test suite for EnergyPriceRepository."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        sample_price_point: EnergyPricePoint,
    ) -> None:
        """Test successful retrieval by composite key."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_price_point
        mock_session.execute.return_value = mock_result

        composite_key = (
            sample_price_point.timestamp,
            sample_price_point.area_code,
            sample_price_point.data_type,
            sample_price_point.business_type,
        )
        result = await repository.get_by_id(composite_key)

        assert result == sample_price_point
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_tuple_signature(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        sample_price_point: EnergyPricePoint,
    ) -> None:
        """Test get_by_id validates tuple signature correctly."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_price_point
        mock_session.execute.return_value = mock_result

        composite_key = (
            sample_price_point.timestamp,
            sample_price_point.area_code,
            sample_price_point.data_type,
            sample_price_point.business_type,
        )
        result = await repository.get_by_id(composite_key)

        assert result == sample_price_point

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test retrieval by composite key when record not found."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        composite_key = (datetime.now(UTC), "DE", EnergyDataType.DAY_AHEAD, "A01")
        result = await repository.get_by_id(composite_key)

        assert result is None

    async def test_get_by_id_invalid_tuple(
        self, repository: EnergyPriceRepository
    ) -> None:
        """Test get_by_id raises ValueError for invalid tuple."""
        invalid_key = ("timestamp_only",)  # Missing required elements

        with pytest.raises(ValueError, match="item_id must be a tuple of"):
            await repository.get_by_id(invalid_key)

    @pytest.mark.asyncio
    async def test_get_by_id_database_error(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test get_by_id handles database errors properly."""
        setup_session_mock(mock_database, mock_session)

        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        composite_key = (datetime.now(UTC), "DE", EnergyDataType.DAY_AHEAD, "A01")

        with pytest.raises(
            DataAccessError, match="Failed to retrieve energy price point"
        ):
            await repository.get_by_id(composite_key)

    @pytest.mark.asyncio
    async def test_get_all_success(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_price_points: list[EnergyPricePoint],
    ) -> None:
        """Test successful retrieval of all price points."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = multiple_price_points
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert result == multiple_price_points

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful deletion by composite key."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        composite_key = (datetime.now(UTC), "DE", EnergyDataType.DAY_AHEAD, "A01")
        result = await repository.delete(composite_key)

        assert result is True
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test deletion when record not found."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        composite_key = (datetime.now(UTC), "DE", EnergyDataType.DAY_AHEAD, "A01")
        result = await repository.delete(composite_key)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_prices_by_time_range_no_filters(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_price_points: list[EnergyPricePoint],
    ) -> None:
        """Test time range query without additional filters."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = multiple_price_points
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        start_time = datetime.now(UTC)
        end_time = datetime.now(UTC)
        result = await repository.get_prices_by_time_range(start_time, end_time)

        assert result == multiple_price_points

    @pytest.mark.asyncio
    async def test_get_prices_by_time_range_with_filters(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_price_points: list[EnergyPricePoint],
    ) -> None:
        """Test time range query with multiple filters."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = multiple_price_points
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        start_time = datetime.now(UTC)
        end_time = datetime.now(UTC)
        result = await repository.get_prices_by_time_range(
            start_time,
            end_time,
            area_codes=["DE", "FR"],
            data_types=[EnergyDataType.DAY_AHEAD],
            currency_units=["EUR"],
            auction_types=["A01"],
            business_types=["A01", "A02"],
        )

        assert result == multiple_price_points

    @pytest.mark.asyncio
    async def test_get_latest_price_for_area_found(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        sample_price_point: EnergyPricePoint,
    ) -> None:
        """Test successful retrieval of latest price for area."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_price_point
        mock_session.execute.return_value = mock_result

        result = await repository.get_latest_price_for_area(
            "DE", EnergyDataType.DAY_AHEAD, "A01"
        )

        assert result == sample_price_point

    @pytest.mark.asyncio
    async def test_get_latest_price_for_area_not_found(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test latest price query when no data found."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_latest_price_for_area(
            "DE", EnergyDataType.DAY_AHEAD, "A01"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_latest_price_for_area_and_type_found(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        sample_price_point: EnergyPricePoint,
    ) -> None:
        """Test successful retrieval of latest price for area and type."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_price_point
        mock_session.execute.return_value = mock_result

        result = await repository.get_latest_price_for_area_and_type(
            "DE", EnergyDataType.DAY_AHEAD
        )

        assert result == sample_price_point

    @pytest.mark.asyncio
    async def test_get_latest_price_for_area_and_type_not_found(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test latest price query by area and type when no data found."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_latest_price_for_area_and_type(
            "DE", EnergyDataType.DAY_AHEAD
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prices_by_currency_success(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_price_points: list[EnergyPricePoint],
    ) -> None:
        """Test successful retrieval of prices by currency."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = multiple_price_points
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_prices_by_currency("EUR")

        assert result == multiple_price_points

    @pytest.mark.asyncio
    async def test_get_prices_by_currency_with_time_range(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_price_points: list[EnergyPricePoint],
    ) -> None:
        """Test currency query with time range filters."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = multiple_price_points
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        start_time = datetime.now(UTC)
        end_time = datetime.now(UTC)
        result = await repository.get_prices_by_currency(
            "EUR", start_time=start_time, end_time=end_time, limit=50
        )

        assert result == multiple_price_points

    @pytest.mark.asyncio
    async def test_get_prices_by_auction_type_success(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_price_points: list[EnergyPricePoint],
    ) -> None:
        """Test successful retrieval of prices by auction type."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = multiple_price_points
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_prices_by_auction_type("A01")

        assert result == multiple_price_points

    @pytest.mark.asyncio
    async def test_get_prices_by_auction_type_with_area_filter(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_price_points: list[EnergyPricePoint],
    ) -> None:
        """Test auction type query with area code filter."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = multiple_price_points
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_prices_by_auction_type(
            "A01", area_codes=["DE", "FR"], limit=50
        )

        assert result == multiple_price_points

    @pytest.mark.asyncio
    async def test_upsert_batch_success(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_price_points: list[EnergyPricePoint],
    ) -> None:
        """Test successful batch upsert operation."""
        setup_session_mock(mock_database, mock_session)

        result = await repository.upsert_batch(multiple_price_points)

        assert result == multiple_price_points
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_batch_empty_list(
        self,
        repository: EnergyPriceRepository,
    ) -> None:
        """Test upsert with empty list returns empty list."""
        result = await repository.upsert_batch([])

        assert result == []

    @pytest.mark.asyncio
    async def test_upsert_batch_database_error(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_price_points: list[EnergyPricePoint],
    ) -> None:
        """Test upsert batch handles database errors properly."""
        setup_session_mock(mock_database, mock_session)

        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DataAccessError, match="Failed to upsert batch"):
            await repository.upsert_batch(multiple_price_points)

        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_time_range_query_database_error(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test time range query handles database errors."""
        setup_session_mock(mock_database, mock_session)

        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        start_time = datetime.now(UTC)
        end_time = datetime.now(UTC)
        with pytest.raises(
            DataAccessError, match="Failed to retrieve energy price points"
        ):
            await repository.get_prices_by_time_range(start_time, end_time)

    @pytest.mark.asyncio
    async def test_currency_query_database_error(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test currency query handles database errors."""
        setup_session_mock(mock_database, mock_session)

        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(
            DataAccessError, match="Failed to retrieve energy price points by currency"
        ):
            await repository.get_prices_by_currency("EUR")

    @pytest.mark.asyncio
    async def test_auction_type_query_database_error(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test auction type query handles database errors."""
        setup_session_mock(mock_database, mock_session)

        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(
            DataAccessError,
            match="Failed to retrieve energy price points by auction type",
        ):
            await repository.get_prices_by_auction_type("A01")

    @pytest.mark.asyncio
    async def test_latest_price_database_error(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test latest price query handles database errors."""
        setup_session_mock(mock_database, mock_session)

        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(
            DataAccessError, match="Failed to retrieve latest energy price point"
        ):
            await repository.get_latest_price_for_area(
                "DE", EnergyDataType.DAY_AHEAD, "A01"
            )

    @pytest.mark.asyncio
    async def test_latest_price_for_area_and_type_database_error(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test latest price for area and type query handles database errors."""
        setup_session_mock(mock_database, mock_session)

        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(
            DataAccessError, match="Failed to retrieve latest energy price point"
        ):
            await repository.get_latest_price_for_area_and_type(
                "DE", EnergyDataType.DAY_AHEAD
            )

    @pytest.mark.asyncio
    async def test_delete_database_error(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test delete handles database errors."""
        setup_session_mock(mock_database, mock_session)

        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        composite_key = (datetime.now(UTC), "DE", EnergyDataType.DAY_AHEAD, "A01")

        with pytest.raises(
            DataAccessError, match="Failed to delete energy price point"
        ):
            await repository.delete(composite_key)

        mock_session.rollback.assert_called_once()

    async def test_delete_invalid_tuple(
        self, repository: EnergyPriceRepository
    ) -> None:
        """Test delete raises ValueError for invalid tuple."""
        invalid_key = ("timestamp_only",)  # Missing required elements

        with pytest.raises(ValueError, match="item_id must be a tuple of"):
            await repository.delete(invalid_key)

    @pytest.mark.asyncio
    async def test_get_by_composite_key_convenience_method(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        sample_price_point: EnergyPricePoint,
    ) -> None:
        """Test convenience method for composite key retrieval."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_price_point
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_composite_key(
            sample_price_point.timestamp,
            sample_price_point.area_code,
            sample_price_point.data_type,
            sample_price_point.business_type,
        )

        assert result == sample_price_point

    @pytest.mark.asyncio
    async def test_delete_by_composite_key_convenience_method(
        self,
        repository: EnergyPriceRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test convenience method for composite key deletion."""
        setup_session_mock(mock_database, mock_session)

        test_timestamp = datetime.now(UTC)
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.delete_by_composite_key(
            test_timestamp, "DE", EnergyDataType.DAY_AHEAD, "A01"
        )

        assert result is True

    def test_get_model_name(self, repository: EnergyPriceRepository) -> None:
        """Test _get_model_name returns correct model name."""
        assert repository._get_model_name() == "EnergyPricePoint"
