"""Dependency injection container for EntsoE client."""

from dependency_injector import containers, providers

from .config.settings import EntsoEClientConfig
from .http.httpx_client import HttpxClient
from .http.retry_handler import RetryHandler


class Container(containers.DeclarativeContainer):
    """Main DI container for EntsoE client."""

    config = providers.Singleton(EntsoEClientConfig)

    retry_handler = providers.Factory(
        RetryHandler,
        config=config.provided.retry,
    )

    http_client = providers.Factory(
        HttpxClient,
        config=config,
        retry_handler=retry_handler,
    )
