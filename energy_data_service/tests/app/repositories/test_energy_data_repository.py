from datetime import UTC, datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.config.database import Database
from app.exceptions.repository_exceptions import DataAccessError
from app.models.load_data import EnergyDataPoint, EnergyDataType
from app.repositories.energy_data_repository import EnergyDataRepository
from sqlalchemy.exc import SQLAlchemyError


def setup_session_mock(mock_database: Database, mock_session: AsyncMock) -> None:
    """Helper to setup session factory mock properly."""
    async_context_mock = AsyncMock()
    async_context_mock.__aenter__ = AsyncMock(return_value=mock_session)
    async_context_mock.__aexit__ = AsyncMock(return_value=None)
    mock_database.session_factory.return_value = async_context_mock


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
def repository(mock_database: Database) -> EnergyDataRepository:
    """Create an energy data repository instance for testing."""
    return EnergyDataRepository(mock_database)


@pytest.fixture
def sample_energy_data_point() -> EnergyDataPoint:
    """Create a sample energy data point for testing."""
    return EnergyDataPoint(
        timestamp=datetime(2025, 1, 24, 12, 0, tzinfo=UTC),
        area_code="DE_LU",
        data_type=EnergyDataType.ACTUAL,
        business_type="A04",
        quantity=Decimal("1500.123"),
        unit="MAW",
        data_source="entsoe",
        document_mrid="test-doc-mrid",
        revision_number=1,
        document_created_at=datetime(2025, 1, 24, 10, 0, tzinfo=UTC),
        time_series_mrid="test-ts-mrid",
        resolution="PT15M",
        curve_type="A01",
        object_aggregation="A01",
        position=1,
        period_start=datetime(2025, 1, 24, 12, 0, tzinfo=UTC),
        period_end=datetime(2025, 1, 24, 12, 15, tzinfo=UTC),
    )


@pytest.fixture
def multiple_energy_data_points() -> list[EnergyDataPoint]:
    """Create multiple energy data points for batch testing."""
    base_time = datetime(2025, 1, 24, 12, 0, tzinfo=UTC)
    return [
        EnergyDataPoint(
            timestamp=base_time.replace(hour=12 + i),
            area_code="DE_LU",
            data_type=EnergyDataType.ACTUAL,
            business_type="A04",
            quantity=Decimal(f"150{i}.123"),
            unit="MAW",
            data_source="entsoe",
            document_mrid=f"test-doc-mrid-{i}",
            revision_number=1,
            document_created_at=base_time.replace(hour=10),
            time_series_mrid=f"test-ts-mrid-{i}",
            resolution="PT15M",
            curve_type="A01",
            object_aggregation="A01",
            position=1,
            period_start=base_time.replace(hour=12 + i),
            period_end=base_time.replace(hour=12 + i, minute=15),
        )
        for i in range(3)
    ]


