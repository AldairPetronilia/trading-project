"""
Custom exception hierarchy for data collection operations.

This module defines a set of domain-specific exceptions that provide structured
error information for data collection failures. The exceptions support context
preservation, proper exception chaining, and clear classification of different
failure scenarios, such as network issues, API rate limiting, and data format errors.

The base exception, `CollectorError`, captures essential context about the operation,
while specialized subclasses provide specific details for different error conditions.
This allows for robust error handling and monitoring in the data collection layer.
"""

from typing import Any


class CollectorError(Exception):
    """
    Base class for collector exceptions with structured error information.

    Provides a common structure for all data collection errors, including the
    collector type, the operation being performed, and additional context. This
    enables consistent error handling and logging across different collectors.
    """

    def __init__(
        self,
        message: str,
        *,
        collector_type: str | None = None,
        operation: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Initializes the CollectorError with structured information.

        Args:
            message: A human-readable error message describing the failure.
            collector_type: The type or name of the collector that raised the error.
            operation: The specific operation that failed (e.g., 'health_check', 'collect_load_data').
            context: A dictionary containing additional context for debugging.
        """
        super().__init__(message)
        self.message = message
        self.collector_type = collector_type
        self.operation = operation
        self.context = context or {}

    def __str__(self) -> str:
        """
        Returns a formatted string representation of the exception.
        """
        parts = [f"[{self.__class__.__name__}] {self.message}"]
        if self.collector_type:
            parts.append(f"  - Collector: {self.collector_type}")
        if self.operation:
            parts.append(f"  - Operation: {self.operation}")
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"  - Context: {{{context_str}}}")
        return "\n".join(parts)


class DataSourceConnectionError(CollectorError):
    """
    Exception raised for network-related connection errors.

    This includes failures to establish a connection with the data source,
    DNS resolution errors, or other network-level issues.
    """


class ApiRateLimitError(CollectorError):
    """
    Exception raised for API rate limit violations.

    This error indicates that the collector has exceeded the allowed number
    of requests to the data source's API.
    """


class AuthenticationError(CollectorError):
    """
    Exception raised for authentication failures.

    This can be due to an invalid API token, expired credentials, or insufficient
    permissions to access the requested resource.
    """


class DataFormatError(CollectorError):
    """
    Exception raised for data format and parsing errors.

    This error occurs when the data received from the source is malformed,
    unexpected, or cannot be parsed correctly.
    """


class RequestTimeoutError(CollectorError):
    """
    Exception raised for request timeouts.

    This indicates that a request to the data source did not complete within
    the configured timeout period.
    """


class DataSourceUnavailableError(CollectorError):
    """
    Exception raised when a data source is unavailable or unreachable.

    This may be due to maintenance, server-side errors, or other issues
    that make the data source temporarily inaccessible.
    """


class InvalidParameterError(CollectorError):
    """
    Exception raised for invalid parameters or configuration settings.

    This error occurs when the parameters provided for a data collection
    request are invalid or inconsistent with the data source's requirements.
    """
