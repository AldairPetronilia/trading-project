"""Dependency injection container for EntsoE client."""

from dependency_injector import containers, providers

from .config.settings import EntsoEClientConfig
from .http.retry_handler import RetryHandler


class Container(containers.DeclarativeContainer):
    """Main DI container for EntsoE client."""

    config = providers.Singleton(EntsoEClientConfig)

    retry_handler = providers.Factory(
        RetryHandler,
        config=config.provided.retry,
    )
