import os
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from app.collectors.entsoe_collector import EntsoeCollector
from app.config.database import Database
from app.config.settings import Settings
from app.container import Container
from app.processors.gl_market_document_processor import GlMarketDocumentProcessor
from app.processors.publication_market_document_processor import (
    PublicationMarketDocumentProcessor,
)
from app.repositories.backfill_progress_repository import BackfillProgressRepository
from app.repositories.energy_data_repository import EnergyDataRepository
from app.repositories.energy_price_repository import EnergyPriceRepository
from app.services.entsoe_data_service import EntsoEDataService


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
        assert hasattr(container, "energy_price_repository")
        assert hasattr(container, "backfill_progress_repository")
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
    def test_energy_price_repository_provider_creation(self) -> None:
        """Test that energy price repository provider creates repository instance."""
        container = Container()

        repository = container.energy_price_repository()

        assert isinstance(repository, EnergyPriceRepository)
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
    def test_publication_market_document_processor_provider_creation(self) -> None:
        """Test that PublicationMarketDocumentProcessor can be resolved from the container."""
        container = Container()

        processor = container.publication_market_document_processor()

        assert isinstance(processor, PublicationMarketDocumentProcessor)

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
        price_repository = container.energy_price_repository()
        processor = container.gl_market_document_processor()
        price_processor = container.publication_market_document_processor()
        service = container.entsoe_data_service()

        # Basic type checks
        assert isinstance(config, Settings)
        assert isinstance(database, Database)
        assert isinstance(repository, EnergyDataRepository)
        assert isinstance(price_repository, EnergyPriceRepository)
        assert isinstance(processor, GlMarketDocumentProcessor)
        assert isinstance(price_processor, PublicationMarketDocumentProcessor)
        assert isinstance(service, EntsoEDataService)

        # Verify dependency relationships
        assert database.config is config
        assert repository.database is database
        assert price_repository.database is database

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    def test_backfill_progress_repository_provider_creation(self) -> None:
        """Test that backfill progress repository provider creates repository instance."""
        container = Container()

        repository = container.backfill_progress_repository()

        assert isinstance(repository, BackfillProgressRepository)
        assert repository.database is container.database()

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    def test_backfill_progress_repository_dependency_injection(self) -> None:
        """Test that backfill progress repository receives proper database dependency."""
        container = Container()

        # Get instances
        database = container.database()
        repository = container.backfill_progress_repository()

        # Verify repository received the same database instance
        assert repository.database is database

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    def test_repository_providers_independence(self) -> None:
        """Test that different repository providers are independent but share database."""
        container = Container()

        # Get instances
        database = container.database()
        energy_repository = container.energy_data_repository()
        price_repository = container.energy_price_repository()
        progress_repository = container.backfill_progress_repository()

        # Verify they are different instances
        assert energy_repository is not progress_repository
        assert energy_repository is not price_repository
        assert price_repository is not progress_repository

        # But they share the same database instance
        assert energy_repository.database is database
        assert price_repository.database is database
        assert progress_repository.database is database

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    def test_backfill_service_provider_with_progress_repository(self) -> None:
        """Test that backfill service provider includes progress repository dependency."""
        container = Container()

        # Get backfill service (which should have progress repository injected)
        backfill_service = container.backfill_service()

        # Verify service has progress repository
        assert hasattr(backfill_service, "_progress_repository")
        assert isinstance(
            backfill_service._progress_repository, BackfillProgressRepository
        )

        # Verify the repository has the same database as other providers
        assert backfill_service._progress_repository.database is container.database()

    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "test_token_1234567890"})
    def test_all_providers_resolution_including_progress_repository(self) -> None:
        """Test that all providers including new progress repository can be resolved."""
        container = Container()

        # Verify all providers can be instantiated
        config = container.config()
        database = container.database()
        energy_repository = container.energy_data_repository()
        progress_repository = container.backfill_progress_repository()
        processor = container.gl_market_document_processor()

        # Basic type checks
        assert isinstance(config, Settings)
        assert isinstance(database, Database)
        assert isinstance(energy_repository, EnergyDataRepository)
        assert isinstance(progress_repository, BackfillProgressRepository)
        assert isinstance(processor, GlMarketDocumentProcessor)

        # Verify dependency relationships
        assert database.config is config
        assert energy_repository.database is database
        assert progress_repository.database is database
