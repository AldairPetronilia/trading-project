import os
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from app.collectors.entsoe_collector import EntsoeCollector
from app.config.database import Database
from app.config.settings import Settings
from app.container import Container
from app.processors.gl_market_document_processor import GlMarketDocumentProcessor
from app.repositories.energy_data_repository import EnergyDataRepository


@pytest.fixture(autouse=True)
def reset_container_state() -> Generator:
    """Reset container state before and after each test for proper isolation."""
    # Create a fresh container instance for each test
    yield
    # Reset any singleton providers after each test
    try:
        # Reset the singleton providers to ensure clean state
        if hasattr(Container, "_singletons"):
            Container._singletons.clear()
    except AttributeError:
        pass  # Container might not have this attribute in all versions


class TestContainer:
    """Test suite for dependency injection container."""

    def test_container_providers_registered(self) -> None:
        """Test that all providers are properly registered."""
        container = Container()

        # Check that providers exist
        assert hasattr(container, "config")
        assert hasattr(container, "database")
        assert hasattr(container, "entsoe_client")
        assert hasattr(container, "entsoe_collector")
        assert hasattr(container, "energy_data_repository")
        assert hasattr(container, "gl_market_document_processor")

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    def test_config_provider_creation(self) -> None:
        """Test that config provider creates Settings instance."""
        container = Container()

        settings = container.config()

        assert isinstance(settings, Settings)
        assert (
            settings.entsoe_client.api_token.get_secret_value()
            == "test_token_1234567890"
        )

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    def test_database_provider_creation(self) -> None:
        """Test that database provider creates Database instance."""
        container = Container()

        database = container.database()

        assert isinstance(database, Database)
        assert (
            database.config.entsoe_client.api_token.get_secret_value()
            == "test_token_1234567890"
        )

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    @patch("app.container.EntsoEClientFactory.create_client")
    def test_entsoe_client_provider_creation(
        self,
        mock_create_client: AsyncMock,
    ) -> None:
        """Test that EntsoE client provider calls factory with correct token."""
        mock_client = AsyncMock()
        mock_create_client.return_value = mock_client

        container = Container()

        client = container.entsoe_client()

        # Verify factory was called with the secret value
        mock_create_client.assert_called_once_with("test_token_1234567890")
        assert client == mock_client

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    def test_container_dependency_injection(self) -> None:
        """Test that dependencies are properly injected between providers."""
        container = Container()

        # Get instances
        settings = container.config()
        database = container.database()

        # Verify database received the same config instance
        assert database.config is settings

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "short"})
    def test_container_with_invalid_config(self) -> None:
        """Test container behavior with invalid configuration."""
        container = Container()

        with pytest.raises(ValueError, match="API token must be at least"):
            container.config()

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    def test_energy_data_repository_provider_creation(self) -> None:
        """Test that energy data repository provider creates repository instance."""
        container = Container()

        repository = container.energy_data_repository()

        assert isinstance(repository, EnergyDataRepository)
        assert repository.database is container.database()

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    def test_repository_dependency_injection(self) -> None:
        """Test that repository receives proper database dependency."""
        container = Container()

        # Get instances
        database = container.database()
        repository = container.energy_data_repository()

        # Verify repository received the same database instance
        assert repository.database is database

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    @patch("app.container.EntsoEClientFactory.create_client")
    def test_entsoe_collector_provider_creation(
        self,
        mock_create_client: AsyncMock,
    ) -> None:
        """Test that entsoe collector provider creates collector instance."""
        mock_client = AsyncMock()
        mock_create_client.return_value = mock_client

        container = Container()

        collector = container.entsoe_collector()

        assert isinstance(collector, EntsoeCollector)
        assert collector._client == mock_client

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    @patch("app.container.EntsoEClientFactory.create_client")
    def test_collector_dependency_injection(
        self,
        mock_create_client: AsyncMock,
    ) -> None:
        """Test that collector receives proper entsoe_client dependency."""
        mock_client = AsyncMock()
        mock_create_client.return_value = mock_client

        container = Container()

        # Get instances
        client = container.entsoe_client()
        collector = container.entsoe_collector()

        # Verify collector received the same client instance
        assert collector._client is client

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    def test_gl_market_document_processor_provider_creation(self) -> None:
        """Test that GL_MarketDocument processor provider creates processor instance."""
        container = Container()

        processor = container.gl_market_document_processor()

        assert isinstance(processor, GlMarketDocumentProcessor)

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    def test_processor_no_dependencies(self) -> None:
        """Test that processor is created without external dependencies."""
        container = Container()

        # Processor should be stateless and not require dependencies
        processor1 = container.gl_market_document_processor()
        processor2 = container.gl_market_document_processor()

        # Should create new instances (Factory provider)
        assert isinstance(processor1, GlMarketDocumentProcessor)
        assert isinstance(processor2, GlMarketDocumentProcessor)
        # Factory provider creates new instances each time
        assert processor1 is not processor2

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    def test_all_providers_resolution(self) -> None:
        """Test that all providers can be resolved without errors."""
        container = Container()

        # Verify all providers can be instantiated
        config = container.config()
        database = container.database()
        repository = container.energy_data_repository()
        processor = container.gl_market_document_processor()

        # Basic type checks
        assert isinstance(config, Settings)
        assert isinstance(database, Database)
        assert isinstance(repository, EnergyDataRepository)
        assert isinstance(processor, GlMarketDocumentProcessor)

        # Verify dependency relationships
        assert database.config is config
        assert repository.database is database
