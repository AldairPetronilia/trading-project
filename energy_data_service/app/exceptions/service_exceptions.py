"""
Service-level exception hierarchy for business logic operations.

This module defines a comprehensive set of exceptions for handling errors that
occur during service orchestration, providing structured error context for
debugging complex service interactions and operation failures.

Key Features:
- Service-level error hierarchy with operation tracking
- HTTP status code mapping for API integration
- Structured error logging for monitoring and debugging
- Context preservation for distributed debugging
- Backfill-specific exceptions with progress tracking
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID

    from .processor_exceptions import ProcessorError


class ServiceError(Exception):
    """
    Base exception for all service-level errors.

    This exception serves as the root of the service exception hierarchy,
    providing common functionality for error context preservation, operation
    tracking, and structured error information for service orchestration failures.

    Attributes:
        service_name: The name of the service that generated the error
        operation: The specific operation that failed
        context: Additional context information about the error
        operation_id: Unique identifier for the operation (for tracing)
        timing_info: Performance timing data when available
    """

    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
        operation: str | None = None,
        context: dict[str, Any] | None = None,
        operation_id: str | UUID | None = None,
        timing_info: dict[str, float] | None = None,
    ) -> None:
        """
        Initialize service error with detailed context.

        Args:
            message: Human-readable error description
            service_name: Name of the service that failed
            operation: Specific operation that caused the error
            context: Additional context information for debugging
            operation_id: Unique identifier for operation tracking
            timing_info: Performance timing data for the failed operation
        """
        super().__init__(message)
        self.service_name = service_name or "unknown_service"
        self.operation = operation or "unknown_operation"
        self.context = context or {}
        self.operation_id = str(operation_id) if operation_id else None
        self.timing_info = timing_info or {}
        self.timestamp = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert exception to dictionary for structured logging.

        Returns:
            Dictionary representation of the error with all context
        """
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "service_name": self.service_name,
            "operation": self.operation,
            "context": self.context,
            "operation_id": self.operation_id,
            "timing_info": self.timing_info,
            "timestamp": self.timestamp.isoformat(),
        }

    def get_http_status_code(self) -> int:
        """
        Get appropriate HTTP status code for this error type.

        Returns:
            HTTP status code (500 for service errors by default)
        """
        return 500  # Internal Server Error


