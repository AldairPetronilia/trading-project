import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta
from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from pydantic import HttpUrl, SecretStr

from entsoe_client.config.settings import EntsoEClientConfig, HttpConfig, RetryConfig
from entsoe_client.http_client.exceptions import (
    HttpClientConnectionError,
    HttpClientError,
    HttpClientRetryError,
    HttpClientTimeoutError,
)
from entsoe_client.http_client.httpx_client import HttpxClient
from entsoe_client.http_client.retry_handler import RetryHandler


class TestHttpxClient:
    """Test cases for HttpxClient class."""

    @pytest.fixture
    def mock_config(self) -> EntsoEClientConfig:
        """Create a mock ENTSO-E client configuration."""
        return EntsoEClientConfig(
            api_token=SecretStr("test-token"),
            base_url=HttpUrl("https://api.example.com"),
            user_agent="test-agent",
            http=HttpConfig(
                connection_timeout=timedelta(seconds=10),
                read_timeout=timedelta(seconds=30),
                write_timeout=timedelta(seconds=25),
                pool_timeout=timedelta(seconds=15),
                max_connections=50,
                max_keepalive_connections=10,
            ),
            retry=RetryConfig(max_attempts=3),
        )

    @pytest.fixture
    def mock_retry_handler(self) -> RetryHandler:
        """Create a mock retry handler."""
        handler = MagicMock(spec=RetryHandler)

        async def execute_mock(func: Callable[[], Awaitable[Any]]) -> Any:
            return await func()

        handler.execute = AsyncMock(side_effect=execute_mock)
        return handler

    @pytest.fixture
    def httpx_client(
        self,
        mock_config: EntsoEClientConfig,
        mock_retry_handler: RetryHandler,
    ) -> HttpxClient:
        """Create an HttpxClient instance for testing."""
        return HttpxClient(mock_config, mock_retry_handler)

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self, httpx_client: HttpxClient) -> None:
        """Test async context manager entry and exit."""
        with (
            patch.object(
                httpx_client,
                "_ensure_client",
                new_callable=AsyncMock,
            ) as mock_ensure,
            patch.object(
                httpx_client,
                "close",
                new_callable=AsyncMock,
            ) as mock_close,
        ):
            async with httpx_client as client:
                assert client is httpx_client
                mock_ensure.assert_called_once()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_client_creates_httpx_client(
        self,
        httpx_client: HttpxClient,
    ) -> None:
        """Test that _ensure_client creates an httpx.AsyncClient with proper configuration."""
        with patch("httpx.AsyncClient") as mock_client_class:
            await httpx_client._ensure_client()

            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args

            # Check limits configuration
            limits = call_args.kwargs["limits"]
            assert limits.max_connections == 50
            assert limits.max_keepalive_connections == 10

            # Check timeout configuration
            timeout = call_args.kwargs["timeout"]
            assert timeout.connect == 10.0
            assert timeout.read == 30.0
            assert timeout.write == 25.0
            assert timeout.pool == 15.0

            # Check other settings
            assert call_args.kwargs["follow_redirects"] is True

    @pytest.mark.asyncio
    async def test_ensure_client_idempotent(self, httpx_client: HttpxClient) -> None:
        """Test that _ensure_client doesn't create multiple clients."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_class.return_value = mock_client_instance

            await httpx_client._ensure_client()
            await httpx_client._ensure_client()

            # Should only be called once
            mock_client_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_success(
        self,
        httpx_client: HttpxClient,
        mock_retry_handler: RetryHandler,
    ) -> None:
        """Test successful GET request."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.text = "<xml>response</xml>"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch.object(httpx_client, "_ensure_client", new_callable=AsyncMock):
            httpx_client._client = mock_client

            result = await httpx_client.get(
                HttpUrl("https://api.example.com/data"),
                {"param1": "value1", "param2": "value2"},
            )

            assert result == "<xml>response</xml>"
            mock_retry_handler.execute.assert_called_once()
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_adds_security_token(
        self,
        httpx_client: HttpxClient,
    ) -> None:
        """Test that GET request adds security token from config."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.text = "response"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch.object(httpx_client, "_ensure_client", new_callable=AsyncMock):
            httpx_client._client = mock_client

            await httpx_client.get(HttpUrl("https://api.example.com/data"))

            # Check that the URL contains the security token
            call_args = mock_client.get.call_args
            called_url = call_args[0][0]

            parsed_url = urlparse(called_url)
            query_params = parse_qs(parsed_url.query)

            assert "securityToken" in query_params
            assert query_params["securityToken"] == ["test-token"]

    @pytest.mark.asyncio
    async def test_get_adds_headers(
        self,
        httpx_client: HttpxClient,
    ) -> None:
        """Test that GET request adds headers from config."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.text = "response"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch.object(httpx_client, "_ensure_client", new_callable=AsyncMock):
            httpx_client._client = mock_client

            await httpx_client.get(HttpUrl("https://api.example.com/data"))

            # Check that headers are passed
            call_args = mock_client.get.call_args
            headers = call_args.kwargs.get("headers", {})

            assert headers.get("User-Agent") == "test-agent"

    @pytest.mark.asyncio
    async def test_get_retryable_error(
        self,
        httpx_client: HttpxClient,
        mock_retry_handler: RetryHandler,
    ) -> None:
        """Test that retryable HTTP errors are handled correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch.object(httpx_client, "_ensure_client", new_callable=AsyncMock):
            httpx_client._client = mock_client

            # Mock retry handler to execute once and raise the exception
            async def execute_mock(func: Callable[[], Awaitable[Any]]) -> Any:
                return await func()

            mock_retry_handler.execute.side_effect = execute_mock

            with pytest.raises(HttpClientRetryError) as exc_info:
                await httpx_client.get(HttpUrl("https://api.example.com/data"))

            assert exc_info.value.status_code == 503
            assert "Request failed with status 503" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_non_retryable_error(
        self,
        httpx_client: HttpxClient,
        mock_retry_handler: RetryHandler,
    ) -> None:
        """Test that non-retryable HTTP errors are handled correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch.object(httpx_client, "_ensure_client", new_callable=AsyncMock):
            httpx_client._client = mock_client

            async def execute_mock(func: Callable[[], Awaitable[Any]]) -> Any:
                return await func()

            mock_retry_handler.execute.side_effect = execute_mock

            with pytest.raises(HttpClientError) as exc_info:
                await httpx_client.get(HttpUrl("https://api.example.com/data"))

            assert exc_info.value.status_code == 400
            assert "Request failed with status 400" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_timeout_error(
        self,
        httpx_client: HttpxClient,
        mock_retry_handler: RetryHandler,
    ) -> None:
        """Test that timeout errors are handled correctly."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timeout")

        with patch.object(httpx_client, "_ensure_client", new_callable=AsyncMock):
            httpx_client._client = mock_client

            async def execute_mock(func: Callable[[], Awaitable[Any]]) -> Any:
                return await func()

            mock_retry_handler.execute.side_effect = execute_mock

            with pytest.raises(HttpClientTimeoutError) as exc_info:
                await httpx_client.get(HttpUrl("https://api.example.com/data"))

            assert "Request timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_connection_error(
        self,
        httpx_client: HttpxClient,
        mock_retry_handler: RetryHandler,
    ) -> None:
        """Test that connection errors are handled correctly."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")

        with patch.object(httpx_client, "_ensure_client", new_callable=AsyncMock):
            httpx_client._client = mock_client

            async def execute_mock(func: Callable[[], Awaitable[Any]]) -> Any:
                return await func()

            mock_retry_handler.execute.side_effect = execute_mock

            with pytest.raises(HttpClientConnectionError) as exc_info:
                await httpx_client.get(HttpUrl("https://api.example.com/data"))

            assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_client_not_initialized(
        self,
        httpx_client: HttpxClient,
        mock_retry_handler: RetryHandler,
    ) -> None:
        """Test that error is raised when client is not initialized during request execution."""
        # Mock _ensure_client to not set the client
        with patch.object(httpx_client, "_ensure_client", new_callable=AsyncMock):
            httpx_client._client = None

            async def execute_mock(func: Callable[[], Awaitable[Any]]) -> Any:
                return await func()

            mock_retry_handler.execute.side_effect = execute_mock

            with pytest.raises(HttpClientError) as exc_info:
                await httpx_client.get(HttpUrl("https://api.example.com/data"))

            assert "Client not initialized" in str(exc_info.value)

    def test_build_url_no_params(self, httpx_client: HttpxClient) -> None:
        """Test URL building without parameters."""
        url = HttpUrl("https://api.example.com/data")
        result = httpx_client._build_url(url, None)
        assert result == "https://api.example.com/data"

    def test_build_url_with_params(self, httpx_client: HttpxClient) -> None:
        """Test URL building with parameters."""
        url = HttpUrl("https://api.example.com/data")
        params = {"param1": "value1", "param2": "value2", "param3": None}

        result = httpx_client._build_url(url, params)

        parsed_url = urlparse(result)
        query_params = parse_qs(parsed_url.query)

        assert parsed_url.scheme == "https"
        assert parsed_url.netloc == "api.example.com"
        assert parsed_url.path == "/data"
        assert query_params["param1"] == ["value1"]
        assert query_params["param2"] == ["value2"]
        assert "param3" not in query_params  # None values should be filtered out

    def test_build_url_empty_params(self, httpx_client: HttpxClient) -> None:
        """Test URL building with empty parameters."""
        url = HttpUrl("https://api.example.com/data")
        result = httpx_client._build_url(url, {})
        assert result == "https://api.example.com/data"

    def test_validate_url_valid(self, httpx_client: HttpxClient) -> None:
        """Test URL validation with valid URLs."""
        httpx_client._validate_url("https://api.example.com/data")
        httpx_client._validate_url("http://api.example.com/data")
        # Should not raise any exceptions

    def test_validate_url_invalid_scheme(self, httpx_client: HttpxClient) -> None:
        """Test URL validation with invalid scheme."""
        with pytest.raises(HttpClientError) as exc_info:
            httpx_client._validate_url("ftp://api.example.com/data")

        assert "Invalid URL scheme" in str(exc_info.value)

    def test_validate_url_empty(self, httpx_client: HttpxClient) -> None:
        """Test URL validation with empty URL."""
        with pytest.raises(HttpClientError) as exc_info:
            httpx_client._validate_url("")

        assert "URL cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_close_with_client(self, httpx_client: HttpxClient) -> None:
        """Test closing client when httpx client exists."""
        mock_client = AsyncMock()
        httpx_client._client = mock_client

        await httpx_client.close()

        mock_client.aclose.assert_called_once()
        assert httpx_client._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self, httpx_client: HttpxClient) -> None:
        """Test closing client when httpx client doesn't exist."""
        httpx_client._client = None

        # Should not raise any exceptions
        await httpx_client.close()

        assert httpx_client._client is None

    @pytest.mark.asyncio
    async def test_get_with_retry_integration(self) -> None:
        """Test that GET method properly integrates with retry handler."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.text = "success"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        # Create real retry handler instead of mock
        retry_config = RetryConfig(max_attempts=3)
        retry_handler = RetryHandler(retry_config)

        # Create client with real retry handler
        config = EntsoEClientConfig(
            api_token=SecretStr("test-token"),
            base_url=HttpUrl("https://api.example.com"),
        )
        client = HttpxClient(config, retry_handler)

        with patch.object(client, "_ensure_client", new_callable=AsyncMock):
            client._client = mock_client

            result = await client.get(HttpUrl("https://api.example.com/data"))

            assert result == "success"
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_request_http_status_error(
        self,
        httpx_client: HttpxClient,
        mock_retry_handler: RetryHandler,
    ) -> None:
        """Test handling of httpx.HTTPStatusError."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "Status error",
            request=MagicMock(),
            response=MagicMock(),
        )

        with patch.object(httpx_client, "_ensure_client", new_callable=AsyncMock):
            httpx_client._client = mock_client

            async def execute_mock(func: Callable[[], Awaitable[Any]]) -> Any:
                return await func()

            mock_retry_handler.execute.side_effect = execute_mock

            with pytest.raises(HttpClientError) as exc_info:
                await httpx_client.get(HttpUrl("https://api.example.com/data"))

            assert "HTTP status error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_request_generic_request_error(
        self,
        httpx_client: HttpxClient,
        mock_retry_handler: RetryHandler,
    ) -> None:
        """Test handling of generic httpx.RequestError."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.RequestError("Generic request error")

        with patch.object(httpx_client, "_ensure_client", new_callable=AsyncMock):
            httpx_client._client = mock_client

            async def execute_mock(func: Callable[[], Awaitable[Any]]) -> Any:
                return await func()

            mock_retry_handler.execute.side_effect = execute_mock

            with pytest.raises(HttpClientError) as exc_info:
                await httpx_client.get(HttpUrl("https://api.example.com/data"))

            assert "Request failed" in str(exc_info.value)
