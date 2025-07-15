from entsoe_client.client.default_entsoe_client import DefaultEntsoEClient
from entsoe_client.client.entsoe_client import EntsoEClient
from entsoe_client.config.settings import EntsoEClientConfig
from entsoe_client.container import Container
from entsoe_client.exceptions.entsoe_client_factory_error import (
    EntsoEClientFactoryError,
)


class EntsoEClientFactory:
    """Factory for creating EntsoE clients."""

    @staticmethod
    def create_client(api_token: str) -> EntsoEClient:
        """
        Create an EntsoE client with the provided API token.

        Args:
            api_token: ENTSO-E API token for authentication

        Returns:
            Configured EntsoE client instance

        Raises:
            ValueError: If API token is None or empty
        """
        if not api_token or not api_token.strip():
            raise EntsoEClientFactoryError.api_token_empty()

        config = EntsoEClientConfig(api_token=api_token)

        # Create container with configuration
        container = Container()
        container.config.override(config)

        # Create HTTP client from container
        http_client = container.http_client()

        return DefaultEntsoEClient(http_client, str(config.base_url))