class TestEnergyDataRepository:
    """Test suite for EnergyDataRepository class."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        sample_energy_data_point: EnergyDataPoint,
    ) -> None:
        """Test retrieving energy data point by composite primary key - found."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_energy_data_point
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_composite_key(
            timestamp=sample_energy_data_point.timestamp,
            area_code=sample_energy_data_point.area_code,
            data_type=sample_energy_data_point.data_type,
            business_type=sample_energy_data_point.business_type,
        )

        assert result == sample_energy_data_point
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_tuple_signature(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        sample_energy_data_point: EnergyDataPoint,
    ) -> None:
        """Test retrieving energy data point using tuple signature."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_energy_data_point
        mock_session.execute.return_value = mock_result

        composite_key = (
            sample_energy_data_point.timestamp,
            sample_energy_data_point.area_code,
            sample_energy_data_point.data_type,
            sample_energy_data_point.business_type,
        )
        result = await repository.get_by_id(composite_key)

        assert result == sample_energy_data_point
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test retrieving energy data point by composite primary key - not found."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_composite_key(
            timestamp=datetime(2025, 1, 24, 12, 0, tzinfo=UTC),
            area_code="DE_LU",
            data_type=EnergyDataType.ACTUAL,
            business_type="A04",
        )

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_database_error(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test get_by_id with database error."""
        setup_session_mock(mock_database, mock_session)

        mock_session.execute.side_effect = SQLAlchemyError("database error")

        with pytest.raises(DataAccessError) as exc_info:
            await repository.get_by_composite_key(
                timestamp=datetime(2025, 1, 24, 12, 0, tzinfo=UTC),
                area_code="DE_LU",
                data_type=EnergyDataType.ACTUAL,
                business_type="A04",
            )

        assert exc_info.value.model_type == "EnergyDataPoint"
        assert exc_info.value.operation == "get_by_id"
        assert "DE_LU" in str(exc_info.value.context)

    @pytest.mark.asyncio
    async def test_get_all_success(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_energy_data_points: list[EnergyDataPoint],
    ) -> None:
        """Test retrieving all energy data points."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = multiple_energy_data_points
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert result == multiple_energy_data_points
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful deletion by composite primary key."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.delete_by_composite_key(
            timestamp=datetime(2025, 1, 24, 12, 0, tzinfo=UTC),
            area_code="DE_LU",
            data_type=EnergyDataType.ACTUAL,
            business_type="A04",
        )

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test deletion when record not found."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.delete_by_composite_key(
            timestamp=datetime(2025, 1, 24, 12, 0, tzinfo=UTC),
            area_code="DE_LU",
            data_type=EnergyDataType.ACTUAL,
            business_type="A04",
        )

        assert result is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_time_range_no_filters(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_energy_data_points: list[EnergyDataPoint],
    ) -> None:
        """Test time range query without additional filters."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = multiple_energy_data_points
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        start_time = datetime(2025, 1, 24, 10, 0, tzinfo=UTC)
        end_time = datetime(2025, 1, 24, 16, 0, tzinfo=UTC)

        result = await repository.get_by_time_range(start_time, end_time)

        assert result == multiple_energy_data_points
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_time_range_with_filters(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_energy_data_points: list[EnergyDataPoint],
    ) -> None:
        """Test time range query with area, data type, and business type filters."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = multiple_energy_data_points[:1]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        start_time = datetime(2025, 1, 24, 10, 0, tzinfo=UTC)
        end_time = datetime(2025, 1, 24, 16, 0, tzinfo=UTC)

        result = await repository.get_by_time_range(
            start_time=start_time,
            end_time=end_time,
            area_codes=["DE_LU"],
            data_types=[EnergyDataType.ACTUAL],
            business_types=["A04"],
        )

        assert len(result) == 1
        assert result == multiple_energy_data_points[:1]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_area_no_filters(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_energy_data_points: list[EnergyDataPoint],
    ) -> None:
        """Test area query without additional filters."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = multiple_energy_data_points
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_area("DE_LU")

        assert result == multiple_energy_data_points
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_area_with_data_type_and_limit(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_energy_data_points: list[EnergyDataPoint],
    ) -> None:
        """Test area query with data type filter and limit."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = multiple_energy_data_points[:2]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_area(
            area_code="DE_LU",
            data_type=EnergyDataType.ACTUAL,
            limit=2,
        )

        assert len(result) == 2
        assert result == multiple_energy_data_points[:2]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_for_area_found(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        sample_energy_data_point: EnergyDataPoint,
    ) -> None:
        """Test getting latest data point for area - found."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_energy_data_point
        mock_session.execute.return_value = mock_result

        result = await repository.get_latest_for_area(
            area_code="DE_LU",
            data_type=EnergyDataType.ACTUAL,
            business_type="A04",
        )

        assert result == sample_energy_data_point
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_for_area_not_found(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting latest data point for area - not found."""
        setup_session_mock(mock_database, mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_latest_for_area(
            area_code="NONEXISTENT",
            data_type=EnergyDataType.ACTUAL,
            business_type="A04",
        )

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_batch_success(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_energy_data_points: list[EnergyDataPoint],
    ) -> None:
        """Test successful batch upsert operation."""
        setup_session_mock(mock_database, mock_session)

        result = await repository.upsert_batch(multiple_energy_data_points)

        assert result == multiple_energy_data_points
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_batch_empty_list(
        self,
        repository: EnergyDataRepository,
    ) -> None:
        """Test batch upsert with empty list."""
        result = await repository.upsert_batch([])
        assert result == []

    @pytest.mark.asyncio
    async def test_upsert_batch_database_error(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
        multiple_energy_data_points: list[EnergyDataPoint],
    ) -> None:
        """Test batch upsert with database error."""
        setup_session_mock(mock_database, mock_session)

        mock_session.execute.side_effect = SQLAlchemyError("database error")

        with pytest.raises(DataAccessError) as exc_info:
            await repository.upsert_batch(multiple_energy_data_points)

        assert exc_info.value.model_type == "EnergyDataPoint"
        assert exc_info.value.operation == "upsert_batch"
        assert exc_info.value.context["batch_size"] == 3
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_time_range_query_database_error(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test time range query with database error."""
        setup_session_mock(mock_database, mock_session)

        mock_session.execute.side_effect = SQLAlchemyError("database error")

        start_time = datetime(2025, 1, 24, 10, 0, tzinfo=UTC)
        end_time = datetime(2025, 1, 24, 16, 0, tzinfo=UTC)

        with pytest.raises(DataAccessError) as exc_info:
            await repository.get_by_time_range(start_time, end_time)

        assert exc_info.value.model_type == "EnergyDataPoint"
        assert exc_info.value.operation == "get_by_time_range"
        assert "start_time" in str(exc_info.value.context)
        assert "end_time" in str(exc_info.value.context)

    @pytest.mark.asyncio
    async def test_get_model_name(self, repository: EnergyDataRepository) -> None:
        """Test model name retrieval."""
        assert repository._get_model_name() == "EnergyDataPoint"

    @pytest.mark.asyncio
    async def test_delete_database_error(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test delete with database error."""
        setup_session_mock(mock_database, mock_session)

        mock_session.execute.side_effect = SQLAlchemyError("database error")

        with pytest.raises(DataAccessError) as exc_info:
            await repository.delete_by_composite_key(
                timestamp=datetime(2025, 1, 24, 12, 0, tzinfo=UTC),
                area_code="DE_LU",
                data_type=EnergyDataType.ACTUAL,
                business_type="A04",
            )

        assert exc_info.value.model_type == "EnergyDataPoint"
        assert exc_info.value.operation == "delete"
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_area_database_error(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test get_by_area with database error."""
        setup_session_mock(mock_database, mock_session)

        mock_session.execute.side_effect = SQLAlchemyError("database error")

        with pytest.raises(DataAccessError) as exc_info:
            await repository.get_by_area("DE_LU")

        assert exc_info.value.model_type == "EnergyDataPoint"
        assert exc_info.value.operation == "get_by_area"
        assert exc_info.value.context["area_code"] == "DE_LU"

    @pytest.mark.asyncio
    async def test_get_latest_for_area_database_error(
        self,
        repository: EnergyDataRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test get_latest_for_area with database error."""
        setup_session_mock(mock_database, mock_session)

        mock_session.execute.side_effect = SQLAlchemyError("database error")

        with pytest.raises(DataAccessError) as exc_info:
            await repository.get_latest_for_area(
                area_code="DE_LU",
                data_type=EnergyDataType.ACTUAL,
                business_type="A04",
            )

        assert exc_info.value.model_type == "EnergyDataPoint"
        assert exc_info.value.operation == "get_latest_for_area"
        assert exc_info.value.context["area_code"] == "DE_LU"
