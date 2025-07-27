"""
Exception hierarchy for data processing operations.

This module defines a comprehensive set of exceptions for handling errors that
occur during data transformation processes, providing detailed context for
debugging complex data structures and business logic failures.
"""

from typing import Any


class ProcessorError(Exception):
    """
    Base exception for all data processing errors.

    This exception serves as the root of the processor exception hierarchy,
    providing common functionality for error context preservation and
    structured error information that aids in debugging and monitoring.

    Attributes:
        processor_type: The name of the processor that generated the error
        operation: The specific operation that failed
        context: Additional context information about the error
        input_count: Number of input items being processed when error occurred
    """

    def __init__(
        self,
        message: str,
        *,
        processor_type: str | None = None,
        operation: str | None = None,
        context: dict[str, Any] | None = None,
        input_count: int | None = None,
    ) -> None:
        """
        Initialize processor error with detailed context.

        Args:
            message: Human-readable error description
            processor_type: Name of the processor class that failed
            operation: Specific operation that caused the error
            context: Additional context information for debugging
            input_count: Number of input items being processed
        """
        super().__init__(message)
        self.processor_type = processor_type
        self.operation = operation
        self.context = context or {}
        self.input_count = input_count

    def to_dict(self) -> dict[str, Any]:
        """
        Convert exception to dictionary for structured logging.

        Returns:
            Dictionary representation of the error with all context
        """
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "processor_type": self.processor_type,
            "operation": self.operation,
            "input_count": self.input_count,
            "context": self.context,
        }

    def get_http_status_code(self) -> int:
        """
        Get appropriate HTTP status code for this error type.

        Returns:
            HTTP status code (422 for processing errors by default)
        """
        return 422  # Unprocessable Entity