class GapDetectionError(ServiceError):
    """
    Exception raised when gap detection fails.

    This exception is raised when the service cannot properly identify
    missing data periods, database queries fail, or gap analysis logic
    encounters unexpected conditions.

    Attributes:
        area_code: The area code being analyzed for gaps
        endpoint_name: The endpoint name being analyzed
        detection_type: Type of gap detection that failed
        query_context: Database query context when available
    """

    def __init__(
        self,
        message: str,
        area_code: str | None = None,
        endpoint_name: str | None = None,
        detection_type: str | None = None,
        query_context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize gap detection error.

        Args:
            message: Human-readable error description
            area_code: Area code being analyzed
            endpoint_name: Endpoint name being analyzed
            detection_type: Type of detection that failed
            query_context: Database query context for debugging
            **kwargs: Additional context passed to parent class
        """
        super().__init__(message, service_name="gap_detection", **kwargs)
        self.area_code = area_code
        self.endpoint_name = endpoint_name
        self.detection_type = detection_type or "unknown_detection"

        # Add to context
        self.context.update(
            {
                "area_code": area_code,
                "endpoint_name": endpoint_name,
                "detection_type": self.detection_type,
                "query_context": query_context or {},
            }
        )

    def get_http_status_code(self) -> int:
        """Get HTTP status code for gap detection errors."""
        return 422  # Unprocessable Entity


class CollectionOrchestrationError(ServiceError):
    """
    Exception raised when collection orchestration fails.

    This exception is raised when the service fails to coordinate
    data collection across multiple collectors, processors, or repositories,
    or when the orchestration logic encounters unexpected states.

    Attributes:
        areas_affected: List of area codes affected by the failure
        endpoints_affected: List of endpoint names affected
        orchestration_stage: Stage of orchestration where failure occurred
        partial_results: Any partial results collected before failure
    """

    def __init__(
        self,
        message: str,
        areas_affected: list[str] | None = None,
        endpoints_affected: list[str] | None = None,
        orchestration_stage: str | None = None,
        partial_results: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize collection orchestration error.

        Args:
            message: Human-readable error description
            areas_affected: Area codes affected by the orchestration failure
            endpoints_affected: Endpoint names affected by the failure
            orchestration_stage: Stage where orchestration failed
            partial_results: Any partial results collected before failure
            **kwargs: Additional context passed to parent class
        """
        super().__init__(message, service_name="collection_orchestration", **kwargs)
        self.areas_affected = areas_affected or []
        self.endpoints_affected = endpoints_affected or []
        self.orchestration_stage = orchestration_stage or "unknown_stage"
        self.partial_results = partial_results or {}

        # Add to context
        self.context.update(
            {
                "areas_affected": self.areas_affected,
                "endpoints_affected": self.endpoints_affected,
                "orchestration_stage": self.orchestration_stage,
                "partial_results_summary": {
                    "total_areas": len(self.areas_affected),
                    "total_endpoints": len(self.endpoints_affected),
                    "has_partial_results": bool(self.partial_results),
                },
            }
        )

    def get_http_status_code(self) -> int:
        """Get HTTP status code for collection orchestration errors."""
        return 502  # Bad Gateway


class ChunkingError(ServiceError):
    """
    Exception raised when data chunking operations fail.

    This exception is raised when the service fails to split large
    date ranges into manageable chunks, chunk size calculations fail,
    or chunk processing encounters unexpected conditions.

    Attributes:
        start_time: Start time of the period being chunked
        end_time: End time of the period being chunked
        chunk_size_days: Chunk size that caused the error
        total_chunks: Total number of chunks being processed
        failed_chunk_index: Index of the chunk that failed
    """

    def __init__(
        self,
        message: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        chunk_size_days: int | None = None,
        total_chunks: int | None = None,
        failed_chunk_index: int | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize chunking error.

        Args:
            message: Human-readable error description
            start_time: Start time of the period being chunked
            end_time: End time of the period being chunked
            chunk_size_days: Size of chunks in days
            total_chunks: Total number of chunks
            failed_chunk_index: Index of the chunk that failed (0-based)
            **kwargs: Additional context passed to parent class
        """
        super().__init__(message, service_name="chunking", **kwargs)
        self.start_time = start_time
        self.end_time = end_time
        self.chunk_size_days = chunk_size_days
        self.total_chunks = total_chunks
        self.failed_chunk_index = failed_chunk_index

        # Add to context
        self.context.update(
            {
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "chunk_size_days": chunk_size_days,
                "total_chunks": total_chunks,
                "failed_chunk_index": failed_chunk_index,
            }
        )

    def get_http_status_code(self) -> int:
        """Get HTTP status code for chunking errors."""
        return 422  # Unprocessable Entity


class BackfillError(ServiceError):
    """
    Base exception for backfill operation errors.

    This exception serves as the base for all backfill-related errors,
    providing common functionality for progress tracking, operation
    context, and historical data collection error handling.

    Attributes:
        backfill_id: Unique identifier for the backfill operation
        area_code: Area code being backfilled
        endpoint_name: Endpoint name being backfilled
        progress_info: Current progress information
    """

    def __init__(
        self,
        message: str,
        backfill_id: int | str | None = None,
        area_code: str | None = None,
        endpoint_name: str | None = None,
        progress_info: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize backfill error.

        Args:
            message: Human-readable error description
            backfill_id: Unique identifier for the backfill operation
            area_code: Area code being backfilled
            endpoint_name: Endpoint name being backfilled
            progress_info: Current progress information
            **kwargs: Additional context passed to parent class
        """
        super().__init__(message, service_name="backfill", **kwargs)
        self.backfill_id = str(backfill_id) if backfill_id else None
        self.area_code = area_code
        self.endpoint_name = endpoint_name
        self.progress_info = progress_info or {}

        # Add to context
        self.context.update(
            {
                "backfill_id": self.backfill_id,
                "area_code": area_code,
                "endpoint_name": endpoint_name,
                "progress_info": self.progress_info,
            }
        )

    def get_http_status_code(self) -> int:
        """Get HTTP status code for backfill errors."""
        return 500  # Internal Server Error


class BackfillProgressError(BackfillError):
    """
    Exception raised when backfill progress tracking fails.

    This exception is raised when progress persistence fails,
    resume operations encounter errors, or progress calculation
    logic encounters unexpected states.

    Attributes:
        progress_operation: The progress operation that failed
        database_error: Original database error if applicable
        progress_state: Current progress state when error occurred
    """

    def __init__(
        self,
        message: str,
        progress_operation: str | None = None,
        database_error: Exception | None = None,
        progress_state: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize backfill progress error.

        Args:
            message: Human-readable error description
            progress_operation: Operation that failed (e.g., 'save', 'resume', 'update')
            database_error: Original database error if applicable
            progress_state: Current progress state when error occurred
            **kwargs: Additional context passed to parent class
        """
        super().__init__(message, operation="progress_tracking", **kwargs)
        self.progress_operation = progress_operation or "unknown_operation"
        self.database_error = database_error
        self.progress_state = progress_state or {}

        # Add to context
        self.context.update(
            {
                "progress_operation": self.progress_operation,
                "database_error": str(database_error) if database_error else None,
                "progress_state": self.progress_state,
            }
        )

    def get_http_status_code(self) -> int:
        """Get HTTP status code for progress errors."""
        return 500  # Internal Server Error


class BackfillCoverageError(BackfillError):
    """
    Exception raised when backfill coverage analysis fails.

    This exception is raised when coverage analysis cannot determine
    missing historical data periods, database coverage queries fail,
    or coverage calculation logic encounters unexpected conditions.

    Attributes:
        coverage_operation: The coverage operation that failed
        analysis_period: Time period being analyzed for coverage
        expected_data_points: Expected number of data points
        actual_data_points: Actual number of data points found
    """

    def __init__(
        self,
        message: str,
        coverage_operation: str | None = None,
        analysis_period: dict[str, datetime] | None = None,
        expected_data_points: int | None = None,
        actual_data_points: int | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize backfill coverage error.

        Args:
            message: Human-readable error description
            coverage_operation: Operation that failed (e.g., 'analyze', 'calculate', 'validate')
            analysis_period: Time period being analyzed
            expected_data_points: Expected number of data points
            actual_data_points: Actual number of data points found
            **kwargs: Additional context passed to parent class
        """
        super().__init__(message, operation="coverage_analysis", **kwargs)
        self.coverage_operation = coverage_operation or "unknown_operation"
        self.analysis_period = analysis_period or {}
        self.expected_data_points = expected_data_points
        self.actual_data_points = actual_data_points

        # Add to context
        self.context.update(
            {
                "coverage_operation": self.coverage_operation,
                "analysis_period": {
                    k: v.isoformat() if isinstance(v, datetime) else str(v)
                    for k, v in self.analysis_period.items()
                },
                "expected_data_points": expected_data_points,
                "actual_data_points": actual_data_points,
                "coverage_gap": (
                    expected_data_points - actual_data_points
                    if expected_data_points is not None
                    and actual_data_points is not None
                    else None
                ),
            }
        )

    def get_http_status_code(self) -> int:
        """Get HTTP status code for coverage errors."""
        return 422  # Unprocessable Entity


class BackfillResourceError(BackfillError):
    """
    Exception raised when backfill resource limits are exceeded.

    This exception is raised when backfill operations exceed
    configured resource limits, concurrent operation limits are
    violated, or system resources are insufficient for the operation.

    Attributes:
        resource_type: Type of resource that was exceeded
        limit_value: The limit that was exceeded
        current_value: Current value that exceeded the limit
        resource_context: Additional resource context
    """

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        limit_value: float | None = None,
        current_value: float | None = None,
        resource_context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize backfill resource error.

        Args:
            message: Human-readable error description
            resource_type: Type of resource (e.g., 'concurrent_operations', 'memory', 'api_calls')
            limit_value: The configured limit
            current_value: Current value that exceeded the limit
            resource_context: Additional resource context
            **kwargs: Additional context passed to parent class
        """
        super().__init__(message, operation="resource_management", **kwargs)
        self.resource_type = resource_type or "unknown_resource"
        self.limit_value = limit_value
        self.current_value = current_value
        self.resource_context = resource_context or {}

        # Add to context
        self.context.update(
            {
                "resource_type": self.resource_type,
                "limit_value": limit_value,
                "current_value": current_value,
                "resource_context": self.resource_context,
            }
        )

    def get_http_status_code(self) -> int:
        """Get HTTP status code for resource errors."""
        return 429  # Too Many Requests


class BackfillDataQualityError(BackfillError):
    """
    Exception raised when backfill data quality validation fails.

    This exception is raised when historical data fails quality
    checks, completeness validation fails, or data integrity
    issues are detected during backfill operations.

    Attributes:
        quality_check: The quality check that failed
        validation_results: Results of data validation
        data_sample: Sample of problematic data
        quality_metrics: Quality metrics calculated
    """

    def __init__(
        self,
        message: str,
        quality_check: str | None = None,
        validation_results: dict[str, Any] | None = None,
        data_sample: list[dict[str, Any]] | None = None,
        quality_metrics: dict[str, float] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize backfill data quality error.

        Args:
            message: Human-readable error description
            quality_check: The quality check that failed
            validation_results: Results of data validation
            data_sample: Sample of problematic data (truncated for logging)
            quality_metrics: Quality metrics calculated
            **kwargs: Additional context passed to parent class
        """
        super().__init__(message, operation="data_quality_validation", **kwargs)
        self.quality_check = quality_check or "unknown_check"
        self.validation_results = validation_results or {}
        self.data_sample = data_sample or []
        self.quality_metrics = quality_metrics or {}

        # Add to context (truncate data sample for logging)
        self.context.update(
            {
                "quality_check": self.quality_check,
                "validation_results": self.validation_results,
                "data_sample_count": len(self.data_sample),
                "data_sample": self.data_sample[:5],  # Only first 5 items
                "quality_metrics": self.quality_metrics,
            }
        )

    def get_http_status_code(self) -> int:
        """Get HTTP status code for data quality errors."""
        return 422  # Unprocessable Entity


# Service exception mapping utilities


def create_service_error_from_processor_error(
    processor_error: ProcessorError,
    service_name: str | None = None,
    operation: str | None = None,
) -> ServiceError:
    """
    Convert a processor error to a service error with additional context.

    Args:
        processor_error: The original processor error
        service_name: Name of the service that encountered the error
        operation: Service operation that was being performed

    Returns:
        ServiceError with processor context preserved
    """
    return ServiceError(
        message=f"Service operation failed due to processor error: {processor_error}",
        service_name=service_name,
        operation=operation,
        context={
            "original_error_type": processor_error.__class__.__name__,
            "processor_context": processor_error.to_dict()
            if hasattr(processor_error, "to_dict")
            else {},
        },
    )


def create_backfill_error_from_service_error(
    service_error: ServiceError,
    backfill_id: int | str | None = None,
    area_code: str | None = None,
    endpoint_name: str | None = None,
) -> BackfillError:
    """
    Convert a service error to a backfill error with backfill context.

    Args:
        service_error: The original service error
        backfill_id: ID of the backfill operation
        area_code: Area code being backfilled
        endpoint_name: Endpoint being backfilled

    Returns:
        BackfillError with service context preserved
    """
    return BackfillError(
        message=f"Backfill operation failed: {service_error}",
        backfill_id=backfill_id,
        area_code=area_code,
        endpoint_name=endpoint_name,
        context={
            "original_error_type": service_error.__class__.__name__,
            "service_context": service_error.to_dict(),
        },
    )
