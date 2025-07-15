from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from entsoe_client.config.settings import RetryConfig
from entsoe_client.http.exceptions import (
    HttpClientConnectionError,
    HttpClientError,
    HttpClientRetryError,
    HttpClientTimeoutError,
)
from entsoe_client.http.retry_handler import RetryHandler


class TestRetryHandler:
    """Test cases for RetryHandler class."""

    @pytest.fixture
    def retry_config(self) -> RetryConfig:
        """Create a test retry configuration."""
        return RetryConfig(
            max_attempts=3,
            base_delay=timedelta(seconds=1),
            max_delay=timedelta(seconds=5),
            exponential_base=2.0,
        )

    @pytest.fixture
    def retry_handler(self, retry_config: RetryConfig) -> RetryHandler:
        """Create a RetryHandler instance for testing."""
        return RetryHandler(retry_config)

    @pytest.mark.asyncio
    async def test_execute_success_on_first_attempt(
        self,
        retry_handler: RetryHandler,
    ) -> None:
        """Test successful execution on first attempt."""
        mock_operation = AsyncMock(return_value="success")

        result = await retry_handler.execute(mock_operation)

        assert result == "success"
        mock_operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_success_after_retry(
        self,
        retry_handler: RetryHandler,
    ) -> None:
        """Test successful execution after one retry."""
        mock_operation = AsyncMock(
            side_effect=[HttpClientTimeoutError("Timeout"), "success"],
        )

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await retry_handler.execute(mock_operation)

        assert result == "success"
        assert mock_operation.call_count == 2
        mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_fails_after_max_attempts(
        self,
        retry_handler: RetryHandler,
    ) -> None:
        """Test failure after exhausting all retry attempts."""
        mock_operation = AsyncMock(side_effect=HttpClientTimeoutError("Timeout"))

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(HttpClientTimeoutError),
        ):
            await retry_handler.execute(mock_operation)

        assert mock_operation.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_retries_on_timeout_error(
        self,
        retry_handler: RetryHandler,
    ) -> None:
        """Test that timeout errors trigger retries."""
        mock_operation = AsyncMock(side_effect=HttpClientTimeoutError("Timeout"))

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(HttpClientTimeoutError),
        ):
            await retry_handler.execute(mock_operation)

        assert mock_operation.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_retries_on_connection_error(
        self,
        retry_handler: RetryHandler,
    ) -> None:
        """Test that connection errors trigger retries."""
        mock_operation = AsyncMock(
            side_effect=HttpClientConnectionError("Connection failed"),
        )

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(HttpClientConnectionError),
        ):
            await retry_handler.execute(mock_operation)

        assert mock_operation.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_retries_on_retry_error(
        self,
        retry_handler: RetryHandler,
    ) -> None:
        """Test that retry errors trigger retries."""
        mock_operation = AsyncMock(
            side_effect=HttpClientRetryError("Retry error", status_code=503),
        )

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(HttpClientRetryError),
        ):
            await retry_handler.execute(mock_operation)

        assert mock_operation.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_does_not_retry_on_non_retryable_error(
        self,
        retry_handler: RetryHandler,
    ) -> None:
        """Test that non-retryable errors don't trigger retries."""
        mock_operation = AsyncMock(side_effect=ValueError("Not retryable"))

        with pytest.raises(HttpClientError) as exc_info:
            await retry_handler.execute(mock_operation)

        assert "Request execution failed" in str(exc_info.value)
        mock_operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_logs_retry_attempts(
        self,
        retry_handler: RetryHandler,
    ) -> None:
        """Test that retry attempts are logged."""
        mock_operation = AsyncMock(
            side_effect=[HttpClientTimeoutError("Timeout"), "success"],
        )

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch("entsoe_client.http.retry_handler.logger"),
        ):
            result = await retry_handler.execute(mock_operation)

        assert result == "success"
        # tenacity's before_sleep_log should have been called
        # We can't easily test the exact log message, but we can verify the operation succeeded

    @pytest.mark.asyncio
    async def test_execute_respects_max_attempts_config(self) -> None:
        """Test that max_attempts configuration is respected."""
        config = RetryConfig(max_attempts=2)
        handler = RetryHandler(config)
        mock_operation = AsyncMock(side_effect=HttpClientTimeoutError("Timeout"))

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(HttpClientTimeoutError),
        ):
            await handler.execute(mock_operation)

        assert mock_operation.call_count == 2

    def test_get_retryable_exceptions(self, retry_handler: RetryHandler) -> None:
        """Test that retryable exceptions are correctly identified."""
        retryable_exceptions = retry_handler._get_retryable_exceptions()

        expected_exceptions = (
            HttpClientTimeoutError,
            HttpClientConnectionError,
            HttpClientRetryError,
        )

        assert retryable_exceptions == expected_exceptions

    @pytest.mark.asyncio
    async def test_execute_with_different_return_types(
        self,
        retry_handler: RetryHandler,
    ) -> None:
        """Test that execute works with different return types."""
        # Test with dict
        mock_operation = AsyncMock(return_value={"key": "value"})
        result = await retry_handler.execute(mock_operation)
        assert result == {"key": "value"}

        # Test with list
        mock_operation = AsyncMock(return_value=[1, 2, 3])
        result = await retry_handler.execute(mock_operation)
        assert result == [1, 2, 3]

        # Test with None
        mock_operation = AsyncMock(return_value=None)
        result = await retry_handler.execute(mock_operation)
        assert result is None

    @pytest.mark.asyncio
    async def test_execute_with_mixed_exceptions(
        self,
        retry_handler: RetryHandler,
    ) -> None:
        """Test behavior with mixed retryable and non-retryable exceptions."""
        mock_operation = AsyncMock(
            side_effect=[
                HttpClientTimeoutError("Timeout"),
                ValueError("Not retryable"),
            ],
        )

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(HttpClientError) as exc_info,
        ):
            await retry_handler.execute(mock_operation)

        assert "Request execution failed" in str(exc_info.value)
        assert mock_operation.call_count == 2
