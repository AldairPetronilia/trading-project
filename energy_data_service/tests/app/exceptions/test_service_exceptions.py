"""
Unit tests for service exception hierarchy.

This module provides comprehensive unit tests for service-level exceptions,
covering error context preservation, HTTP status mapping, and structured logging.
"""

from datetime import UTC, datetime, timezone
from uuid import uuid4

import pytest
from app.exceptions.processor_exceptions import ProcessorError
from app.exceptions.service_exceptions import (
    BackfillCoverageError,
    BackfillDataQualityError,
    BackfillError,
    BackfillProgressError,
    BackfillResourceError,
    ChunkingError,
    CollectionOrchestrationError,
    GapDetectionError,
    ServiceError,
    create_backfill_error_from_service_error,
    create_service_error_from_processor_error,
)


class TestServiceError:
    """Test suite for ServiceError base class."""

    def test_service_error_basic_creation(self) -> None:
        """Test basic ServiceError creation."""
        error = ServiceError("Test message")

        assert str(error) == "Test message"
        assert error.service_name == "unknown_service"
        assert error.operation == "unknown_operation"
        assert error.context == {}
        assert error.operation_id is None
        assert error.timing_info == {}
        assert error.timestamp is not None

    def test_service_error_full_context(self) -> None:
        """Test ServiceError with full context."""
        operation_id = uuid4()
        context = {"key": "value"}
        timing_info = {"duration": 1.5, "db_query_time": 0.3}

        error = ServiceError(
            message="Test error",
            service_name="test_service",
            operation="test_operation",
            context=context,
            operation_id=operation_id,
            timing_info=timing_info,
        )

        assert error.service_name == "test_service"
        assert error.operation == "test_operation"
        assert error.context == context
        assert error.operation_id == str(operation_id)
        assert error.timing_info == timing_info

    def test_service_error_to_dict(self) -> None:
        """Test ServiceError to_dict method."""
        operation_id = "test-op-123"
        error = ServiceError(
            message="Test error",
            service_name="test_service",
            operation="test_operation",
            operation_id=operation_id,
        )

        result = error.to_dict()

        assert result["error_type"] == "ServiceError"
        assert result["message"] == "Test error"
        assert result["service_name"] == "test_service"
        assert result["operation"] == "test_operation"
        assert result["operation_id"] == operation_id
        assert "timestamp" in result

    def test_service_error_http_status_code(self) -> None:
        """Test ServiceError HTTP status code."""
        error = ServiceError("Test error")
        assert error.get_http_status_code() == 500


class TestGapDetectionError:
    """Test suite for GapDetectionError."""

    def test_gap_detection_error_creation(self) -> None:
        """Test GapDetectionError creation with gap context."""
        query_context = {"query": "SELECT * FROM data", "duration": 0.5}

        error = GapDetectionError(
            message="Gap detection failed",
            area_code="DE",
            endpoint_name="actual_load",
            detection_type="missing_periods",
            query_context=query_context,
        )

        assert error.area_code == "DE"
        assert error.endpoint_name == "actual_load"
        assert error.detection_type == "missing_periods"
        assert error.service_name == "gap_detection"
        assert error.context["area_code"] == "DE"
        assert error.context["query_context"] == query_context

    def test_gap_detection_error_http_status(self) -> None:
        """Test GapDetectionError HTTP status code."""
        error = GapDetectionError("Gap detection failed")
        assert error.get_http_status_code() == 422


class TestCollectionOrchestrationError:
    """Test suite for CollectionOrchestrationError."""

    def test_collection_orchestration_error_creation(self) -> None:
        """Test CollectionOrchestrationError creation with orchestration context."""
        areas_affected = ["DE", "FR"]
        endpoints_affected = ["actual_load", "day_ahead_forecast"]
        partial_results = {"DE": {"actual_load": 100}, "FR": {"actual_load": 50}}

        error = CollectionOrchestrationError(
            message="Orchestration failed",
            areas_affected=areas_affected,
            endpoints_affected=endpoints_affected,
            orchestration_stage="data_collection",
            partial_results=partial_results,
        )

        assert error.areas_affected == areas_affected
        assert error.endpoints_affected == endpoints_affected
        assert error.orchestration_stage == "data_collection"
        assert error.partial_results == partial_results
        assert error.service_name == "collection_orchestration"

    def test_collection_orchestration_error_context(self) -> None:
        """Test CollectionOrchestrationError context generation."""
        error = CollectionOrchestrationError(
            message="Orchestration failed",
            areas_affected=["DE", "FR"],
            endpoints_affected=["actual_load"],
        )

        context = error.context
        summary = context["partial_results_summary"]
        assert summary["total_areas"] == 2
        assert summary["total_endpoints"] == 1
        assert summary["has_partial_results"] is False

    def test_collection_orchestration_error_http_status(self) -> None:
        """Test CollectionOrchestrationError HTTP status code."""
        error = CollectionOrchestrationError("Orchestration failed")
        assert error.get_http_status_code() == 502


