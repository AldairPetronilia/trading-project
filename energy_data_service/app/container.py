from dependency_injector import containers, providers

from app.config.database import Database
from app.config.settings import Settings
from app.repositories.energy_data_repository import EnergyDataRepository
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

    energy_data_repository = providers.Factory(
        EnergyDataRepository,
        database=database,
    )
