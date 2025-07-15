"""Unit tests for EntsoEClientFactory."""

from unittest.mock import Mock, patch

import pytest

from entsoe_client.client.default_entsoe_client import DefaultEntsoEClient
from entsoe_client.client.entsoe_client import EntsoEClient
from entsoe_client.client.entsoe_client_factory import EntsoEClientFactory
from entsoe_client.config.settings import EntsoEClientConfig
from entsoe_client.container import Container
from entsoe_client.exceptions.entsoe_client_factory_error import (
    EntsoEClientFactoryError,
)


class TestEntsoEClientFactory:
    """Test suite for EntsoEClientFactory."""

    @pytest.fixture
    def valid_api_token(self) -> str:
        """Valid API token for testing."""
        return "test-api-token-123"

    @pytest.fixture
    def mock_config(self) -> Mock:
        """Mock EntsoEClientConfig."""
        mock_config = Mock(spec=EntsoEClientConfig)
        mock_config.base_url = "https://web-api.tp.entsoe.eu/api"
        return mock_config

    @pytest.fixture
    def mock_http_client(self) -> Mock:
        """Mock HTTP client."""
        return Mock()

    @pytest.fixture
    def mock_container(self, mock_http_client: Mock) -> Mock:
        """Mock Container with configured dependencies."""
        mock_container = Mock(spec=Container)
        mock_container.http_client.return_value = mock_http_client
        return mock_container

    @pytest.fixture
    def mock_default_client(self) -> Mock:
        """Mock DefaultEntsoEClient."""
        return Mock(spec=DefaultEntsoEClient)

    def test_create_client_success(
        self,
        valid_api_token: str,
        mock_config: Mock,
        mock_container: Mock,
        mock_default_client: Mock,
    ) -> None:
        """Test successful client creation with valid API token."""
        with (
            patch(
                "entsoe_client.client.entsoe_client_factory.EntsoEClientConfig",
                return_value=mock_config,
            ) as mock_config_class,
            patch(
                "entsoe_client.client.entsoe_client_factory.Container",
                return_value=mock_container,
            ) as mock_container_class,
            patch(
                "entsoe_client.client.entsoe_client_factory.DefaultEntsoEClient",
                return_value=mock_default_client,
            ) as mock_client_class,
        ):
            result = EntsoEClientFactory.create_client(valid_api_token)

            # Verify result
            assert result == mock_default_client
            assert isinstance(result, Mock)  # Mock of DefaultEntsoEClient

            # Verify EntsoEClientConfig was created with correct token
            mock_config_class.assert_called_once_with(api_token=valid_api_token)

            # Verify Container was created and configured
            mock_container_class.assert_called_once()
            mock_container.config.override.assert_called_once_with(mock_config)

            # Verify HTTP client was created
            mock_container.http_client.assert_called_once()

            # Verify DefaultEntsoEClient was created with correct parameters
            mock_client_class.assert_called_once_with(
                mock_container.http_client.return_value,
                str(mock_config.base_url),
            )

    def test_create_client_with_container_integration(
        self,
        valid_api_token: str,
        mock_config: Mock,
        mock_http_client: Mock,
        mock_default_client: Mock,
    ) -> None:
        """Test client creation with real container flow."""
        with (
            patch(
                "entsoe_client.client.entsoe_client_factory.EntsoEClientConfig",
                return_value=mock_config,
            ),
            patch(
                "entsoe_client.client.entsoe_client_factory.Container",
            ) as mock_container_class,
            patch(
                "entsoe_client.client.entsoe_client_factory.DefaultEntsoEClient",
                return_value=mock_default_client,
            ),
        ):
            mock_container = Mock()
            mock_container.http_client.return_value = mock_http_client
            mock_container_class.return_value = mock_container

            result = EntsoEClientFactory.create_client(valid_api_token)

            # Verify the flow
            assert result == mock_default_client

            # Verify config creation
            mock_container_class.assert_called_once()
            mock_container.config.override.assert_called_once_with(mock_config)
            mock_container.http_client.assert_called_once()

    def test_create_client_returns_entso_e_client_interface(
        self,
        valid_api_token: str,
        mock_config: Mock,
        mock_container: Mock,
        mock_http_client: Mock,
    ) -> None:
        """Test that create_client returns EntsoEClient interface."""
        with (
            patch(
                "entsoe_client.client.entsoe_client_factory.EntsoEClientConfig",
                return_value=mock_config,
            ),
            patch(
                "entsoe_client.client.entsoe_client_factory.Container",
                return_value=mock_container,
            ),
            patch(
                "entsoe_client.client.entsoe_client_factory.DefaultEntsoEClient",
            ) as mock_client_class,
        ):
            mock_client = Mock(spec=DefaultEntsoEClient)
            mock_client_class.return_value = mock_client

            result = EntsoEClientFactory.create_client(valid_api_token)

            # Verify return type is compatible with EntsoEClient interface
            assert result == mock_client
            # DefaultEntsoEClient implements EntsoEClient interface
            mock_client_class.assert_called_once_with(
                mock_http_client,
                str(mock_config.base_url),
            )

    def test_create_client_with_none_token(self) -> None:
        """Test create_client raises error with None token."""
        with pytest.raises(EntsoEClientFactoryError) as exc_info:
            EntsoEClientFactory.create_client(None)

        assert "API token cannot be null or empty" in str(exc_info.value)

    def test_create_client_with_empty_token(self) -> None:
        """Test create_client raises error with empty token."""
        with pytest.raises(EntsoEClientFactoryError) as exc_info:
            EntsoEClientFactory.create_client("")

        assert "API token cannot be null or empty" in str(exc_info.value)

    def test_create_client_with_whitespace_only_token(self) -> None:
        """Test create_client raises error with whitespace-only token."""
        with pytest.raises(EntsoEClientFactoryError) as exc_info:
            EntsoEClientFactory.create_client("   ")

        assert "API token cannot be null or empty" in str(exc_info.value)

    def test_create_client_with_tab_and_newline_token(self) -> None:
        """Test create_client raises error with tab and newline token."""
        with pytest.raises(EntsoEClientFactoryError) as exc_info:
            EntsoEClientFactory.create_client("\t\n\r")

        assert "API token cannot be null or empty" in str(exc_info.value)

    def test_create_client_with_minimal_valid_token(
        self,
        mock_config: Mock,
        mock_container: Mock,
        mock_default_client: Mock,
    ) -> None:
        """Test create_client with minimal valid token."""
        minimal_token = "a"

        with (
            patch(
                "entsoe_client.client.entsoe_client_factory.EntsoEClientConfig",
                return_value=mock_config,
            ),
            patch(
                "entsoe_client.client.entsoe_client_factory.Container",
                return_value=mock_container,
            ),
            patch(
                "entsoe_client.client.entsoe_client_factory.DefaultEntsoEClient",
                return_value=mock_default_client,
            ),
        ):
            result = EntsoEClientFactory.create_client(minimal_token)

            assert result == mock_default_client

    def test_create_client_with_long_token(
        self,
        mock_config: Mock,
        mock_container: Mock,
        mock_default_client: Mock,
    ) -> None:
        """Test create_client with long token."""
        long_token = "a" * 1000

        with (
            patch(
                "entsoe_client.client.entsoe_client_factory.EntsoEClientConfig",
                return_value=mock_config,
            ),
            patch(
                "entsoe_client.client.entsoe_client_factory.Container",
                return_value=mock_container,
            ),
            patch(
                "entsoe_client.client.entsoe_client_factory.DefaultEntsoEClient",
                return_value=mock_default_client,
            ),
        ):
            result = EntsoEClientFactory.create_client(long_token)

            assert result == mock_default_client

    def test_create_client_with_special_characters(
        self,
        mock_config: Mock,
        mock_container: Mock,
        mock_default_client: Mock,
    ) -> None:
        """Test create_client with special characters in token."""
        special_token = "token-with-123_special.chars@domain.com"

        with (
            patch(
                "entsoe_client.client.entsoe_client_factory.EntsoEClientConfig",
                return_value=mock_config,
            ),
            patch(
                "entsoe_client.client.entsoe_client_factory.Container",
                return_value=mock_container,
            ),
            patch(
                "entsoe_client.client.entsoe_client_factory.DefaultEntsoEClient",
                return_value=mock_default_client,
            ),
        ):
            result = EntsoEClientFactory.create_client(special_token)

            assert result == mock_default_client

    def test_create_client_config_creation_params(
        self,
        valid_api_token: str,
        mock_container: Mock,
        mock_default_client: Mock,
    ) -> None:
        """Test that EntsoEClientConfig is created with correct parameters."""
        with (
            patch(
                "entsoe_client.client.entsoe_client_factory.EntsoEClientConfig",
            ) as mock_config_class,
            patch(
                "entsoe_client.client.entsoe_client_factory.Container",
                return_value=mock_container,
            ),
            patch(
                "entsoe_client.client.entsoe_client_factory.DefaultEntsoEClient",
                return_value=mock_default_client,
            ),
        ):
            mock_config = Mock()
            mock_config.base_url = "https://web-api.tp.entsoe.eu/api"
            mock_config_class.return_value = mock_config

            result = EntsoEClientFactory.create_client(valid_api_token)

            # Verify config was created with correct API token
            mock_config_class.assert_called_once_with(api_token=valid_api_token)
            assert result == mock_default_client

    def test_create_client_default_client_creation_params(
        self,
        valid_api_token: str,
        mock_config: Mock,
        mock_container: Mock,
        mock_http_client: Mock,
    ) -> None:
        """Test that DefaultEntsoEClient is created with correct parameters."""
        with (
            patch(
                "entsoe_client.client.entsoe_client_factory.EntsoEClientConfig",
                return_value=mock_config,
            ),
            patch(
                "entsoe_client.client.entsoe_client_factory.Container",
                return_value=mock_container,
            ),
            patch(
                "entsoe_client.client.entsoe_client_factory.DefaultEntsoEClient",
            ) as mock_client_class,
        ):
            mock_client = Mock(spec=DefaultEntsoEClient)
            mock_client_class.return_value = mock_client

            result = EntsoEClientFactory.create_client(valid_api_token)

            # Verify DefaultEntsoEClient was created with correct parameters
            mock_client_class.assert_called_once_with(
                mock_http_client,
                str(mock_config.base_url),
            )
            assert result == mock_client

    def test_create_client_error_propagation(self, valid_api_token: str) -> None:
        """Test that errors from dependencies are properly propagated."""
        with (
            patch(
                "entsoe_client.client.entsoe_client_factory.EntsoEClientConfig",
                side_effect=ValueError("Config creation failed"),
            ),
            pytest.raises(ValueError, match="Config creation failed"),
        ):
            EntsoEClientFactory.create_client(valid_api_token)

    def test_create_client_is_static_method(self) -> None:
        """Test that create_client is a static method."""
        # Verify we can call it without instantiating the class
        with (
            patch(
                "entsoe_client.client.entsoe_client_factory.EntsoEClientConfig",
            ),
            patch(
                "entsoe_client.client.entsoe_client_factory.Container",
            ),
            patch(
                "entsoe_client.client.entsoe_client_factory.DefaultEntsoEClient",
            ),
        ):
            # Should be callable without instance
            assert callable(EntsoEClientFactory.create_client)

            # Should not require self parameter - this should work without error
            result = EntsoEClientFactory.create_client("test-token")
            assert result is not None
