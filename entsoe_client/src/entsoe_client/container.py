"""Dependency injection container for EntsoE client."""

from dependency_injector import containers, providers

from .config.settings import EntsoEClientConfig


class Container(containers.DeclarativeContainer):
    """Main DI container for EntsoE client."""

    config = providers.Singleton(EntsoEClientConfig)