class TestChunkingError:
    """Test suite for ChunkingError."""

    def test_chunking_error_creation(self) -> None:
        """Test ChunkingError creation with chunking context."""
        start_time = datetime(2022, 1, 1, tzinfo=UTC)
        end_time = datetime(2022, 12, 31, tzinfo=UTC)

        error = ChunkingError(
            message="Chunking failed",
            start_time=start_time,
            end_time=end_time,
            chunk_size_days=30,
            total_chunks=12,
            failed_chunk_index=5,
        )

        assert error.start_time == start_time
        assert error.end_time == end_time
        assert error.chunk_size_days == 30
        assert error.total_chunks == 12
        assert error.failed_chunk_index == 5
        assert error.service_name == "chunking"

    def test_chunking_error_context_serialization(self) -> None:
        """Test ChunkingError context serialization of datetime objects."""
        start_time = datetime(2022, 1, 1, tzinfo=UTC)
        end_time = datetime(2022, 12, 31, tzinfo=UTC)

        error = ChunkingError(
            message="Chunking failed",
            start_time=start_time,
            end_time=end_time,
        )

        context = error.context
        assert context["start_time"] == start_time.isoformat()
        assert context["end_time"] == end_time.isoformat()

    def test_chunking_error_http_status(self) -> None:
        """Test ChunkingError HTTP status code."""
        error = ChunkingError("Chunking failed")
        assert error.get_http_status_code() == 422


class TestBackfillError:
    """Test suite for BackfillError base class."""

    def test_backfill_error_creation(self) -> None:
        """Test BackfillError creation with backfill context."""
        progress_info = {"completed_chunks": 5, "total_chunks": 10}

        error = BackfillError(
            message="Backfill failed",
            backfill_id=123,
            area_code="DE",
            endpoint_name="actual_load",
            progress_info=progress_info,
        )

        assert error.backfill_id == "123"
        assert error.area_code == "DE"
        assert error.endpoint_name == "actual_load"
        assert error.progress_info == progress_info
        assert error.service_name == "backfill"

    def test_backfill_error_context(self) -> None:
        """Test BackfillError context generation."""
        error = BackfillError(
            message="Backfill failed",
            backfill_id="456",
            area_code="FR",
            endpoint_name="day_ahead_forecast",
        )

        context = error.context
        assert context["backfill_id"] == "456"
        assert context["area_code"] == "FR"
        assert context["endpoint_name"] == "day_ahead_forecast"

    def test_backfill_error_http_status(self) -> None:
        """Test BackfillError HTTP status code."""
        error = BackfillError("Backfill failed")
        assert error.get_http_status_code() == 500


class TestBackfillProgressError:
    """Test suite for BackfillProgressError."""

    def test_backfill_progress_error_creation(self) -> None:
        """Test BackfillProgressError creation with progress context."""
        database_error = Exception("Database connection failed")
        progress_state = {"status": "in_progress", "completed_chunks": 3}

        error = BackfillProgressError(
            message="Progress tracking failed",
            backfill_id=789,
            progress_operation="save",
            database_error=database_error,
            progress_state=progress_state,
        )

        assert error.progress_operation == "save"
        assert error.database_error == database_error
        assert error.progress_state == progress_state
        assert error.operation == "progress_tracking"

    def test_backfill_progress_error_context(self) -> None:
        """Test BackfillProgressError context generation."""
        database_error = ValueError("Invalid data")

        error = BackfillProgressError(
            message="Progress save failed",
            progress_operation="update",
            database_error=database_error,
        )

        context = error.context
        assert context["progress_operation"] == "update"
        assert context["database_error"] == "Invalid data"

    def test_backfill_progress_error_http_status(self) -> None:
        """Test BackfillProgressError HTTP status code."""
        error = BackfillProgressError("Progress failed")
        assert error.get_http_status_code() == 500


