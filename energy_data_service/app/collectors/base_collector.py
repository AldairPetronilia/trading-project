import asyncio
import logging
import types
from abc import ABC, abstractmethod
from datetime import datetime
from http import HTTPStatus
from typing import Any

import aiohttp

from app.model.collection_result import CollectionResult

log = logging.getLogger(__name__)


class BaseCollector(ABC):
    """
    Base class for collectors.
    Collectors are responsible for gathering data from various sources.

    Each collector is responsible for:
    1. Authenticating with its specific data source
    2. Fetching raw data
    3. Converting to standardized RawDataPoint format
    4. Handling errors and retries gracefully
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = config
        self.session: aiohttp.ClientSession | None = None
        self.last_successful_collection: datetime | None = None

    async def __aenter__(self) -> "BaseCollector":
        """Asynchronous context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Asynchronous context manager exit."""
        await self.cleanup()

    async def initialize(self) -> None:
        """Initialize the collector (setup HTTP session, etc.)"""
        timeout = aiohttp.ClientTimeout(
            total=self.config.get("timeout", 10),
            connect=self.config.get("connect_timeout", 5),
        )
        connector = aiohttp.TCPConnector(limit=self.config.get("max_connections", 10))
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=self._get_default_headers(),
        )

    async def cleanup(self) -> None:
        """Cleanup resources used by the collector."""
        if self.session:
            await self.session.close()
        log.info("Collector %s cleaned up resources.", self.name)

    def _get_default_headers(self) -> dict[str, str]:
        """Override in subclasses to add authentication headers"""
        return {
            "User-Agent": "EnergyDataCollector/1.0",
            "Accept": "application/xml, application/json",
        }

    @abstractmethod
    async def collect(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> CollectionResult:
        """
        Collect data for the specified date range.

        Args:
            start_date: Start of collection period (UTC)
            end_date: End of collection period (UTC)

        Returns:
            CollectionResult with data points or error information
        """

    @abstractmethod
    def _validate_config(self) -> bool:
        """
        Validate collector configuration.

        Returns:
            bool: True if configuration is valid, False otherwise
        """

    async def _make_request(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> aiohttp.ClientResponse:
        """
        Make HTTP request with proper error handling and retries.

        Implements exponential backoff, rate limit handling, and proper
        error categorization for monitoring and alerting.

        Args:
            url: Request URL
            params: Query parameters
            headers: Additional headers

        Returns:
            HTTP response object

        Raises:
            aiohttp.ClientError: If request fails after all retries
        """
        if not self.session:
            msg = "Collector %s is not initialized"
            raise RuntimeError(msg, self.name)

        max_retries = self.config.get("max_retries", 3)
        retry_delay = self.config.get("retry_delay", 1)

        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)

        for attempt in range(max_retries):
            try:
                async with self.session.get(
                    url,
                    params=params,
                    headers=request_headers,
                ) as response:
                    if response.status == HTTPStatus.OK:
                        return response
                    await self._handle_response_errors(
                        attempt,
                        max_retries,
                        response,
                        retry_delay,
                    )
            except aiohttp.ClientError as e:
                if attempt == max_retries - 1:
                    raise  # Reraise after final attempt
                wait_time = retry_delay * (2**attempt)
                log.warning(
                    "%s: Request failed with error %s, retrying in %d seconds (attempt %d/%d)",
                    self.name,
                    str(e),
                    wait_time,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(wait_time)
        msg = f"{self.name}: Request failed after {max_retries} attempts"
        raise aiohttp.ClientError(
            msg,
        )

    async def _handle_response_errors(
        self,
        attempt: int,
        max_retries: int,
        response: aiohttp.ClientResponse,
        retry_delay: int,
    ) -> None:
        if response.status == HTTPStatus.TOO_MANY_REQUESTS:
            # Handle rate limiting
            retry_after = response.headers.get("Retry-After")
            wait_time = int(retry_after) if retry_after else retry_delay * (2**attempt)
            log.warning(
                "Rate limit hit for %s, retrying in %d seconds (attempt %d/%d)",
                self.name,
                wait_time,
                attempt + 1,
                max_retries,
            )
            await asyncio.sleep(wait_time)
        elif response.status == HTTPStatus.UNAUTHORIZED:
            msg = f"{self.name}: Authentication failed"
            await self._raise_client_error(msg)
        elif response.status == HTTPStatus.NOT_FOUND:
            msg = f"{self.name}: Resource not found"
            await self._raise_client_error(msg)
        elif response.status >= HTTPStatus.INTERNAL_SERVER_ERROR:
            wait_time = retry_delay * (2**attempt)
            log.warning(
                "%s: Server error with status %d, retrying in %d seconds (attempt %d/%d)",
                self.name,
                response.status,
                wait_time,
                attempt + 1,
                max_retries,
            )
            await asyncio.sleep(wait_time)
        else:
            msg = f"{self.name}: Unexpected status {response.status} - {await response.text()}"
            await self._raise_client_error(msg)

    async def _raise_client_error(self, msg: str) -> None:
        raise aiohttp.ClientError(msg)
