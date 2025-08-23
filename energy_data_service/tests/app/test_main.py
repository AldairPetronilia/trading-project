"""Tests for main.py SimpleSchedulerRunner."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import uvicorn
from main import SimpleSchedulerRunner


class TestSimpleSchedulerRunner:
    """Test the SimpleSchedulerRunner class."""

    @pytest.fixture
    def runner(self) -> SimpleSchedulerRunner:
        """Create a SimpleSchedulerRunner instance for testing."""
        return SimpleSchedulerRunner()

    @pytest.fixture
    def mock_container(self) -> MagicMock:
        """Mock container with required services."""
        mock_container = MagicMock()

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.http.host = "0.0.0.0"  # noqa: S104
        mock_settings.http.port = 8000
        mock_settings.http.access_log = True
        mock_settings.logging.level = "INFO"
        mock_container.config.return_value = mock_settings

        return mock_container

    @pytest.fixture
    def mock_scheduler_service(self) -> MagicMock:
        """Mock scheduler service."""
        mock_service = MagicMock()
        mock_start_result = MagicMock()
        mock_start_result.success = True
        mock_service.start = AsyncMock(return_value=mock_start_result)

        mock_stop_result = MagicMock()
        mock_stop_result.success = True
        mock_service.stop = AsyncMock(return_value=mock_stop_result)

        return mock_service

    @pytest.fixture
    def mock_api_server(self) -> MagicMock:
        """Mock uvicorn server."""
        mock_server = MagicMock(spec=uvicorn.Server)
        mock_server.should_exit = False
        return mock_server


class TestApiServerMethods(TestSimpleSchedulerRunner):
    """Test API server related methods."""

    async def test_start_api_server_success(
        self, runner: SimpleSchedulerRunner, mock_container: MagicMock
    ) -> None:
        """Test successful API server startup."""
        runner.container = mock_container

        with (
            patch("main.create_app") as mock_create_app,
            patch("main.uvicorn.Server") as mock_server_class,
            patch("main.uvicorn.Config") as mock_config_class,
            patch("asyncio.create_task") as mock_create_task,
        ):
            mock_app = MagicMock()
            mock_create_app.return_value = mock_app

            mock_config = MagicMock()
            mock_config_class.return_value = mock_config
            mock_config.port = 8000

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server

            # Mock the task creation
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task

            result = await runner._start_api_server()

            # Assertions
            mock_create_app.assert_called_once()
            mock_config_class.assert_called_once()
            mock_server_class.assert_called_once_with(mock_config)
            mock_create_task.assert_called_once_with(mock_server.serve())
            assert result == mock_server
            assert runner.api_task == mock_task

    async def test_start_api_server_exception(
        self, runner: SimpleSchedulerRunner, mock_container: MagicMock
    ) -> None:
        """Test API server startup with exception."""
        runner.container = mock_container

        with (
            patch("main.create_app", side_effect=Exception("Test error")),
            pytest.raises(Exception, match="Test error"),
        ):
            await runner._start_api_server()

    async def test_shutdown_services_success(
        self,
        runner: SimpleSchedulerRunner,
        mock_scheduler_service: MagicMock,
        mock_api_server: MagicMock,
    ) -> None:
        """Test successful shutdown of both services."""
        # Mock api_task as completed
        mock_task = MagicMock()
        mock_task.done.return_value = True
        runner.api_task = mock_task

        await runner._shutdown_services(mock_scheduler_service, mock_api_server)

        # Verify shutdown sequence
        assert mock_api_server.should_exit is True
        mock_scheduler_service.stop.assert_called_once()

    async def test_shutdown_services_without_api_task(
        self,
        runner: SimpleSchedulerRunner,
        mock_scheduler_service: MagicMock,
        mock_api_server: MagicMock,
    ) -> None:
        """Test shutdown when no API task is running."""
        # No api_task attribute set
        await runner._shutdown_services(mock_scheduler_service, mock_api_server)

        # Verify shutdown sequence
        assert mock_api_server.should_exit is True
        mock_scheduler_service.stop.assert_called_once()

    async def test_shutdown_services_basic_flow(
        self,
        runner: SimpleSchedulerRunner,
        mock_scheduler_service: MagicMock,
        mock_api_server: MagicMock,
    ) -> None:
        """Test basic shutdown flow with completed API task."""
        # Mock completed api_task
        mock_task = MagicMock()
        mock_task.done.return_value = True
        runner.api_task = mock_task

        await runner._shutdown_services(mock_scheduler_service, mock_api_server)

        # Verify shutdown sequence
        assert mock_api_server.should_exit is True
        mock_scheduler_service.stop.assert_called_once()
        # Task was completed, so no waiting needed

    async def test_shutdown_services_scheduler_failure(
        self, runner: SimpleSchedulerRunner, mock_api_server: MagicMock
    ) -> None:
        """Test shutdown when scheduler stop fails."""
        mock_scheduler_service = MagicMock()
        mock_stop_result = MagicMock()
        mock_stop_result.success = False
        mock_stop_result.message = "Failed to stop"
        mock_scheduler_service.stop = AsyncMock(return_value=mock_stop_result)

        # Should not raise exception even if scheduler fails to stop
        await runner._shutdown_services(mock_scheduler_service, mock_api_server)

        mock_scheduler_service.stop.assert_called_once()


class TestRunMethod(TestSimpleSchedulerRunner):
    """Test the main run method."""

    async def test_run_successful_startup_and_shutdown(
        self, runner: SimpleSchedulerRunner
    ) -> None:
        """Test successful run with both services starting and stopping."""
        with (
            patch.object(runner, "setup_signal_handlers"),
            patch.object(runner, "_initialize_database") as mock_init_db,
            patch.object(runner, "_validate_api_configuration"),
            patch.object(runner, "_start_scheduler_service") as mock_start_sched,
            patch.object(runner, "_start_api_server") as mock_start_api,
            patch.object(runner, "_perform_startup_tasks"),
            patch.object(runner, "_shutdown_services") as mock_shutdown,
        ):
            # Mock return values
            mock_scheduler = MagicMock()
            mock_api_server = MagicMock()
            mock_start_sched.return_value = mock_scheduler
            mock_start_api.return_value = mock_api_server

            # Mock shutdown event to trigger immediately
            runner.shutdown_event = AsyncMock()
            runner.shutdown_event.wait = AsyncMock()

            await runner.run()

            # Verify startup sequence
            mock_init_db.assert_called_once()
            mock_start_sched.assert_called_once()
            mock_start_api.assert_called_once()

            # Verify shutdown
            mock_shutdown.assert_called_once_with(mock_scheduler, mock_api_server)

    async def test_run_keyboard_interrupt(self, runner: SimpleSchedulerRunner) -> None:
        """Test run method handles KeyboardInterrupt gracefully."""
        with (
            patch.object(runner, "setup_signal_handlers"),
            patch.object(runner, "_initialize_database"),
            patch.object(runner, "_validate_api_configuration"),
            patch.object(runner, "_start_scheduler_service") as mock_start_sched,
            patch.object(runner, "_start_api_server") as mock_start_api,
            patch.object(runner, "_perform_startup_tasks"),
            patch.object(runner, "_shutdown_services") as mock_shutdown,
        ):
            mock_scheduler = MagicMock()
            mock_api_server = MagicMock()
            mock_start_sched.return_value = mock_scheduler
            mock_start_api.return_value = mock_api_server

            # Mock KeyboardInterrupt during wait
            runner.shutdown_event = AsyncMock()
            runner.shutdown_event.wait = AsyncMock(side_effect=KeyboardInterrupt())

            await runner.run()

            # Verify graceful shutdown
            mock_shutdown.assert_called_once_with(mock_scheduler, mock_api_server)

    async def test_run_exception_during_startup(
        self, runner: SimpleSchedulerRunner
    ) -> None:
        """Test run method handles exceptions during startup."""
        with (
            patch.object(runner, "setup_signal_handlers"),
            patch.object(
                runner, "_initialize_database", side_effect=Exception("DB error")
            ),
            patch.object(runner, "_shutdown_services"),
            patch("sys.exit") as mock_exit,
        ):
            await runner.run()

            # Should attempt emergency shutdown and exit
            mock_exit.assert_called_once_with(1)

    async def test_run_partial_startup_failure(
        self, runner: SimpleSchedulerRunner
    ) -> None:
        """Test run method when only one service starts successfully."""
        with (
            patch.object(runner, "setup_signal_handlers"),
            patch.object(runner, "_initialize_database"),
            patch.object(runner, "_validate_api_configuration"),
            patch.object(runner, "_start_scheduler_service") as mock_start_sched,
            patch.object(
                runner,
                "_start_api_server",
                side_effect=Exception("API error"),
            ),
            patch.object(runner, "_shutdown_services"),
            patch("sys.exit") as mock_exit,
        ):
            mock_scheduler = MagicMock()
            mock_start_sched.return_value = mock_scheduler

            await runner.run()

            # Should attempt emergency shutdown and exit
            mock_exit.assert_called_once_with(1)
