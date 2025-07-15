from typing import Optional


class HttpClientError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        responnse_body: str | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = responnse_body
        self.cause = cause


class HttpClientRetryError(HttpClientError):
    """Exception raised when a request should be retried."""

    @classmethod
    def is_retryable(cls, status_code: int) -> bool:
        """Check if the status code indicates a retryable error."""
        return status_code in {429, 502, 503, 504}


class HttpClientTimeoutError(HttpClientError):
    """Exception raised when a request times out."""


class HttpClientConnectionError(HttpClientError):
    """Exception raised when a connection error occurs."""
