from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any


class CollectorError(Exception):
    """Base class for collector exceptions with structured error information.

    Designed to work with any data source (ENTSO-E, Investing.com, AGSI+, SMARD.de, etc.)
    and provide consistent error handling across all data collection operations.
    """

    def __init__(  # noqa: PLR0913
        self,
        message: str,
        *,
        data_source: str | None = None,
        operation: str | None = None,
        request_params: dict[str, Any] | None = None,
        http_details: dict[str, Any] | None = None,
        retry_context: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.data_source = data_source
        self.operation = operation
        self.request_params = request_params or {}
        self.http_details = http_details or {}
        self.retry_context = retry_context or {}
        self.context = context or {}
        self.timestamp = datetime.now(UTC)


class DataSourceConnectionError(CollectorError):
    """Exception raised for network connection and infrastructure failures.

    Covers scenarios like DNS resolution failures, network timeouts,
    SSL/TLS handshake failures, and general connectivity issues.
    """


class RateLimitError(CollectorError):
    """Exception raised when API rate limits are exceeded.

    Handles various rate limiting implementations across different data sources
    including HTTP 429 responses, custom rate limit headers, and quota-based limits.
    """


class DataFormatError(CollectorError):
    """Exception raised for invalid or unexpected response format.

    Covers XML parsing failures, JSON schema validation errors,
    missing required fields, and unexpected data structures.
    """


class RequestTimeoutError(CollectorError):
    """Exception raised when requests exceed configured timeout limits.

    Handles both connection timeouts and read timeouts for any data source.
    """


class AuthenticationError(CollectorError):
    """Exception raised for authentication and authorization failures.

    Covers API token validation failures, OAuth authentication issues,
    API key expiration, and insufficient permissions.
    """


class DataUnavailableError(CollectorError):
    """Exception raised when requested data is not available.

    Handles scenarios where the data source doesn't have data for the
    requested time period, market, or other parameters.
    """


class QuotaExceededError(CollectorError):
    """Exception raised when API usage quotas are exceeded.

    Covers daily/monthly API call limits, data transfer quotas,
    and subscription-based usage limits.
    """


class CollectorConfigurationError(CollectorError):
    """Exception raised for collector setup and configuration issues.

    Handles invalid collector configuration, missing required settings,
    and incompatible parameter combinations.
    """


def map_http_error_to_collector_error(  # noqa: PLR0913, PLR0911
    status_code: int,
    response_body: str | None = None,
    headers: dict[str, str] | None = None,
    data_source: str | None = None,
    operation: str | None = None,
    request_params: dict[str, Any] | None = None,
    original_error: Exception | None = None,  # noqa: ARG001
) -> CollectorError:
    """Map HTTP status codes to appropriate collector exceptions.

    Provides consistent error mapping across all data sources.

    Args:
        status_code: HTTP status code from the response
        response_body: Response body content (may contain error details)
        headers: HTTP response headers
        data_source: Identifier for the data source ("entsoe", "investing", etc.)
        operation: Operation being performed when error occurred
        request_params: Parameters of the failed request
        original_error: Original exception that caused this error

    Returns:
        Appropriate CollectorError subclass based on the HTTP status code
    """
    http_details = {
        "status_code": status_code,
        "response_body": response_body,
        "headers": headers or {},
    }

    try:
        http_status = HTTPStatus(status_code)
    except ValueError:
        # Handle unknown status codes
        return CollectorError(
            f"Unknown HTTP error from {data_source or 'data source'}: HTTP {status_code}",
            data_source=data_source,
            operation=operation,
            request_params=request_params,
            http_details=http_details,
        )

    # Handle specific authentication errors
    if status_code == HTTPStatus.UNAUTHORIZED:
        return AuthenticationError(
            f"Authentication failed for {data_source or 'data source'}: HTTP {status_code}",
            data_source=data_source,
            operation=operation,
            request_params=request_params,
            http_details=http_details,
        )
    if status_code == HTTPStatus.FORBIDDEN:
        return AuthenticationError(
            f"Access forbidden for {data_source or 'data source'}: HTTP {status_code}",
            data_source=data_source,
            operation=operation,
            request_params=request_params,
            http_details=http_details,
        )

    # Handle specific data availability errors
    if status_code == HTTPStatus.NOT_FOUND:
        return DataUnavailableError(
            f"Data not found for {data_source or 'data source'}: HTTP {status_code}",
            data_source=data_source,
            operation=operation,
            request_params=request_params,
            http_details=http_details,
        )

    # Handle rate limiting
    if status_code == HTTPStatus.TOO_MANY_REQUESTS:
        return RateLimitError(
            f"Rate limit exceeded for {data_source or 'data source'}: HTTP {status_code}",
            data_source=data_source,
            operation=operation,
            request_params=request_params,
            http_details=http_details,
        )

    # Use HTTPStatus properties for broad categorization
    if http_status.is_server_error:
        return DataSourceConnectionError(
            f"Server error from {data_source or 'data source'}: HTTP {status_code}",
            data_source=data_source,
            operation=operation,
            request_params=request_params,
            http_details=http_details,
        )
    if http_status.is_client_error:
        return DataFormatError(
            f"Client error from {data_source or 'data source'}: HTTP {status_code}",
            data_source=data_source,
            operation=operation,
            request_params=request_params,
            http_details=http_details,
        )

    # Handle all other status codes
    return CollectorError(
        f"HTTP error from {data_source or 'data source'}: HTTP {status_code}",
        data_source=data_source,
        operation=operation,
        request_params=request_params,
        http_details=http_details,
    )


def create_timeout_error(
    timeout_type: str,
    timeout_value: float,
    data_source: str | None = None,
    operation: str | None = None,
    request_params: dict[str, Any] | None = None,
) -> RequestTimeoutError:
    """Create a timeout error with standardized context.

    Args:
        timeout_type: Type of timeout ("connection", "read", "total")
        timeout_value: Timeout value in seconds
        data_source: Identifier for the data source
        operation: Operation being performed when timeout occurred
        request_params: Parameters of the timed-out request

    Returns:
        RequestTimeoutError with timeout context
    """
    return RequestTimeoutError(
        f"{timeout_type.title()} timeout ({timeout_value}s) for {data_source or 'data source'}",
        data_source=data_source,
        operation=operation,
        request_params=request_params,
        context={
            "timeout_type": timeout_type,
            "timeout_value": timeout_value,
        },
    )


def create_data_format_error(  # noqa: PLR0913
    format_issue: str,
    expected_format: str | None = None,
    received_format: str | None = None,
    data_source: str | None = None,
    operation: str | None = None,
    request_params: dict[str, Any] | None = None,
    sample_data: str | None = None,
) -> DataFormatError:
    """Create a data format error with detailed context.

    Args:
        format_issue: Description of the format issue
        expected_format: Expected data format (e.g., "XML", "JSON")
        received_format: Actual received format
        data_source: Identifier for the data source
        operation: Operation being performed when error occurred
        request_params: Parameters of the failed request
        sample_data: Sample of the problematic data (truncated for logging)

    Returns:
        DataFormatError with format context
    """
    return DataFormatError(
        f"Data format error from {data_source or 'data source'}: {format_issue}",
        data_source=data_source,
        operation=operation,
        request_params=request_params,
        context={
            "format_issue": format_issue,
            "expected_format": expected_format,
            "received_format": received_format,
            "sample_data": sample_data[:500] if sample_data else None,
        },
    )