class DocumentParsingError(ProcessorError):
    """
    Exception raised when document structure cannot be parsed.

    This exception is raised when the input document (XML, JSON, etc.)
    has an invalid or unexpected structure that prevents processing.

    Attributes:
        document_type: Type of document that failed to parse
        document_id: Identifier of the specific document
        parsing_stage: Stage of parsing where the error occurred
    """

    def __init__(
        self,
        message: str,
        *,
        document_type: str | None = None,
        document_id: str | None = None,
        parsing_stage: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize document parsing error.

        Args:
            message: Human-readable error description
            document_type: Type of document (e.g., 'GL_MarketDocument')
            document_id: Unique identifier of the document
            parsing_stage: Stage where parsing failed (e.g., 'time_series_extraction')
            **kwargs: Additional context passed to parent class
        """
        super().__init__(message, **kwargs)
        self.document_type = document_type
        self.document_id = document_id
        self.parsing_stage = parsing_stage

        # Add to context
        self.context.update(
            {
                "document_type": document_type,
                "document_id": document_id,
                "parsing_stage": parsing_stage,
            }
        )

    def get_http_status_code(self) -> int:
        """Get HTTP status code for document parsing errors."""
        return 400  # Bad Request


class DataValidationError(ProcessorError):
    """
    Exception raised when data fails business rule validation.

    This exception is raised when the data structure is valid but the
    content violates business rules, data quality requirements, or
    expected value ranges.

    Attributes:
        field: Name of the field that failed validation
        value: The invalid value that caused the error
        validation_rule: Description of the validation rule that was violated
        expected_type: Expected data type for the field
    """

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        value: Any = None,
        validation_rule: str | None = None,
        expected_type: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize data validation error.

        Args:
            message: Human-readable error description
            field: Name of the field that failed validation
            value: The value that caused the validation failure
            validation_rule: Description of the violated validation rule
            expected_type: Expected data type for the field
            **kwargs: Additional context passed to parent class
        """
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value
        self.validation_rule = validation_rule
        self.expected_type = expected_type

        # Add to context
        self.context.update(
            {
                "field": field,
                "value": str(value) if value is not None else None,
                "validation_rule": validation_rule,
                "expected_type": expected_type,
            }
        )

    def get_http_status_code(self) -> int:
        """Get HTTP status code for data validation errors."""
        return 422  # Unprocessable Entity


class TimestampCalculationError(ProcessorError):
    """
    Exception raised when timestamp calculation fails.

    This exception is raised when errors occur during timestamp parsing,
    resolution calculation, or time interval processing. This is critical
    for time-series data where accurate timestamps are essential.

    Attributes:
        resolution: The time resolution string that caused the error
        period_start: Start time of the period being processed
        period_end: End time of the period being processed
        position: Position within the time series where error occurred
    """

    def __init__(
        self,
        message: str,
        *,
        resolution: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
        position: int | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize timestamp calculation error.

        Args:
            message: Human-readable error description
            resolution: Time resolution string (e.g., 'PT15M', 'PT60M')
            period_start: ISO format start time of the period
            period_end: ISO format end time of the period
            position: Position in time series where error occurred
            **kwargs: Additional context passed to parent class
        """
        super().__init__(message, **kwargs)
        self.resolution = resolution
        self.period_start = period_start
        self.period_end = period_end
        self.position = position

        # Add to context
        self.context.update(
            {
                "resolution": resolution,
                "period_start": period_start,
                "period_end": period_end,
                "position": position,
            }
        )

    def get_http_status_code(self) -> int:
        """Get HTTP status code for timestamp calculation errors."""
        return 422  # Unprocessable Entity


class MappingError(ProcessorError):
    """
    Exception raised when code mapping operations fail.

    This exception is raised when mapping between different code systems
    fails, such as converting ENTSO-E ProcessType codes to internal
    EnergyDataType enums or mapping area codes between formats.

    Attributes:
        source_code: The original code that failed to map
        source_type: Type of the source code system
        target_type: Type of the target code system
        available_mappings: List of available mapping options
    """

    def __init__(
        self,
        message: str,
        *,
        source_code: str | None = None,
        source_type: str | None = None,
        target_type: str | None = None,
        available_mappings: list | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize mapping error.

        Args:
            message: Human-readable error description
            source_code: The code that failed to map
            source_type: Type of source code system (e.g., 'ProcessType')
            target_type: Type of target code system (e.g., 'EnergyDataType')
            available_mappings: List of valid mapping options
            **kwargs: Additional context passed to parent class
        """
        super().__init__(message, **kwargs)
        self.source_code = source_code
        self.source_type = source_type
        self.target_type = target_type
        self.available_mappings = available_mappings or []

        # Add to context
        self.context.update(
            {
                "source_code": source_code,
                "source_type": source_type,
                "target_type": target_type,
                "available_mappings": available_mappings,
            }
        )

    def get_http_status_code(self) -> int:
        """Get HTTP status code for mapping errors."""
        return 422  # Unprocessable Entity


class TransformationError(ProcessorError):
    """
    Exception raised when data transformation operations fail.

    This exception is raised when the core transformation logic fails,
    such as unit conversions, data type transformations, or calculation
    errors during the processing pipeline.

    Attributes:
        transformation_type: Type of transformation that failed
        source_value: Original value before transformation
        target_type: Expected result type after transformation
        step: Specific transformation step that failed
    """

    def __init__(
        self,
        message: str,
        *,
        transformation_type: str | None = None,
        source_value: Any = None,
        target_type: str | None = None,
        step: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize transformation error.

        Args:
            message: Human-readable error description
            transformation_type: Type of transformation (e.g., 'unit_conversion')
            source_value: Original value before transformation
            target_type: Expected result type
            step: Specific step in transformation pipeline
            **kwargs: Additional context passed to parent class
        """
        super().__init__(message, **kwargs)
        self.transformation_type = transformation_type
        self.source_value = source_value
        self.target_type = target_type
        self.step = step

        # Add to context
        self.context.update(
            {
                "transformation_type": transformation_type,
                "source_value": str(source_value) if source_value is not None else None,
                "target_type": target_type,
                "step": step,
            }
        )

    def get_http_status_code(self) -> int:
        """Get HTTP status code for transformation errors."""
        return 422  # Unprocessable Entity
