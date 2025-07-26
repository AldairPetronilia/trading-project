"""
Unit tests for the collector exception hierarchy.

This test suite validates the behavior of the custom exception classes defined in
`app.exceptions.collector_errors`. It ensures that the exceptions correctly
store and format context information, support proper exception chaining, and
maintain the intended class hierarchy.

The tests cover:
- Correct attribute assignment in the constructor.
- Accurate and readable string formatting for logs and debugging.
- Preservation of the original exception cause for proper chaining.
- Verification of the inheritance structure using `isinstance`.
"""

import pytest
from app.exceptions.collector_errors import (
    ApiRateLimitError,
    AuthenticationError,
    CollectorError,
    DataFormatError,
    DataSourceConnectionError,
    DataSourceUnavailableError,
    InvalidParameterError,
    RequestTimeoutError,
)


class TestCollectorError:
    """Test suite for the CollectorError exception hierarchy."""

    def test_initialization_with_all_attributes(self) -> None:
        """
        Tests that CollectorError correctly initializes with all optional attributes.
        """
        message = "Test error message"
        collector_type = "TestCollector"
        operation = "test_operation"
        context = {"key": "value", "id": 123}

        err = CollectorError(
            message,
            collector_type=collector_type,
            operation=operation,
            context=context,
        )

        assert err.message == message
        assert err.collector_type == collector_type
        assert err.operation == operation
        assert err.context == context

    def test_initialization_with_minimal_attributes(self) -> None:
        """
        Tests that CollectorError initializes correctly with only the required message.
        """
        message = "Minimal error"
        err = CollectorError(message)

        assert err.message == message
        assert err.collector_type is None
        assert err.operation is None
        assert err.context == {}

    def test_str_representation_with_all_attributes(self) -> None:
        """
        Tests the string formatting when all attributes are present.
        """
        err = CollectorError(
            "Connection failed",
            collector_type="EntsoeCollector",
            operation="collect_load_data",
            context={"area": "DE", "retries": 3},
        )

        expected_str = (
            "[CollectorError] Connection failed\n"
            "  - Collector: EntsoeCollector\n"
            "  - Operation: collect_load_data\n"
            "  - Context: {area=DE, retries=3}"
        )
        assert str(err) == expected_str

    def test_str_representation_with_minimal_attributes(self) -> None:
        """
        Tests the string formatting with only the required message.
        """
        err = CollectorError("A simple error occurred")
        expected_str = "[CollectorError] A simple error occurred"
        assert str(err) == expected_str

    def test_str_representation_for_subclass(self) -> None:
        """
        Tests that the string formatting correctly uses the subclass name.
        """
        err = ApiRateLimitError("Rate limit exceeded")
        expected_str = "[ApiRateLimitError] Rate limit exceeded"
        assert str(err) == expected_str

    def test_exception_chaining(self) -> None:
        """
        Tests that the exception correctly preserves the original cause.
        """
        original_exception = ValueError("Original cause")
        error_message = "Wrapper exception"

        def _raise_error() -> None:
            raise CollectorError(error_message) from original_exception

        with pytest.raises(CollectorError) as excinfo:
            _raise_error()
        assert excinfo.value.__cause__ is original_exception

    def test_inheritance_hierarchy(self) -> None:
        """
        Tests that all specific exceptions are subclasses of CollectorError.
        """
        subclasses = [
            DataSourceConnectionError,
            ApiRateLimitError,
            AuthenticationError,
            DataFormatError,
            RequestTimeoutError,
            DataSourceUnavailableError,
            InvalidParameterError,
        ]

        for subclass in subclasses:
            instance = subclass("test")
            assert isinstance(instance, CollectorError)
            assert isinstance(instance, Exception)
