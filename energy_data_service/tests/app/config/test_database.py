import contextlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.config.database import Database
from app.config.settings import DatabaseConfig, Settings
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


class TestDatabase:
    """Unit tests for Database class."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        settings = MagicMock(spec=Settings)
        settings.database = MagicMock(spec=DatabaseConfig)
        settings.database.url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
        settings.debug = True
        return settings

    @patch("app.config.database.create_async_engine")
    def test_create_database_engine(
        self,
        mock_create_engine: Any,
        mock_settings: Any,
    ) -> None:
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine

        database = Database(mock_settings)

        mock_create_engine.assert_called_once_with(
            mock_settings.database.url,
            echo=mock_settings.debug,
        )
        assert database.engine == mock_engine

    @patch("app.config.database.async_sessionmaker")
    @patch("app.config.database.create_async_engine")
    def test_create_session_factory(
        self,
        mock_create_engine: Any,
        mock_sessionmaker: Any,
        mock_settings: Any,
    ) -> None:
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine
        mock_factory = MagicMock()
        mock_sessionmaker.return_value = mock_factory

        database = Database(mock_settings)

        mock_sessionmaker.assert_called_once_with(mock_engine, expire_on_commit=False)
        assert database.session_factory == mock_factory

    @pytest.mark.asyncio
    @patch("app.config.database.create_async_engine")
    @patch("app.config.database.async_sessionmaker")
    async def test_get_database_session_success(
        self,
        mock_sessionmaker: Any,
        mock_settings: Any,
    ) -> None:
        """Test that session commits on normal completion."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        mock_factory = MagicMock()
        mock_factory.return_value = mock_context_manager
        mock_sessionmaker.return_value = mock_factory

        database = Database(mock_settings)

        generator = database.get_database_session()
        session = await generator.__anext__()

        assert session == mock_session

        with contextlib.suppress(StopAsyncIteration):
            await generator.__anext__()

        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.config.database.create_async_engine")
    @patch("app.config.database.async_sessionmaker")
    async def test_get_database_session_exception_rollback(
        self,
        mock_sessionmaker: Any,
        mock_settings: Any,
    ) -> None:
        """Test that session rolls back on exception."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        mock_factory = MagicMock()
        mock_factory.return_value = mock_context_manager
        mock_sessionmaker.return_value = mock_factory

        database = Database(mock_settings)

        generator = database.get_database_session()
        session = await generator.__anext__()

        assert session == mock_session

        with pytest.raises(ValueError, match="Test exception"):
            await generator.athrow(ValueError("Test exception"))

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.config.database.create_async_engine")
    @patch("app.config.database.async_sessionmaker")
    async def test_get_database_session_generator_pattern(
        self,
        mock_sessionmaker: Any,
        mock_settings: Any,
    ) -> None:
        """Test async generator yields session correctly."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        mock_factory = MagicMock()
        mock_factory.return_value = mock_context_manager
        mock_sessionmaker.return_value = mock_factory

        database = Database(mock_settings)

        session_generator = database.get_database_session()
        session = await session_generator.__anext__()

        assert session == mock_session

        with contextlib.suppress(StopAsyncIteration):
            await session_generator.__anext__()

    def test_database_initialization_creates_components(
        self,
        mock_settings: Any,
    ) -> None:
        """Test that initialization creates all required components."""
        with (
            patch("app.config.database.create_async_engine") as mock_create_engine,
            patch("app.config.database.async_sessionmaker") as mock_sessionmaker,
        ):
            mock_engine = MagicMock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            mock_factory = MagicMock()
            mock_sessionmaker.return_value = mock_factory

            database = Database(mock_settings)

            assert database.engine == mock_engine
            assert database.session_factory == mock_factory
            assert database.config == mock_settings
