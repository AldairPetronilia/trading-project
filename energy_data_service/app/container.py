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

from entsoe_client.client.entsoe_client import EntsoEClient
from entsoe_client.client.entsoe_client_factory import EntsoEClientFactory


def _create_entsoe_client(config: Settings) -> EntsoEClient:
    """Wrapper function to create EntsoE client with secret token extraction."""
    api_token = config.entsoe_client.api_token.get_secret_value()
    return EntsoEClientFactory.create_client(api_token)


class Container(containers.DeclarativeContainer):
    """Main DI container for Energy-Data-Service client."""

    config = providers.Singleton(Settings)

    database = providers.Singleton(Database, config=config)

    entsoe_client = providers.Factory(_create_entsoe_client, config=config)

    entsoe_collector = providers.Factory(
        EntsoeCollector,
        entsoe_client=entsoe_client,
    )

    energy_data_repository = providers.Factory(
        EnergyDataRepository,
        database=database,
    )

    backfill_progress_repository = providers.Factory(
        BackfillProgressRepository,
        database=database,
    )

    gl_market_document_processor = providers.Factory(
        GlMarketDocumentProcessor,
    )

    entsoe_data_service = providers.Factory(
        EntsoEDataService,
        collector=entsoe_collector,
        processor=gl_market_document_processor,
        repository=energy_data_repository,
    )

    backfill_service = providers.Factory(
        BackfillService,
        collector=entsoe_collector,
        processor=gl_market_document_processor,
        repository=energy_data_repository,
        database=database,
        config=providers.Callable(lambda c: c.backfill, config),
        progress_repository=backfill_progress_repository,
    )

    scheduler_service = providers.Factory(
        SchedulerService,
        entsoe_data_service=entsoe_data_service,
        backfill_service=backfill_service,
        database=database,
        config=providers.Callable(lambda c: c.scheduler, config),
    )
