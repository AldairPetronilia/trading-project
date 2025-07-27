"""Tests for processor exception hierarchy and functionality."""

from typing import Any

import pytest
from app.exceptions.processor_exceptions import (
    DataValidationError,
    DocumentParsingError,
    MappingError,
    ProcessorError,
    TimestampCalculationError,
    TransformationError,
)


class TestProcessorExceptionHierarchy:
    """Test suite for processor exception hierarchy."""

    def test_processor_error_inheritance(self) -> None:
        """Test that all processor exceptions inherit from ProcessorError."""
        exception_classes = [
            DocumentParsingError,
            DataValidationError,
            TimestampCalculationError,
            MappingError,
            TransformationError,
        ]

        for exception_class in exception_classes:
            assert issubclass(exception_class, ProcessorError)
            assert issubclass(exception_class, Exception)

    def test_processor_error_basic_functionality(self) -> None:
        """Test basic ProcessorError functionality."""
        error = ProcessorError(
            "Test error message",
            processor_type="TestProcessor",
            operation="test_operation",
            context={"key": "value"},
            input_count=100,
        )

        assert str(error) == "Test error message"
        assert error.processor_type == "TestProcessor"
        assert error.operation == "test_operation"
        assert error.context == {"key": "value"}
        assert error.input_count == 100

    def test_processor_error_default_values(self) -> None:
        """Test ProcessorError with default values."""
        error = ProcessorError("Simple error")

        assert str(error) == "Simple error"
        assert error.processor_type is None
        assert error.operation is None
        assert error.context == {}
        assert error.input_count is None

    def test_processor_error_to_dict(self) -> None:
        """Test ProcessorError to_dict method for structured logging."""
        error = ProcessorError(
            "Test error",
            processor_type="TestProcessor",
            operation="test_op",
            context={"test": "data"},
            input_count=42,
        )

        result = error.to_dict()

        expected = {
            "error_type": "ProcessorError",
            "message": "Test error",
            "processor_type": "TestProcessor",
            "operation": "test_op",
            "input_count": 42,
            "context": {"test": "data"},
        }

        assert result == expected

    def test_processor_error_http_status_code(self) -> None:
        """Test default HTTP status code for ProcessorError."""
        error = ProcessorError("Test error")
        assert error.get_http_status_code() == 422  # Unprocessable Entity


class TestDocumentParsingError:
    """Test suite for DocumentParsingError."""

    def test_document_parsing_error_creation(self) -> None:
        """Test DocumentParsingError creation with all parameters."""
        error = DocumentParsingError(
            "Failed to parse XML",
            document_type="GL_MarketDocument",
            document_id="DOC123",
            parsing_stage="time_series_extraction",
            processor_type="TestProcessor",
        )

        assert str(error) == "Failed to parse XML"
        assert error.document_type == "GL_MarketDocument"
        assert error.document_id == "DOC123"
        assert error.parsing_stage == "time_series_extraction"
        assert error.processor_type == "TestProcessor"

    def test_document_parsing_error_context_update(self) -> None:
        """Test that DocumentParsingError updates context with document info."""
        error = DocumentParsingError(
            "Parse error",
            document_type="TestDoc",
            document_id="ID123",
            parsing_stage="validation",
        )

        expected_context = {
            "document_type": "TestDoc",
            "document_id": "ID123",
            "parsing_stage": "validation",
        }

        assert error.context == expected_context

    def test_document_parsing_error_http_status(self) -> None:
        """Test HTTP status code for DocumentParsingError."""
        error = DocumentParsingError("Parse error")
        assert error.get_http_status_code() == 400  # Bad Request


class TestDataValidationError:
    """Test suite for DataValidationError."""

    def test_data_validation_error_creation(self) -> None:
        """Test DataValidationError creation with all parameters."""
        error = DataValidationError(
            "Invalid quantity value",
            field="quantity",
            value=-100.5,
            validation_rule="must_be_positive",
            expected_type="Decimal",
        )

        assert str(error) == "Invalid quantity value"
        assert error.field == "quantity"
        assert error.value == -100.5
        assert error.validation_rule == "must_be_positive"
        assert error.expected_type == "Decimal"

    def test_data_validation_error_context_update(self) -> None:
        """Test that DataValidationError updates context with validation info."""
        error = DataValidationError(
            "Validation failed",
            field="test_field",
            value=123,
            validation_rule="test_rule",
            expected_type="str",
        )

        expected_context = {
            "field": "test_field",
            "value": "123",
            "validation_rule": "test_rule",
            "expected_type": "str",
        }

        assert error.context == expected_context

    def test_data_validation_error_none_value(self) -> None:
        """Test DataValidationError with None value."""
        error = DataValidationError(
            "Value is None",
            field="required_field",
            value=None,
        )

        assert error.context["value"] is None

    def test_data_validation_error_http_status(self) -> None:
        """Test HTTP status code for DataValidationError."""
        error = DataValidationError("Validation error")
        assert error.get_http_status_code() == 422  # Unprocessable Entity


