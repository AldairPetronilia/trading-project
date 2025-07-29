"""
Unit tests for BackfillProgress model.

This module provides comprehensive unit tests for the BackfillProgress model,
covering status tracking, progress updates, and model properties.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.models import BackfillProgress, BackfillStatus


class TestBackfillProgress:
    """Test suite for BackfillProgress model."""

    @pytest.fixture
    def sample_progress(self) -> BackfillProgress:
        """Create a sample backfill progress record."""
        return BackfillProgress(
            area_code="DE",
            endpoint_name="actual_load",
            period_start=datetime(2022, 1, 1, tzinfo=UTC),
            period_end=datetime(2023, 1, 1, tzinfo=UTC),
            status=BackfillStatus.PENDING,
            progress_percentage=Decimal("0.00"),
            total_chunks=10,
            completed_chunks=0,
            failed_chunks=0,
            total_data_points=0,
            chunk_size_days=30,
            rate_limit_delay=Decimal("2.0"),
        )

    def test_backfill_progress_creation(
        self, sample_progress: BackfillProgress
    ) -> None:
        """Test creating a backfill progress record."""
        assert sample_progress.area_code == "DE"
        assert sample_progress.endpoint_name == "actual_load"
        assert sample_progress.status == BackfillStatus.PENDING
        assert sample_progress.total_chunks == 10
        assert sample_progress.completed_chunks == 0
        assert sample_progress.progress_percentage == Decimal("0.00")
        assert sample_progress.chunk_size_days == 30
        assert sample_progress.rate_limit_delay == Decimal("2.0")

    def test_backfill_progress_repr(self, sample_progress: BackfillProgress) -> None:
        """Test string representation of backfill progress."""
        sample_progress.id = 1
        repr_str = repr(sample_progress)

        assert "BackfillProgress" in repr_str
        assert "id=1" in repr_str
        assert "area=DE" in repr_str
        assert "endpoint=actual_load" in repr_str
        assert "status=pending" in repr_str
        assert "progress=0.00%" in repr_str

    # Property Tests

    def test_is_active_property(self, sample_progress: BackfillProgress) -> None:
        """Test is_active property for different statuses."""
        # Test each status independently to avoid mypy literal type issues
        for status, expected_active in [
            (BackfillStatus.PENDING, True),
            (BackfillStatus.IN_PROGRESS, True),
            (BackfillStatus.COMPLETED, False),
            (BackfillStatus.FAILED, False),
            (BackfillStatus.CANCELLED, False),
        ]:
            sample_progress.status = status
            assert sample_progress.is_active is expected_active

    def test_is_completed_property(self, sample_progress: BackfillProgress) -> None:
        """Test is_completed property for different statuses."""
        # Only completed status should return true
        sample_progress.status = BackfillStatus.COMPLETED
        assert sample_progress.is_completed is True

        # All other statuses should return false
        for status in [
            BackfillStatus.PENDING,
            BackfillStatus.IN_PROGRESS,
            BackfillStatus.FAILED,
            BackfillStatus.CANCELLED,
        ]:
            sample_progress.status = status
            assert sample_progress.is_completed is False

    def test_is_failed_property(self, sample_progress: BackfillProgress) -> None:
        """Test is_failed property for different statuses."""
        # Only failed status should return true
        sample_progress.status = BackfillStatus.FAILED
        assert sample_progress.is_failed is True

        # All other statuses should return false
        for status in [
            BackfillStatus.PENDING,
            BackfillStatus.IN_PROGRESS,
            BackfillStatus.COMPLETED,
            BackfillStatus.CANCELLED,
        ]:
            sample_progress.status = status
            assert sample_progress.is_failed is False

    def test_can_be_resumed_property(self, sample_progress: BackfillProgress) -> None:
        """Test can_be_resumed property for different conditions."""
        # Test each condition independently to avoid mypy literal type issues
        test_cases = [
            (BackfillStatus.FAILED, 3, True),  # Failed with some chunks is resumable
            (BackfillStatus.PENDING, 2, True),  # Pending with some chunks is resumable
            (BackfillStatus.FAILED, 0, False),  # Failed with no chunks is not resumable
            (BackfillStatus.COMPLETED, 5, False),  # Completed is not resumable
            (BackfillStatus.IN_PROGRESS, 3, False),  # In progress is not resumable
        ]

        for status, completed_chunks, expected_resumable in test_cases:
            sample_progress.status = status
            sample_progress.completed_chunks = completed_chunks
            assert sample_progress.can_be_resumed is expected_resumable

    def test_remaining_chunks_property(self, sample_progress: BackfillProgress) -> None:
        """Test remaining_chunks property calculation."""
        sample_progress.total_chunks = 10
        sample_progress.completed_chunks = 3
        assert sample_progress.remaining_chunks == 7

        # Should not go below zero
        sample_progress.completed_chunks = 12
        assert sample_progress.remaining_chunks == 0

    def test_success_rate_property(self, sample_progress: BackfillProgress) -> None:
        """Test success_rate property calculation."""
        # No chunks processed yet
        sample_progress.total_chunks = 10
        sample_progress.completed_chunks = 0
        sample_progress.failed_chunks = 0
        assert sample_progress.success_rate == Decimal("0.00")

        # All chunks successful
        sample_progress.completed_chunks = 8
        sample_progress.failed_chunks = 0
        assert sample_progress.success_rate == Decimal("80.00")

        # Some chunks failed
        sample_progress.completed_chunks = 6
        sample_progress.failed_chunks = 2
        assert sample_progress.success_rate == Decimal("40.00")  # (6-2)/10 * 100

    # Progress Tracking Methods

    def test_update_progress(self, sample_progress: BackfillProgress) -> None:
        """Test update_progress method."""
        current_start = datetime(2022, 3, 1, tzinfo=UTC)
        current_end = datetime(2022, 3, 31, tzinfo=UTC)

        sample_progress.update_progress(
            completed_chunks=5,
            total_data_points=1000,
            current_chunk_start=current_start,
            current_chunk_end=current_end,
        )

        assert sample_progress.completed_chunks == 5
        assert sample_progress.total_data_points == 1000
        assert sample_progress.current_chunk_start == current_start
        assert sample_progress.current_chunk_end == current_end
        assert sample_progress.progress_percentage == Decimal("50.00")  # 5/10 * 100

    def test_update_progress_no_total_chunks(
        self, sample_progress: BackfillProgress
    ) -> None:
        """Test update_progress method when total_chunks is 0."""
        sample_progress.total_chunks = 0

        sample_progress.update_progress(
            completed_chunks=5,
            total_data_points=1000,
        )

        assert sample_progress.completed_chunks == 5
        assert sample_progress.total_data_points == 1000
        # Progress percentage should remain 0 when total_chunks is 0
        assert sample_progress.progress_percentage == Decimal("0.00")

    # Status Change Methods

    def test_mark_started(self, sample_progress: BackfillProgress) -> None:
        """Test mark_started method."""
        before_start = datetime.now(UTC)
        sample_progress.mark_started()
        after_start = datetime.now(UTC)

        assert sample_progress.status == BackfillStatus.IN_PROGRESS
        assert sample_progress.started_at is not None
        assert before_start <= sample_progress.started_at <= after_start

    def test_mark_completed(self, sample_progress: BackfillProgress) -> None:
        """Test mark_completed method."""
        before_completion = datetime.now(UTC)
        sample_progress.mark_completed()
        after_completion = datetime.now(UTC)

        assert sample_progress.status == BackfillStatus.COMPLETED
        assert sample_progress.completed_at is not None
        assert before_completion <= sample_progress.completed_at <= after_completion
        assert sample_progress.progress_percentage == Decimal("100.00")

    def test_mark_failed(self, sample_progress: BackfillProgress) -> None:
        """Test mark_failed method."""
        error_message = "API timeout error"
        sample_progress.mark_failed(error_message)

        assert sample_progress.status == BackfillStatus.FAILED
        assert sample_progress.last_error == error_message
        assert (
            sample_progress.completed_at is None
        )  # Should not set completed_at for failures

    def test_mark_cancelled(self, sample_progress: BackfillProgress) -> None:
        """Test mark_cancelled method."""
        before_cancellation = datetime.now(UTC)
        sample_progress.mark_cancelled()
        after_cancellation = datetime.now(UTC)

        assert sample_progress.status == BackfillStatus.CANCELLED
        assert sample_progress.completed_at is not None
        assert before_cancellation <= sample_progress.completed_at <= after_cancellation

    def test_increment_failed_chunks(self, sample_progress: BackfillProgress) -> None:
        """Test increment_failed_chunks method."""
        initial_failed = sample_progress.failed_chunks
        sample_progress.increment_failed_chunks()
        assert sample_progress.failed_chunks == initial_failed + 1

        sample_progress.increment_failed_chunks()
        assert sample_progress.failed_chunks == initial_failed + 2

    # Integration Tests

    def test_full_progress_lifecycle(self, sample_progress: BackfillProgress) -> None:
        """Test a complete progress lifecycle."""
        # Start the backfill
        sample_progress.mark_started()
        current_status = sample_progress.status
        assert current_status == BackfillStatus.IN_PROGRESS
        assert sample_progress.is_active is True

        # Process some chunks
        sample_progress.update_progress(
            completed_chunks=3,
            total_data_points=300,
        )
        assert sample_progress.progress_percentage == Decimal("30.00")

        # Encounter a failure
        sample_progress.increment_failed_chunks()
        assert sample_progress.failed_chunks == 1

        # Continue processing
        sample_progress.update_progress(
            completed_chunks=8,
            total_data_points=750,  # Less than expected due to failure
        )
        assert sample_progress.progress_percentage == Decimal("80.00")

        # Complete the backfill - this will set status to COMPLETED and progress to 100%
        sample_progress.mark_completed()
        final_status = sample_progress.status
        assert final_status == BackfillStatus.COMPLETED
        assert sample_progress.is_completed is True
        assert sample_progress.is_active is False

    def test_failed_backfill_resume_scenario(
        self, sample_progress: BackfillProgress
    ) -> None:
        """Test a failed backfill that can be resumed."""
        # Start and process some chunks
        sample_progress.mark_started()
        sample_progress.update_progress(completed_chunks=4, total_data_points=400)

        # Fail with error
        sample_progress.mark_failed("Network timeout")
        assert sample_progress.status == BackfillStatus.FAILED
        assert sample_progress.can_be_resumed is True
        assert sample_progress.last_error == "Network timeout"

        # Resume would reset status to in_progress
        sample_progress.status = BackfillStatus.IN_PROGRESS

        # Continue from where left off
        sample_progress.update_progress(completed_chunks=10, total_data_points=950)
        sample_progress.mark_completed()

        assert sample_progress.is_completed is True
        assert sample_progress.progress_percentage == Decimal("100.00")


class TestBackfillStatus:
    """Test suite for BackfillStatus enum."""

    def test_backfill_status_values(self) -> None:
        """Test BackfillStatus enum values."""
        assert BackfillStatus.PENDING.value == "pending"
        assert BackfillStatus.IN_PROGRESS.value == "in_progress"
        assert BackfillStatus.COMPLETED.value == "completed"
        assert BackfillStatus.FAILED.value == "failed"
        assert BackfillStatus.CANCELLED.value == "cancelled"

    def test_backfill_status_string_inheritance(self) -> None:
        """Test that BackfillStatus inherits from str."""
        # This allows direct string comparison
        status = BackfillStatus.PENDING
        assert status == "pending"
        # String enums are instances of str and support string operations
        assert isinstance(status, str)
        # Enum values can be accessed directly since status == "pending" works
        assert "pending" in [s.value for s in BackfillStatus]

    def test_backfill_status_enum_membership(self) -> None:
        """Test BackfillStatus enum membership."""
        all_statuses = list(BackfillStatus)
        expected_statuses = [
            BackfillStatus.PENDING,
            BackfillStatus.IN_PROGRESS,
            BackfillStatus.COMPLETED,
            BackfillStatus.FAILED,
            BackfillStatus.CANCELLED,
        ]
        assert len(all_statuses) == 5
        assert set(all_statuses) == set(expected_statuses)
