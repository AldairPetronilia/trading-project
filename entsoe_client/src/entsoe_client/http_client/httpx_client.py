import logging
from http import HTTPStatus
from types import TracebackType
from typing import Any
from urllib.parse import urlencode

import httpx
from pydantic import HttpUrl

from entsoe_client.config.settings import EntsoEClientConfig
from entsoe_client.http_client.exceptions import (
    HttpClientConnectionError,
    HttpClientError,
    HttpClientRetryError,
    HttpClientTimeoutError,
)
from entsoe_client.http_client.http_client import HttpClient
from entsoe_client.http_client.retry_handler import RetryHandler

logger = logging.getLogger(__name__)


class HttpxClient(HttpClient):
    """HTTP client implementation using httpx for ENTSO-E API requests."""

    def __init__(self, config: EntsoEClientConfig, retry_handler: RetryHandler):
        self._config = config
        self._retry_handler = retry_handler
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "HttpxClient":
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> None:
        """Ensure the httpx client is initialized."""
        if self._client is None:
            # Connection pooling configuration from config
            limits = httpx.Limits(
                max_connections=self._config.http.max_connections,
                max_keepalive_connections=self._config.http.max_keepalive_connections,
            )

            # Timeout configuration
            timeout = httpx.Timeout(
                connect=self._config.http.connection_timeout.total_seconds(),
                read=self._config.http.read_timeout.total_seconds(),
                write=self._config.http.write_timeout.total_seconds(),
                pool=self._config.http.pool_timeout.total_seconds(),
            )

            self._client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                follow_redirects=True,
            )

    async def get(self, url: HttpUrl, params: dict[str, Any] | None = None) -> str:
        """Perform a GET request to the specified URL with optional parameters."""
        await self._ensure_client()

        # Add security token from config
        request_params = params.copy() if params else {}
        request_params.update(self._config.get_auth_params())

        # Build full URL with parameters
        full_url = self._build_url(url, request_params)

        # Validate URL
        self._validate_url(full_url)

        # Execute request with retry logic
        return await self._retry_handler.execute(
            lambda: self._execute_request(full_url),
        )

    async def _execute_request(self, url: str) -> str:
        """Execute a single HTTP request."""
        if self._client is None:
            msg = "Client not initialized"
            raise HttpClientError(msg)

        # Build request with headers
        headers = self._config.get_auth_headers()

        try:
            response = await self._client.get(url, headers=headers)

            # Handle response based on status code
            if response.status_code == HTTPStatus.OK:
                logger.debug("Request successful: %s", response.status_code)
                return response.text
            if HttpClientRetryError.is_retryable(response.status_code):
                error_msg = f"Request failed with status {response.status_code}"
                logger.warning("HTTP retryable error: %s", error_msg)
                raise HttpClientRetryError(
                    error_msg,
                    status_code=response.status_code,
                    responnse_body=response.text,
                )
            error_msg = f"Request failed with status {response.status_code}"
            logger.error("HTTP error: %s", error_msg)
            raise HttpClientError(
                error_msg,
                status_code=response.status_code,
                responnse_body=response.text,
            )

        except httpx.TimeoutException as e:
            logger.exception("Request timeout")
            msg = "Request timeout"
            raise HttpClientTimeoutError(msg) from e
        except httpx.ConnectError as e:
            logger.exception("Connection error")
            msg = "Connection failed"
            raise HttpClientConnectionError(msg) from e
        except httpx.HTTPStatusError as e:
            logger.exception("HTTP status error")
            msg = "HTTP status error"
            raise HttpClientError(msg) from e
        except httpx.RequestError as e:
            logger.exception("Request error")
            msg = "Request failed"
            raise HttpClientError(msg) from e

    def _build_url(self, base_url: HttpUrl, params: dict[str, Any] | None) -> str:
        """Build URL with query parameters."""
        if not params:
            return str(base_url)

        # Filter out None values and convert to strings
        filtered_params = {
            key: str(value) for key, value in params.items() if value is not None
        }

        if not filtered_params:
            return str(base_url)

        # Build query string
        query_string = urlencode(filtered_params)
        return f"{base_url}?{query_string}"

    def _validate_url(self, url: str) -> None:
        """Validate that the URL is properly formatted."""
        if not url:
            msg = "URL cannot be empty"
            raise HttpClientError(msg)

        if not url.startswith(("http://", "https://")):
            msg = f"Invalid URL scheme: {url}"
            raise HttpClientError(msg)

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.debug("HTTP client closed")