class TestBackfillCoverageError:
    """Test suite for BackfillCoverageError."""

    def test_backfill_coverage_error_creation(self) -> None:
        """Test BackfillCoverageError creation with coverage context."""
        analysis_period = {
            "start": datetime(2022, 1, 1, tzinfo=UTC),
            "end": datetime(2023, 1, 1, tzinfo=UTC),
        }

        error = BackfillCoverageError(
            message="Coverage analysis failed",
            coverage_operation="analyze",
            analysis_period=analysis_period,
            expected_data_points=1000,
            actual_data_points=800,
        )

        assert error.coverage_operation == "analyze"
        assert error.analysis_period == analysis_period
        assert error.expected_data_points == 1000
        assert error.actual_data_points == 800
        assert error.operation == "coverage_analysis"

    def test_backfill_coverage_error_context_serialization(self) -> None:
        """Test BackfillCoverageError datetime serialization in context."""
        analysis_period = {
            "start": datetime(2022, 1, 1, tzinfo=UTC),
            "end": datetime(2023, 1, 1, tzinfo=UTC),
        }

        error = BackfillCoverageError(
            message="Coverage analysis failed",
            analysis_period=analysis_period,
            expected_data_points=1000,
            actual_data_points=800,
        )

        context = error.context
        assert "2022-01-01T00:00:00" in context["analysis_period"]["start"]
        assert "2023-01-01T00:00:00" in context["analysis_period"]["end"]
        assert context["coverage_gap"] == 200  # 1000 - 800

    def test_backfill_coverage_error_http_status(self) -> None:
        """Test BackfillCoverageError HTTP status code."""
        error = BackfillCoverageError("Coverage analysis failed")
        assert error.get_http_status_code() == 422


class TestBackfillResourceError:
    """Test suite for BackfillResourceError."""

    def test_backfill_resource_error_creation(self) -> None:
        """Test BackfillResourceError creation with resource context."""
        resource_context = {"active_operations": ["op1", "op2"]}

        error = BackfillResourceError(
            message="Resource limit exceeded",
            resource_type="concurrent_operations",
            limit_value=2,
            current_value=3,
            resource_context=resource_context,
        )

        assert error.resource_type == "concurrent_operations"
        assert error.limit_value == 2
        assert error.current_value == 3
        assert error.resource_context == resource_context
        assert error.operation == "resource_management"

    def test_backfill_resource_error_context(self) -> None:
        """Test BackfillResourceError context generation."""
        error = BackfillResourceError(
            message="Memory limit exceeded",
            resource_type="memory",
            limit_value=1024,
            current_value=1500,
        )

        context = error.context
        assert context["resource_type"] == "memory"
        assert context["limit_value"] == 1024
        assert context["current_value"] == 1500

    def test_backfill_resource_error_http_status(self) -> None:
        """Test BackfillResourceError HTTP status code."""
        error = BackfillResourceError("Resource limit exceeded")
        assert error.get_http_status_code() == 429


class TestBackfillDataQualityError:
    """Test suite for BackfillDataQualityError."""

    def test_backfill_data_quality_error_creation(self) -> None:
        """Test BackfillDataQualityError creation with quality context."""
        validation_results = {"completeness": 85.5, "accuracy": 92.0}
        data_sample = [{"timestamp": "2022-01-01T00:00:00", "value": None}]
        quality_metrics = {"null_percentage": 14.5}

        error = BackfillDataQualityError(
            message="Data quality check failed",
            quality_check="completeness_validation",
            validation_results=validation_results,
            data_sample=data_sample,
            quality_metrics=quality_metrics,
        )

        assert error.quality_check == "completeness_validation"
        assert error.validation_results == validation_results
        assert error.data_sample == data_sample
        assert error.quality_metrics == quality_metrics
        assert error.operation == "data_quality_validation"

    def test_backfill_data_quality_error_data_sample_truncation(self) -> None:
        """Test BackfillDataQualityError data sample truncation."""
        # Create a large data sample (more than 5 items)
        data_sample = [{"id": i, "value": None} for i in range(10)]

        error = BackfillDataQualityError(
            message="Data quality failed",
            data_sample=data_sample,
        )

        # Context should only include first 5 items
        context = error.context
        assert context["data_sample_count"] == 10
        assert len(context["data_sample"]) == 5
        assert context["data_sample"][0]["id"] == 0
        assert context["data_sample"][4]["id"] == 4

    def test_backfill_data_quality_error_http_status(self) -> None:
        """Test BackfillDataQualityError HTTP status code."""
        error = BackfillDataQualityError("Data quality failed")
        assert error.get_http_status_code() == 422


