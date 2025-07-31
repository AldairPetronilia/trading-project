"""Integration tests for Database class using testcontainers."""

import asyncio
from collections.abc import Generator

import pytest
from app.config.database import Database
from app.config.settings import DatabaseConfig, Settings
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from testcontainers.postgres import PostgresContainer


class TestDatabaseError(Exception):
    """Custom exception for database testing."""


@pytest.fixture
def postgres_container() -> Generator[PostgresContainer]:
    """Fixture that provides a PostgreSQL testcontainer."""
    with PostgresContainer("postgres:16") as postgres:
        yield postgres


@pytest.fixture
def database_config(postgres_container: PostgresContainer) -> DatabaseConfig:
    """Create DatabaseConfig using testcontainer connection details."""
    return DatabaseConfig(
        host=postgres_container.get_container_host_ip(),
        port=postgres_container.get_exposed_port(5432),
        user=postgres_container.username,
        password=postgres_container.password,
        name=postgres_container.dbname,
    )


@pytest.fixture
def settings(database_config: DatabaseConfig) -> Settings:
    """Create Settings with testcontainer database config."""
    from app.config.settings import EntsoEClientConfig
    from pydantic import SecretStr

    return Settings(
        database=database_config,
        debug=True,
        entsoe_client=EntsoEClientConfig(api_token=SecretStr("test_token_1234567890")),
    )


@pytest.fixture
def database(settings: Settings) -> Database:
    """Create Database instance with testcontainer config."""
    return Database(settings)


class TestDatabaseIntegration:
    """Integration tests for Database class with real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_database_engine_creation(self, database: Database) -> None:
        """Test that database engine is created successfully."""
        assert database.engine is not None
        assert database.engine.url.database is not None

    @pytest.mark.asyncio
    async def test_session_factory_creation(self, database: Database) -> None:
        """Test that session factory is created successfully."""
        assert database.session_factory is not None

    @pytest.mark.asyncio
    async def test_database_connection(self, database: Database) -> None:
        """Test actual database connection and query execution."""
        async with database.session_factory() as session:
            result = await session.execute(text("SELECT 1 as test_value"))
            row = result.fetchone()
            assert row is not None
            assert row.test_value == 1

    @pytest.mark.asyncio
    async def test_get_database_session_success(self, database: Database) -> None:
        """Test successful session lifecycle with commit."""
        async for session in database.get_database_session():
            result = await session.execute(text("SELECT version()"))
            version_info = result.fetchone()
            assert version_info is not None
            assert "PostgreSQL" in str(version_info[0])

    @pytest.mark.asyncio
    async def test_get_database_session_rollback_on_exception(
        self,
        database: Database,
    ) -> None:
        """Test that session rolls back on exception."""

        async def _execute_with_rollback() -> None:
            """Helper function to contain the rollback test logic."""
            async for session in database.get_database_session():
                await session.execute(
                    text("CREATE TEMP TABLE test_rollback (id INTEGER)"),
                )
                await session.execute(text("INSERT INTO test_rollback VALUES (1)"))

                result = await session.execute(
                    text("SELECT COUNT(*) FROM test_rollback"),
                )
                count = result.scalar()
                assert count == 1

                error_msg = "Test exception"
                raise TestDatabaseError(error_msg)

        with pytest.raises(TestDatabaseError, match="Test exception"):
            await _execute_with_rollback()

        async with database.session_factory() as new_session:
            with pytest.raises(ProgrammingError, match="relation.*does not exist"):
                await new_session.execute(text("SELECT COUNT(*) FROM test_rollback"))

    @pytest.mark.asyncio
    async def test_database_url_generation(
        self,
        database_config: DatabaseConfig,
    ) -> None:
        """Test that database URL is correctly generated."""
        expected_url = (
            f"postgresql+asyncpg://{database_config.user}:"
            f"{database_config.password.get_secret_value()}@{database_config.host}:"
            f"{database_config.port}/{database_config.name}"
        )
        assert database_config.url == expected_url

    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions(self, database: Database) -> None:
        """Test that multiple sessions can be created concurrently."""

        async def execute_query(session_id: int) -> int:
            async for session in database.get_database_session():
                result = await session.execute(
                    text(f"SELECT {session_id} as session_id"),
                )
                row = result.fetchone()
                if row is not None:
                    return row.session_id
            error_msg = "No session was provided by database.get_database_session()"
            raise RuntimeError(error_msg)

        tasks = [execute_query(i) for i in range(3)]
        results = await asyncio.gather(*tasks)

        assert results == [0, 1, 2]
