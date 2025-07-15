import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from entsoe_client.config.settings import RetryConfig
from entsoe_client.http_client.exceptions import (
    HttpClientConnectionError,
    HttpClientError,
    HttpClientRetryError,
    HttpClientTimeoutError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryHandler:
    """Handles retry logic for HTTP requests using tenacity."""

    def __init__(self, config: RetryConfig):
        self._config = config

    async def execute(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Execute the operation with retry logic."""
        retry_decorator = retry(
            stop=stop_after_attempt(self._config.max_attempts),
            wait=wait_exponential(
                multiplier=self._config.base_delay.total_seconds(),
                max=self._config.max_delay.total_seconds(),
                exp_base=self._config.exponential_base,
            ),
            retry=retry_if_exception_type(self._get_retryable_exceptions()),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

        try:
            return await retry_decorator(operation)()
        except RetryError as e:
            # Re-raise the original exception, not the RetryError
            if e.last_attempt.exception():
                raise e.last_attempt.exception() from e
            msg = "Request execution failed"
            raise HttpClientError(msg) from e
        except self._get_retryable_exceptions():
            # Re-raise retryable exceptions as-is (tenacity already handled retries)
            raise
        except Exception as e:
            # Wrap non-retryable exceptions in HttpClientError
            msg = "Request execution failed"
            raise HttpClientError(msg, cause=e) from e

    def _get_retryable_exceptions(self) -> tuple:
        """Get tuple of retryable exception types."""
        return HttpClientTimeoutError, HttpClientConnectionError, HttpClientRetryError