class TestServiceExceptionUtilities:
    """Test suite for service exception utility functions."""

    def test_create_service_error_from_processor_error(self) -> None:
        """Test creating ServiceError from ProcessorError."""
        processor_error = ProcessorError(
            message="Processing failed",
            processor_type="test_processor",
            operation="transform",
        )

        service_error = create_service_error_from_processor_error(
            processor_error=processor_error,
            service_name="test_service",
            operation="process_data",
        )

        assert isinstance(service_error, ServiceError)
        assert service_error.service_name == "test_service"
        assert service_error.operation == "process_data"
        assert "processor error" in str(service_error)
        assert service_error.context["original_error_type"] == "ProcessorError"

    def test_create_backfill_error_from_service_error(self) -> None:
        """Test creating BackfillError from ServiceError."""
        service_error = ServiceError(
            message="Service operation failed",
            service_name="test_service",
            operation="test_operation",
        )

        backfill_error = create_backfill_error_from_service_error(
            service_error=service_error,
            backfill_id=123,
            area_code="DE",
            endpoint_name="actual_load",
        )

        assert isinstance(backfill_error, BackfillError)
        assert backfill_error.backfill_id == "123"
        assert backfill_error.area_code == "DE"
        assert backfill_error.endpoint_name == "actual_load"
        assert "Backfill operation failed" in str(backfill_error)
        assert backfill_error.context["original_error_type"] == "ServiceError"


class TestServiceExceptionInheritance:
    """Test suite for service exception inheritance hierarchy."""

    def test_all_service_exceptions_inherit_from_service_error(self) -> None:
        """Test that all service exceptions inherit from ServiceError."""
        service_exception_classes = [
            GapDetectionError,
            CollectionOrchestrationError,
            ChunkingError,
            BackfillError,
            BackfillProgressError,
            BackfillCoverageError,
            BackfillResourceError,
            BackfillDataQualityError,
        ]

        for exception_class in service_exception_classes:
            assert issubclass(exception_class, ServiceError)

    def test_backfill_exceptions_inherit_from_backfill_error(self) -> None:
        """Test that backfill-specific exceptions inherit from BackfillError."""
        backfill_exception_classes = [
            BackfillProgressError,
            BackfillCoverageError,
            BackfillResourceError,
            BackfillDataQualityError,
        ]

        for exception_class in backfill_exception_classes:
            assert issubclass(exception_class, BackfillError)
            assert issubclass(exception_class, ServiceError)

    def test_exception_chaining_support(self) -> None:
        """Test that exceptions support proper chaining."""
        original_error = ValueError("Original error")
        service_message = "Service failed"

        def _raise_chained_exception() -> None:
            try:
                raise original_error
            except ValueError as e:
                raise ServiceError(service_message) from e

        with pytest.raises(ServiceError) as exc_info:
            _raise_chained_exception()

        service_error = exc_info.value
        assert service_error.__cause__ == original_error
        assert "Original error" in str(service_error.__cause__)

    def test_exception_context_preservation(self) -> None:
        """Test that exception context is preserved through inheritance."""
        error = BackfillProgressError(
            message="Progress failed",
            backfill_id=456,
            area_code="FR",
            progress_operation="save",
        )

        # Should have both BackfillError and ServiceError context
        assert error.backfill_id == "456"  # BackfillError attribute
        assert error.area_code == "FR"  # BackfillError attribute
        assert error.service_name == "backfill"  # ServiceError attribute
        assert (
            error.operation == "progress_tracking"
        )  # Specific to BackfillProgressError
        assert error.progress_operation == "save"  # BackfillProgressError attribute

    def test_to_dict_method_inheritance(self) -> None:
        """Test that to_dict method works correctly with inheritance."""
        error = BackfillResourceError(
            message="Resource limit exceeded",
            backfill_id=789,
            resource_type="memory",
            limit_value=1024,
        )

        error_dict = error.to_dict()

        # Should include ServiceError fields
        assert error_dict["error_type"] == "BackfillResourceError"
        assert error_dict["message"] == "Resource limit exceeded"
        assert error_dict["service_name"] == "backfill"

        # Should include context from all levels
        assert error_dict["context"]["backfill_id"] == "789"
        assert error_dict["context"]["resource_type"] == "memory"
        assert error_dict["context"]["limit_value"] == 1024
