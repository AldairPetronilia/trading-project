from datetime import UTC, datetime, timezone
from typing import Any

import pytest
from app.exceptions.collector_exceptions import (
    AuthenticationError,
    CollectorConfigurationError,
    CollectorError,
    DataFormatError,
    DataSourceConnectionError,
    DataUnavailableError,
    QuotaExceededError,
    RateLimitError,
    RequestTimeoutError,
    create_data_format_error,
    create_timeout_error,
    map_http_error_to_collector_error,
)


class TestCollectorError:
    """Test the base CollectorError class."""

    def test_collector_error_basic_creation(self) -> None:
        error = CollectorError("Test message")

        assert str(error) == "Test message"
        assert error.message == "Test message"
        assert error.data_source is None
        assert error.operation is None
        assert error.request_params == {}
        assert error.http_details == {}
        assert error.retry_context == {}
        assert error.context == {}
        assert isinstance(error.timestamp, datetime)

    def test_collector_error_full_context(self) -> None:
        request_params = {"start_time": "2024-01-01", "end_time": "2024-01-02"}
        http_details = {"status_code": 500, "response_body": "Server error"}
        retry_context = {"attempt": 2, "max_attempts": 3}
        context = {"custom_field": "custom_value"}

        error = CollectorError(
            "Test message with context",
            data_source="entsoe",
            operation="collect_load_data",
            request_params=request_params,
            http_details=http_details,
            retry_context=retry_context,
            context=context,
        )

        assert error.message == "Test message with context"
        assert error.data_source == "entsoe"
        assert error.operation == "collect_load_data"
        assert error.request_params == request_params
        assert error.http_details == http_details
        assert error.retry_context == retry_context
        assert error.context == context

    def test_collector_error_timestamp_within_bounds(self) -> None:
        before = datetime.now(UTC)
        error = CollectorError("Test message")
        after = datetime.now(UTC)

        assert before <= error.timestamp <= after


class TestCollectorErrorHierarchy:
    """Test the inheritance hierarchy of collector exceptions."""

    def test_all_exceptions_inherit_from_collector_error(self) -> None:
        exceptions = [
            DataSourceConnectionError,
            RateLimitError,
            DataFormatError,
            RequestTimeoutError,
            AuthenticationError,
            DataUnavailableError,
            QuotaExceededError,
            CollectorConfigurationError,
        ]

        for exception_class in exceptions:
            assert issubclass(exception_class, CollectorError)

    def test_exception_instance_creation(self) -> None:
        test_cases = [
            (DataSourceConnectionError, "Connection failed"),
            (RateLimitError, "Rate limit exceeded"),
            (DataFormatError, "Invalid format"),
            (RequestTimeoutError, "Request timed out"),
            (AuthenticationError, "Auth failed"),
            (DataUnavailableError, "No data available"),
            (QuotaExceededError, "Quota exceeded"),
            (CollectorConfigurationError, "Invalid config"),
        ]

        for exception_class, message in test_cases:
            error = exception_class(message, data_source="test_source")
            assert isinstance(error, CollectorError)
            assert error.message == message
            assert error.data_source == "test_source"


