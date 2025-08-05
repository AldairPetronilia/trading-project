from typing import TYPE_CHECKING

from app.collectors.entsoe_collector import EntsoeCollector
from app.config.database import Database
from app.config.settings import BackfillConfig, Settings
from app.processors.gl_market_document_processor import GlMarketDocumentProcessor
from app.repositories.backfill_progress_repository import BackfillProgressRepository
from app.repositories.energy_data_repository import EnergyDataRepository
from app.services.backfill_service import BackfillService
from app.services.entsoe_data_service import EntsoEDataService
from app.services.scheduler_service import SchedulerService
from dependency_injector import containers, providers

if TYPE_CHECKING:
    from app.config.settings import EntsoEDataCollectionConfig

from entsoe_client.client.entsoe_client import EntsoEClient
from entsoe_client.client.entsoe_client_factory import EntsoEClientFactory


def _create_entsoe_client(config: Settings) -> EntsoEClient:
    """Wrapper function to create EntsoE client with secret token extraction."""
    api_token = config.entsoe_client.api_token.get_secret_value()
    return EntsoEClientFactory.create_client(api_token)


class Container(containers.DeclarativeContainer):
    """Main DI container for Energy-Data-Service client."""

    config: providers.Singleton[Settings] = providers.Singleton(Settings)

    database: providers.Singleton[Database] = providers.Singleton(
        Database, config=config
    )

    entsoe_client: providers.Factory[EntsoEClient] = providers.Factory(
        _create_entsoe_client, config=config
    )

    entsoe_collector: providers.Factory[EntsoeCollector] = providers.Factory(
        EntsoeCollector,
        entsoe_client=entsoe_client,
    )

    energy_data_repository: providers.Factory[EnergyDataRepository] = providers.Factory(
        EnergyDataRepository,
        database=database,
    )

    backfill_progress_repository: providers.Factory[BackfillProgressRepository] = (
        providers.Factory(
            BackfillProgressRepository,
            database=database,
        )
    )

    gl_market_document_processor: providers.Factory[GlMarketDocumentProcessor] = (
        providers.Factory(
            GlMarketDocumentProcessor,
        )
    )

    entsoe_data_service: providers.Factory[EntsoEDataService] = providers.Factory(
        EntsoEDataService,
        collector=entsoe_collector,
        processor=gl_market_document_processor,
        repository=energy_data_repository,
        entsoe_data_collection_config=providers.Callable(
            lambda c: c.entsoe_data_collection, config
        ),
    )

    backfill_service: providers.Factory[BackfillService] = providers.Factory(
        BackfillService,
        collector=entsoe_collector,
        processor=gl_market_document_processor,
        repository=energy_data_repository,
        database=database,
        config=providers.Callable(lambda c: c.backfill, config),
        progress_repository=backfill_progress_repository,
        entsoe_data_collection_config=providers.Callable(
            lambda c: c.entsoe_data_collection, config
        ),
    )

    scheduler_service: providers.Factory[SchedulerService] = providers.Factory(
        SchedulerService,
        entsoe_data_service=entsoe_data_service,
        backfill_service=backfill_service,
        database=database,
        config=providers.Callable(lambda c: c.scheduler, config),
    )