class TestTimestampCalculationError:
    """Test suite for TimestampCalculationError."""

    def test_timestamp_calculation_error_creation(self) -> None:
        """Test TimestampCalculationError creation with all parameters."""
        error = TimestampCalculationError(
            "Failed to calculate timestamp",
            resolution="PT15M",
            period_start="2023-01-01T00:00:00Z",
            period_end="2023-01-01T01:00:00Z",
            position=5,
        )

        assert str(error) == "Failed to calculate timestamp"
        assert error.resolution == "PT15M"
        assert error.period_start == "2023-01-01T00:00:00Z"
        assert error.period_end == "2023-01-01T01:00:00Z"
        assert error.position == 5

    def test_timestamp_calculation_error_context_update(self) -> None:
        """Test that TimestampCalculationError updates context."""
        error = TimestampCalculationError(
            "Timestamp error",
            resolution="PT60M",
            position=10,
        )

        expected_context = {
            "resolution": "PT60M",
            "period_start": None,
            "period_end": None,
            "position": 10,
        }

        assert error.context == expected_context

    def test_timestamp_calculation_error_http_status(self) -> None:
        """Test HTTP status code for TimestampCalculationError."""
        error = TimestampCalculationError("Timestamp error")
        assert error.get_http_status_code() == 422  # Unprocessable Entity


class TestMappingError:
    """Test suite for MappingError."""

    def test_mapping_error_creation(self) -> None:
        """Test MappingError creation with all parameters."""
        error = MappingError(
            "Failed to map code",
            source_code="A02",
            source_type="ProcessType",
            target_type="EnergyDataType",
            available_mappings=["A01", "A16", "A31"],
        )

        assert str(error) == "Failed to map code"
        assert error.source_code == "A02"
        assert error.source_type == "ProcessType"
        assert error.target_type == "EnergyDataType"
        assert error.available_mappings == ["A01", "A16", "A31"]

    def test_mapping_error_default_mappings(self) -> None:
        """Test MappingError with default empty mappings list."""
        error = MappingError("Mapping failed")
        assert error.available_mappings == []

    def test_mapping_error_context_update(self) -> None:
        """Test that MappingError updates context with mapping info."""
        error = MappingError(
            "Map error",
            source_code="TEST",
            source_type="TestType",
            target_type="TargetType",
            available_mappings=["VALID1", "VALID2"],
        )

        expected_context = {
            "source_code": "TEST",
            "source_type": "TestType",
            "target_type": "TargetType",
            "available_mappings": ["VALID1", "VALID2"],
        }

        assert error.context == expected_context

    def test_mapping_error_http_status(self) -> None:
        """Test HTTP status code for MappingError."""
        error = MappingError("Mapping error")
        assert error.get_http_status_code() == 422  # Unprocessable Entity


class TestTransformationError:
    """Test suite for TransformationError."""

    def test_transformation_error_creation(self) -> None:
        """Test TransformationError creation with all parameters."""
        error = TransformationError(
            "Transformation failed",
            transformation_type="unit_conversion",
            source_value=100.5,
            target_type="Decimal",
            step="decimal_conversion",
        )

        assert str(error) == "Transformation failed"
        assert error.transformation_type == "unit_conversion"
        assert error.source_value == 100.5
        assert error.target_type == "Decimal"
        assert error.step == "decimal_conversion"

    def test_transformation_error_context_update(self) -> None:
        """Test that TransformationError updates context with transformation info."""
        error = TransformationError(
            "Transform error",
            transformation_type="test_transform",
            source_value={"complex": "object"},
            target_type="SimpleType",
            step="validation",
        )

        expected_context = {
            "transformation_type": "test_transform",
            "source_value": "{'complex': 'object'}",
            "target_type": "SimpleType",
            "step": "validation",
        }

        assert error.context == expected_context

    def test_transformation_error_none_source_value(self) -> None:
        """Test TransformationError with None source value."""
        error = TransformationError(
            "Transform error",
            source_value=None,
        )

        assert error.context["source_value"] is None

    def test_transformation_error_http_status(self) -> None:
        """Test HTTP status code for TransformationError."""
        error = TransformationError("Transform error")
        assert error.get_http_status_code() == 422  # Unprocessable Entity


class TestExceptionChaining:
    """Test exception chaining and context preservation."""

    def test_exception_chaining_context_preservation(self) -> None:
        """Test that exception chaining preserves context."""
        original_error = ValueError("Original error")

        def _raise_wrapped_error() -> None:
            msg = "Wrapped error"
            raise ProcessorError(
                msg,
                processor_type="TestProcessor",
                operation="test",
            ) from original_error

        with pytest.raises(ProcessorError) as exc_info:
            _raise_wrapped_error()

        e = exc_info.value
        assert str(e) == "Wrapped error"
        assert e.__cause__ is original_error
        assert e.processor_type == "TestProcessor"

    def test_nested_exception_context(self) -> None:
        """Test nested exception context handling."""

        def _raise_inner_error() -> None:
            inner_msg = "Inner error"
            raise ValueError(inner_msg)

        def _raise_parsing_error(inner: ValueError) -> None:
            parsing_msg = "Parsing failed"
            raise DocumentParsingError(
                parsing_msg,
                document_type="TestDoc",
                document_id="ID123",
            ) from inner

        def _raise_chained_error() -> None:
            try:
                _raise_inner_error()
            except ValueError as inner:
                _raise_parsing_error(inner)

        with pytest.raises(DocumentParsingError) as exc_info:
            _raise_chained_error()

        outer = exc_info.value
        # Verify the chain is preserved
        assert isinstance(outer.__cause__, ValueError)
        assert str(outer.__cause__) == "Inner error"

        # Verify specific context is preserved
        assert outer.document_type == "TestDoc"
        assert outer.document_id == "ID123"
