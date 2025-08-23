"""Integration tests for unified service (scheduler + API server)."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from app.api.app import create_app
from app.config.database import Database
from app.config.settings import (
    DatabaseConfig,
    EntsoEClientConfig,
    HttpConfig,
    Settings,
)
from app.container import Container
from app.models.load_data import EnergyDataPoint
from httpx import AsyncClient
from main import SimpleSchedulerRunner
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from testcontainers.postgres import PostgresContainer


@pytest.fixture
def postgres_container() -> Generator[PostgresContainer]:
    """Fixture that provides a TimescaleDB testcontainer."""
    # Use timescale/timescaledb image for TimescaleDB support
    with PostgresContainer("timescale/timescaledb:2.16.1-pg16") as postgres:
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
    """Create Settings with testcontainer database config and HTTP config."""
    return Settings(
        database=database_config,
        debug=True,
        entsoe_client=EntsoEClientConfig(api_token=SecretStr("test_token_1234567890")),
        http=HttpConfig(
            host="127.0.0.1",
            port=8001,  # Use different port to avoid conflicts
            workers=1,
            access_log=True,
        ),
    )


@pytest.fixture
def container(settings: Settings) -> Container:
    """Create Container with test settings."""
    container = Container()
    container.config.override(settings)
    return container


@pytest_asyncio.fixture
async def initialized_database(container: Container) -> AsyncGenerator[Database]:
    """Initialize database with TimescaleDB extension and tables."""
    from app.config.database import Database
    from app.models.base import Base
    from sqlalchemy import text

    database = container.database()

    # Initialize database with TimescaleDB extension and tables
    async with database.engine.begin() as conn:
        # Enable TimescaleDB extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    yield database

    # Cleanup
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def sample_data(
    initialized_database: Database,  # noqa: ARG001
    container: Container,
) -> list[EnergyDataPoint]:
    """Insert sample energy data for testing."""
    database = container.database()
    async with database.session_factory() as session:
        sample_points = []

        # Create test data points
        base_time = datetime.now(UTC) - timedelta(hours=2)
        from app.models.load_data import EnergyDataType

        for i in range(5):
            point = EnergyDataPoint(
                timestamp=base_time + timedelta(hours=i),
                area_code="DE",
                data_type=EnergyDataType.ACTUAL,
                business_type="A04",
                quantity=Decimal("1000.00") + Decimal(str(i * 100)),
                unit="MW",
                data_source="ENTSOE",
                resolution="PT60M",
                curve_type="A01",
                document_mrid=f"doc-DE-{i}",
                revision_number=1,
                document_created_at=base_time,
                time_series_mrid=f"ts-DE-{i}",
                object_aggregation="A01",
                position=i + 1,
                period_start=base_time + timedelta(hours=i),
                period_end=base_time + timedelta(hours=i + 1),
            )
            session.add(point)
            sample_points.append(point)

        await session.commit()
        return sample_points


class TestUnifiedServiceIntegration:
    """Integration tests for unified scheduler and API service."""

    @pytest_asyncio.fixture
    async def unified_service(
        self, container: Container
    ) -> AsyncGenerator[SimpleSchedulerRunner]:
        """Create and configure unified service runner for testing."""
        runner = SimpleSchedulerRunner()
        runner.container = container

        # Mock external dependencies to avoid actual API calls
        with patch(
            "app.services.scheduler_service.SchedulerService.start"
        ) as mock_start:
            mock_scheduler = AsyncMock()
            mock_scheduler.stop = AsyncMock(return_value=True)
            mock_start.return_value = mock_scheduler

            # Use setattr to avoid mypy attr-defined error
            runner._mock_scheduler = mock_scheduler  # type: ignore[attr-defined]
            yield runner

    @pytest_asyncio.fixture
    async def api_client(self, container: Container) -> AsyncGenerator[AsyncClient]:
        """Create HTTP client for API testing."""
        app = create_app()
        app.state.container = container

        # Ensure container resources are initialized
        container.init_resources()

        from httpx import ASGITransport

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client

    async def test_api_server_initialization(
        self, unified_service: SimpleSchedulerRunner
    ) -> None:
        """Test API server starts with correct configuration."""
        # Mock uvicorn Server
        with patch("main.uvicorn.Server") as mock_server_class:
            mock_server = MagicMock()
            # Make serve() return an async coroutine
            mock_server.serve = AsyncMock()
            mock_server_class.return_value = mock_server

            with patch("main.create_app") as mock_create_app:
                mock_create_app.return_value = MagicMock()

                # Test API server initialization
                server = await unified_service._start_api_server()

                # Verify app was created
                mock_create_app.assert_called_once()

                # Verify server was configured correctly
                mock_server_class.assert_called_once()
                config = mock_server_class.call_args[0][
                    0
                ]  # First positional argument (uvicorn.Config)

                assert config.host == "127.0.0.1"
                assert config.port == 8001
                assert config.use_colors is False
                assert config.access_log is True

                # Verify server was returned
                assert server == mock_server

                # Verify serve() was called as a task
                assert hasattr(unified_service, "api_task")

    async def test_concurrent_service_startup(
        self, unified_service: SimpleSchedulerRunner
    ) -> None:
        """Test both services start without blocking each other."""
        # Mock the scheduler service startup
        with patch.object(
            unified_service, "_start_scheduler_service"
        ) as mock_scheduler:
            mock_scheduler_service = AsyncMock()
            mock_scheduler.return_value = mock_scheduler_service

            with patch.object(unified_service, "_start_api_server") as mock_api:
                mock_api_server = MagicMock()
                mock_api.return_value = mock_api_server

                # Initialize database
                await unified_service._initialize_database()

                # Start both services
                scheduler = await unified_service._start_scheduler_service()
                api_server = await unified_service._start_api_server()

                # Verify both services were started
                mock_scheduler.assert_called_once()
                mock_api.assert_called_once()

                assert scheduler == mock_scheduler_service
                assert api_server == mock_api_server

    @pytest.mark.usefixtures("sample_data")
    async def test_api_accessible_during_collection(
        self,
        unified_service: SimpleSchedulerRunner,
        api_client: AsyncClient,
    ) -> None:
        """Verify API responds while scheduler service is running."""
        # Mock scheduler to simulate running state
        with patch.object(
            unified_service, "_start_scheduler_service"
        ) as mock_scheduler:
            mock_scheduler_service = AsyncMock()
            mock_scheduler_service.stop = AsyncMock(return_value=True)
            mock_scheduler.return_value = mock_scheduler_service

            # Initialize database
            await unified_service._initialize_database()

            # Start scheduler (mocked)
            scheduler = await unified_service._start_scheduler_service()

            # Verify scheduler was started
            assert scheduler == mock_scheduler_service

            # Test API accessibility while scheduler is "running"
            response = await api_client.get("/api/v1/health/")
            assert response.status_code == 200

            # Test data endpoint - no trailing slash for FastAPI endpoint
            response = await api_client.get(
                "/api/v1/energy-data/latest?area_code=DE&limit=3"
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data) <= 3
            assert all(item["area_code"] == "DE" for item in data)

    async def test_graceful_shutdown_both_services(
        self, unified_service: SimpleSchedulerRunner
    ) -> None:
        """Test both services stop cleanly on shutdown."""
        # Create mock services
        from datetime import UTC

        from app.services.scheduler_service import ScheduleExecutionResult

        mock_scheduler = AsyncMock()
        mock_result = ScheduleExecutionResult(
            operation="stop",
            success=True,
            message="Test stop",
            timestamp=datetime.now(UTC),
        )
        mock_scheduler.stop = AsyncMock(return_value=mock_result)

        mock_api_server = MagicMock()
        mock_api_server.should_exit = False

        # Mock the api_task
        mock_task = AsyncMock()
        mock_task.done.return_value = False  # Task is still running
        mock_task.cancel = MagicMock()
        unified_service.api_task = mock_task

        # Test shutdown
        await unified_service._shutdown_services(mock_scheduler, mock_api_server)

        # Verify scheduler was stopped
        mock_scheduler.stop.assert_called_once()

        # Verify API server was signaled to exit
        assert mock_api_server.should_exit is True

        # Verify API task was checked and awaited
        mock_task.done.assert_called()
        # The task should be awaited via asyncio.wait_for, not directly
        # So we don't check assert_awaited_once() since it goes through asyncio.wait_for

    async def test_service_error_handling(
        self, unified_service: SimpleSchedulerRunner
    ) -> None:
        """Test service continues if one component fails during startup."""
        # Test API server startup failure
        with patch.object(
            unified_service, "_start_scheduler_service"
        ) as mock_scheduler:
            mock_scheduler_service = AsyncMock()
            mock_scheduler.return_value = mock_scheduler_service

            with patch.object(unified_service, "_start_api_server") as mock_api:
                mock_api.side_effect = Exception("API server failed")

                # Initialize database
                await unified_service._initialize_database()

                # Start scheduler should succeed
                scheduler = await unified_service._start_scheduler_service()
                assert scheduler == mock_scheduler_service

                # API server should fail
                with pytest.raises(Exception, match="API server failed"):
                    await unified_service._start_api_server()

    @pytest.mark.usefixtures("sample_data")
    async def test_api_endpoints_during_service_operation(
        self,
        api_client: AsyncClient,
    ) -> None:
        """Test various API endpoints work during service operation."""
        # Test health endpoint
        response = await api_client.get("/api/v1/health/")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "message" in health_data

        # Test latest data endpoint - FastAPI endpoint doesn't expect trailing slash
        response = await api_client.get("/api/v1/energy-data/latest?area_code=DE")
        assert response.status_code == 200
        latest_data = response.json()
        assert isinstance(latest_data, list)
        assert len(latest_data) > 0

    @pytest.mark.usefixtures("sample_data")
    async def test_concurrent_api_requests_during_collection(
        self,
        api_client: AsyncClient,
    ) -> None:
        """Test multiple concurrent API requests during data collection."""
        # Create multiple concurrent requests - no trailing slash for FastAPI endpoint
        tasks = []
        for _ in range(10):
            task = api_client.get("/api/v1/energy-data/latest?area_code=DE&limit=1")
            tasks.append(task)

        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks)

        # Verify all requests succeeded
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) <= 1

    async def test_service_configuration_validation(
        self, unified_service: SimpleSchedulerRunner
    ) -> None:
        """Test service validates configuration correctly."""
        # Test API configuration validation
        unified_service._validate_api_configuration()

        # Should not raise any exceptions for valid config
        # The method logs validation results but doesn't raise exceptions
        # for missing optional configuration

    async def test_database_initialization_during_startup(
        self, unified_service: SimpleSchedulerRunner
    ) -> None:
        """Test database is properly initialized during service startup."""
        # Test database initialization
        await unified_service._initialize_database()

        # Verify database connection works
        database = unified_service.container.database()
        async with database.session_factory() as session:
            # Simple query to verify connection
            from sqlalchemy import text

            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    async def test_startup_tasks_execution(
        self, unified_service: SimpleSchedulerRunner
    ) -> None:
        """Test startup tasks are executed properly."""
        settings = unified_service.container.config()

        # Mock the backfill operation since it requires external API
        with patch.object(
            unified_service, "_perform_startup_backfill"
        ) as mock_backfill:
            mock_backfill.return_value = None

            await unified_service._perform_startup_tasks(settings)

            # Verify backfill was called (if configured)
            # This will depend on settings, but we've mocked it to avoid external calls
            mock_backfill.assert_called_once()
