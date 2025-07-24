from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.config.database import Database
from app.exceptions.repository_exceptions import (
    DataAccessError,
    DataValidationError,
    DuplicateDataError,
)
from app.repositories.base_repository import BaseRepository
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


class MockModel:
    """Mock model for testing base repository functionality."""

    def __init__(self, model_id: int, name: str) -> None:
        self.id = model_id
        self.name = name


class ConcreteRepository(BaseRepository[MockModel]):
    """Concrete implementation of BaseRepository for testing."""

    async def get_by_id(self, item_id: Any) -> MockModel | None:
        """Mock implementation of get_by_id."""
        async with self.database.session_factory() as _session:
            if item_id == 1:
                return MockModel(1, "test")
            return None

    async def get_all(self) -> list[MockModel]:
        """Mock implementation of get_all."""
        async with self.database.session_factory() as _session:
            return [MockModel(1, "test1"), MockModel(2, "test2")]

    async def delete(self, item_id: Any) -> bool:
        """Mock implementation of delete."""
        async with self.database.session_factory() as _session:
            return item_id == 1

    def _get_model_name(self) -> str:
        """Return model name for error reporting."""
        return "MockModel"


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
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.merge = AsyncMock()
    session.add_all = MagicMock()
    return session


@pytest.fixture
def repository(mock_database: Database) -> ConcreteRepository:
    """Create a concrete repository instance for testing."""
    return ConcreteRepository(mock_database)


class TestBaseRepository:
    """Test suite for BaseRepository abstract class."""

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        repository: ConcreteRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful model creation."""
        setup_session_mock(mock_database, mock_session)

        model = MockModel(1, "test")

        result = await repository.create(model)

        assert result == model
        mock_session.add.assert_called_once_with(model)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(model)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_error(
        self,
        repository: ConcreteRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test creation with duplicate data error."""
        setup_session_mock(mock_database, mock_session)

        integrity_error = IntegrityError("unique constraint", None, None)
        integrity_error.orig = MagicMock()
        integrity_error.orig.pgcode = "23505"
        mock_session.flush.side_effect = integrity_error

        model = MockModel(1, "test")

        with pytest.raises(DuplicateDataError) as exc_info:
            await repository.create(model)

        assert exc_info.value.model_type == "MockModel"
        assert exc_info.value.operation == "create"
        assert exc_info.value.context["error_code"] == "23505"
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_database_error(
        self,
        repository: ConcreteRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test creation with database error."""
        setup_session_mock(mock_database, mock_session)

        mock_session.flush.side_effect = SQLAlchemyError("database error")

        model = MockModel(1, "test")

        with pytest.raises(DataAccessError) as exc_info:
            await repository.create(model)

        assert exc_info.value.model_type == "MockModel"
        assert exc_info.value.operation == "create"
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_validation_error(
        self,
        repository: ConcreteRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test creation with validation error."""
        setup_session_mock(mock_database, mock_session)

        mock_session.flush.side_effect = ValueError("validation error")

        model = MockModel(1, "test")

        with pytest.raises(DataValidationError) as exc_info:
            await repository.create(model)

        assert exc_info.value.model_type == "MockModel"
        assert exc_info.value.operation == "create"
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        repository: ConcreteRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful model update."""
        setup_session_mock(mock_database, mock_session)

        model = MockModel(1, "updated")
        merged_model = MockModel(1, "updated")
        mock_session.merge.return_value = merged_model

        result = await repository.update(model)

        assert result == merged_model
        mock_session.merge.assert_called_once_with(model)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(merged_model)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_duplicate_error(
        self,
        repository: ConcreteRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test update with duplicate data error."""
        setup_session_mock(mock_database, mock_session)

        integrity_error = IntegrityError("unique constraint", None, None)
        integrity_error.orig = MagicMock()
        integrity_error.orig.pgcode = "23505"
        mock_session.flush.side_effect = integrity_error

        model = MockModel(1, "updated")
        mock_session.merge.return_value = model

        with pytest.raises(DuplicateDataError) as exc_info:
            await repository.update(model)

        assert exc_info.value.model_type == "MockModel"
        assert exc_info.value.operation == "update"
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_batch_success(
        self,
        repository: ConcreteRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful batch creation."""
        setup_session_mock(mock_database, mock_session)

        models = [MockModel(1, "test1"), MockModel(2, "test2")]

        result = await repository.create_batch(models)

        assert result == models
        mock_session.add_all.assert_called_once_with(models)
        mock_session.flush.assert_called_once()
        assert mock_session.refresh.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_batch_empty_list(
        self,
        repository: ConcreteRepository,
    ) -> None:
        """Test batch creation with empty list."""
        result = await repository.create_batch([])
        assert result == []

    @pytest.mark.asyncio
    async def test_create_batch_duplicate_error(
        self,
        repository: ConcreteRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test batch creation with duplicate data error."""
        setup_session_mock(mock_database, mock_session)

        integrity_error = IntegrityError("unique constraint", None, None)
        integrity_error.orig = MagicMock()
        integrity_error.orig.pgcode = "23505"
        mock_session.flush.side_effect = integrity_error

        models = [MockModel(1, "test1"), MockModel(2, "test2")]

        with pytest.raises(DuplicateDataError) as exc_info:
            await repository.create_batch(models)

        assert exc_info.value.model_type == "MockModel"
        assert exc_info.value.operation == "create_batch"
        assert exc_info.value.context["batch_size"] == 2
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_batch_success(
        self,
        repository: ConcreteRepository,
        mock_database: Database,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful batch update."""
        setup_session_mock(mock_database, mock_session)

        models = [MockModel(1, "updated1"), MockModel(2, "updated2")]
        merged_models = [MockModel(1, "updated1"), MockModel(2, "updated2")]

        mock_session.merge.side_effect = merged_models

        result = await repository.update_batch(models)

        assert result == merged_models
        assert mock_session.merge.call_count == 2
        mock_session.flush.assert_called_once()
        assert mock_session.refresh.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_batch_empty_list(
        self,
        repository: ConcreteRepository,
    ) -> None:
        """Test batch update with empty list."""
        result = await repository.update_batch([])
        assert result == []

    @pytest.mark.asyncio
    async def test_get_model_name(self, repository: ConcreteRepository) -> None:
        """Test model name retrieval."""
        assert repository._get_model_name() == "MockModel"