class TestHttpErrorMapping:
    """Test HTTP status code to exception mapping."""

    def test_authentication_errors(self) -> None:
        # Test 401 Unauthorized
        error = map_http_error_to_collector_error(
            status_code=401, data_source="entsoe", operation="collect_data"
        )
        assert isinstance(error, AuthenticationError)
        assert "Authentication failed" in error.message
        assert error.data_source == "entsoe"
        assert error.http_details["status_code"] == 401

        # Test 403 Forbidden
        error = map_http_error_to_collector_error(
            status_code=403, data_source="investing", operation="get_prices"
        )
        assert isinstance(error, AuthenticationError)
        assert "Access forbidden" in error.message

    def test_data_unavailable_error(self) -> None:
        error = map_http_error_to_collector_error(
            status_code=404,
            response_body="Not found",
            data_source="agsi",
            operation="get_storage_data",
        )
        assert isinstance(error, DataUnavailableError)
        assert "Data not found" in error.message
        assert error.http_details["response_body"] == "Not found"

    def test_rate_limit_error(self) -> None:
        headers = {"X-RateLimit-Remaining": "0", "Retry-After": "3600"}
        error = map_http_error_to_collector_error(
            status_code=429,
            headers=headers,
            data_source="marine_traffic",
            operation="track_vessels",
        )
        assert isinstance(error, RateLimitError)
        assert "Rate limit exceeded" in error.message
        assert error.http_details["headers"] == headers

    def test_server_errors(self) -> None:
        server_status_codes = [500, 502, 503, 504]

        for status_code in server_status_codes:
            error = map_http_error_to_collector_error(
                status_code=status_code, data_source="smard", operation="get_grid_data"
            )
            assert isinstance(error, DataSourceConnectionError)
            assert "Server error" in error.message
            assert error.http_details["status_code"] == status_code

    def test_client_errors(self) -> None:
        client_status_codes = [400, 422, 418]  # Various 4xx codes

        for status_code in client_status_codes:
            error = map_http_error_to_collector_error(
                status_code=status_code,
                data_source="weather_api",
                operation="get_forecast",
            )
            assert isinstance(error, DataFormatError)
            assert "Client error" in error.message

    def test_unknown_status_code(self) -> None:
        error = map_http_error_to_collector_error(
            status_code=999, data_source="unknown_api"
        )
        assert isinstance(error, CollectorError)
        assert type(error) is CollectorError  # Exact type, not subclass
        assert "Unknown HTTP error" in error.message

    def test_request_params_included(self) -> None:
        request_params = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-02",
            "market": "DE",
        }

        error = map_http_error_to_collector_error(
            status_code=404, request_params=request_params, data_source="test_source"
        )

        assert error.request_params == request_params

    def test_httpstatus_properties_used_correctly(self) -> None:
        # Test that HTTPStatus properties are used for categorization
        # Test a server error not specifically handled (e.g., 505)
        error = map_http_error_to_collector_error(
            status_code=505,  # HTTP Version Not Supported
            data_source="test_api",
        )
        assert isinstance(error, DataSourceConnectionError)
        assert "Server error" in error.message

        # Test a client error not specifically handled (e.g., 418)
        error = map_http_error_to_collector_error(
            status_code=418,  # I'm a teapot
            data_source="test_api",
        )
        assert isinstance(error, DataFormatError)
        assert "Client error" in error.message


class TestTimeoutErrorCreation:
    """Test timeout error creation utility."""

    def test_create_timeout_error_basic(self) -> None:
        error = create_timeout_error(
            timeout_type="connection",
            timeout_value=30.0,
            data_source="entsoe",
            operation="get_load_data",
        )

        assert isinstance(error, RequestTimeoutError)
        assert "Connection timeout (30.0s)" in error.message
        assert error.data_source == "entsoe"
        assert error.operation == "get_load_data"
        assert error.context["timeout_type"] == "connection"
        assert error.context["timeout_value"] == 30.0

    def test_create_timeout_error_types(self) -> None:
        timeout_types = ["connection", "read", "total"]

        for timeout_type in timeout_types:
            error = create_timeout_error(timeout_type=timeout_type, timeout_value=60.0)
            assert timeout_type.title() in error.message
            assert error.context["timeout_type"] == timeout_type

    def test_create_timeout_error_with_params(self) -> None:
        request_params = {"area": "DE", "start": "2024-01-01"}

        error = create_timeout_error(
            timeout_type="read",
            timeout_value=120.0,
            data_source="investing",
            operation="get_futures_prices",
            request_params=request_params,
        )

        assert error.request_params == request_params


class TestDataFormatErrorCreation:
    """Test data format error creation utility."""

    def test_create_data_format_error_basic(self) -> None:
        error = create_data_format_error(
            format_issue="Missing required field 'timestamp'",
            data_source="entsoe",
            operation="parse_gl_market_document",
        )

        assert isinstance(error, DataFormatError)
        assert "Data format error from entsoe" in error.message
        assert "Missing required field" in error.message
        assert error.context["format_issue"] == "Missing required field 'timestamp'"

    def test_create_data_format_error_full_context(self) -> None:
        sample_data = "<invalid>This is not valid XML</malformed>"

        error = create_data_format_error(
            format_issue="XML parsing failed",
            expected_format="XML",
            received_format="Malformed XML",
            data_source="entsoe",
            operation="parse_response",
            request_params={"document_type": "GL_MarketDocument"},
            sample_data=sample_data,
        )

        assert error.context["format_issue"] == "XML parsing failed"
        assert error.context["expected_format"] == "XML"
        assert error.context["received_format"] == "Malformed XML"
        assert error.context["sample_data"] == sample_data
        assert error.request_params["document_type"] == "GL_MarketDocument"

    def test_create_data_format_error_truncates_long_sample(self) -> None:
        long_sample = "x" * 1000  # 1000 characters

        error = create_data_format_error(
            format_issue="Too much data", sample_data=long_sample
        )

        # Should be truncated to 500 characters
        assert len(error.context["sample_data"]) == 500
        assert error.context["sample_data"] == "x" * 500

    def test_create_data_format_error_none_sample(self) -> None:
        error = create_data_format_error(format_issue="Unknown issue", sample_data=None)

        assert error.context["sample_data"] is None


class TestExceptionChaining:
    """Test exception chaining and context preservation."""

    def test_exception_can_be_chained(self) -> None:
        original_error = ValueError("Original error")

        def _raise_chained_error() -> None:
            message = "Collector error"
            raise CollectorError(message) from original_error

        with pytest.raises(CollectorError) as exc_info:
            _raise_chained_error()

        error = exc_info.value
        assert error.__cause__ is original_error
        assert str(error.__cause__) == "Original error"

    def test_mapping_preserves_original_error(self) -> None:
        # The map function doesn't automatically chain, but it accepts original_error
        # This test verifies the parameter is accepted (actual chaining would be done by caller)
        original_error = ConnectionError("Network failed")

        error = map_http_error_to_collector_error(
            status_code=503, data_source="entsoe", original_error=original_error
        )

        # The mapping function accepts the parameter but doesn't automatically chain
        # Chaining would be done by the caller like: raise mapped_error from original_error
        assert isinstance(error, DataSourceConnectionError)


class TestMultiSourceCompatibility:
    """Test that exceptions work with different data sources."""

    @pytest.mark.parametrize(
        ("data_source", "operation"),
        [
            ("entsoe", "collect_load_data"),
            ("investing", "get_futures_prices"),
            ("agsi", "get_storage_levels"),
            ("smard", "get_grid_data"),
            ("dwd", "get_weather_forecast"),
            ("marine_traffic", "track_lng_vessels"),
        ],
    )
    def test_exceptions_work_with_all_sources(
        self, data_source: str, operation: str
    ) -> None:
        error = CollectorError(
            f"Test error for {data_source}",
            data_source=data_source,
            operation=operation,
        )

        assert error.data_source == data_source
        assert error.operation == operation
        assert data_source in error.message

    def test_generic_request_params_structure(self) -> None:
        # Different data sources might have different parameter structures
        test_cases: list[dict[str, Any]] = [
            # ENTSO-E style
            {
                "area_code": "DE",
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-02T00:00:00Z",
                "business_type": "A65",
            },
            # Investing.com style
            {
                "symbol": "TTF",
                "timeframe": "1D",
                "from_date": "2024-01-01",
                "to_date": "2024-01-02",
            },
            # Weather API style
            {
                "latitude": 52.5200,
                "longitude": 13.4050,
                "forecast_hours": 48,
                "model": "ICON-EU",
            },
        ]

        for params in test_cases:
            error = CollectorError(
                "Test with different param structures", request_params=params
            )
            assert error.request_params == params
