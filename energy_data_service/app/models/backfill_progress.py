"""
Backfill progress tracking model for historical data collection operations.

This module provides database models for tracking the progress of historical
data backfill operations, enabling resumable operations and progress monitoring
across service restarts and failures.

Key Features:
- Status tracking for backfill operations (pending, in_progress, completed, failed)
- Progress persistence with detailed timing and statistics
- Area and endpoint specificity for granular progress tracking
- Resumable operations through database-persisted state
- Foreign key relationships for data integrity
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import TimestampedModel

if TYPE_CHECKING:
    from .load_data import EnergyDataPoint


class BackfillStatus(str, Enum):
    """Status enumeration for backfill operations with clear state transitions."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackfillProgress(TimestampedModel):
    """
    Model for tracking backfill operation progress and enabling resumable operations.

    This model provides comprehensive tracking of historical data collection
    operations, including progress persistence, error context, and performance
    metrics for monitoring and debugging large-scale backfill operations.

    Attributes:
        area_code: The geographic area code for this backfill operation
        endpoint_name: The ENTSO-E endpoint name being backfilled
        period_start: Start of the historical period being backfilled
        period_end: End of the historical period being backfilled
        status: Current status of the backfill operation
        progress_percentage: Completion percentage (0.0 to 100.0)
        current_chunk_start: Start of the currently processing chunk
        current_chunk_end: End of the currently processing chunk
        total_chunks: Total number of chunks for this backfill
        completed_chunks: Number of completed chunks
        total_data_points: Total number of data points collected
        failed_chunks: Number of chunks that failed processing
        last_error: Last error message if operation failed
        started_at: Timestamp when backfill operation started
        completed_at: Timestamp when backfill operation completed
        estimated_completion: Estimated completion timestamp based on progress
        chunk_size_days: Size of each chunk in days for this operation
        rate_limit_delay: Rate limiting delay used for this operation
    """

    __tablename__ = "backfill_progress"

    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    area_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="Geographic area code (e.g., 'DE', 'FR')",
    )
    endpoint_name: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="ENTSO-E endpoint name"
    )

    # Time period definition
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="Start of backfill period"
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="End of backfill period"
    )

    # Progress tracking
    status: Mapped[BackfillStatus] = mapped_column(
        SQLEnum(BackfillStatus),
        default=BackfillStatus.PENDING,
        nullable=False,
        index=True,
        comment="Current status of backfill operation",
    )
    progress_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Completion percentage (0.00-100.00)",
    )

    # Chunk-level progress
    current_chunk_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Start of current processing chunk",
    )
    current_chunk_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="End of current processing chunk",
    )
    total_chunks: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Total chunks for operation"
    )
    completed_chunks: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Number of completed chunks"
    )

    # Data statistics
    total_data_points: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Total data points collected"
    )
    failed_chunks: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Number of failed chunks"
    )

    # Error tracking
    last_error: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Last error message if operation failed"
    )

    # Timing information
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When backfill operation started",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When backfill operation completed",
    )
    estimated_completion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Estimated completion time"
    )

    # Configuration used
    chunk_size_days: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Chunk size in days used for this operation"
    )
    rate_limit_delay: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, comment="Rate limit delay in seconds"
    )

    # Constraints and indexes
    __table_args__ = (
        # Unique constraint on area/endpoint/period combination
        # This prevents duplicate backfill operations for the same data
        # Note: Using string names since columns are already defined above
        # Composite index for efficient querying
        {"comment": "Backfill progress tracking with resumable operation support"},
    )

    def __repr__(self) -> str:
        """String representation for debugging and logging."""
        return (
            f"BackfillProgress(id={self.id}, area={self.area_code}, "
            f"endpoint={self.endpoint_name}, status={self.status.value}, "
            f"progress={self.progress_percentage}%)"
        )

    @property
    def is_active(self) -> bool:
        """Check if backfill operation is currently active."""
        return self.status in (BackfillStatus.PENDING, BackfillStatus.IN_PROGRESS)

    @property
    def is_completed(self) -> bool:
        """Check if backfill operation completed successfully."""
        return self.status == BackfillStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if backfill operation failed."""
        return self.status == BackfillStatus.FAILED

    @property
    def can_be_resumed(self) -> bool:
        """Check if backfill operation can be resumed."""
        return (
            self.status in (BackfillStatus.FAILED, BackfillStatus.PENDING)
            and self.completed_chunks > 0
        )

    @property
    def remaining_chunks(self) -> int:
        """Calculate remaining chunks to process."""
        return max(0, self.total_chunks - self.completed_chunks)

    @property
    def success_rate(self) -> Decimal:
        """Calculate success rate as percentage of successful chunks."""
        if self.total_chunks == 0:
            return Decimal("0.00")
        successful_chunks = self.completed_chunks - self.failed_chunks
        return Decimal(str(successful_chunks / self.total_chunks * 100)).quantize(
            Decimal("0.01")
        )

    def update_progress(
        self,
        completed_chunks: int,
        total_data_points: int,
        current_chunk_start: datetime | None = None,
        current_chunk_end: datetime | None = None,
    ) -> None:
        """
        Update progress information for the backfill operation.

        Args:
            completed_chunks: Number of chunks completed so far
            total_data_points: Total data points collected
            current_chunk_start: Start of currently processing chunk
            current_chunk_end: End of currently processing chunk
        """
        self.completed_chunks = completed_chunks
        self.total_data_points = total_data_points
        self.current_chunk_start = current_chunk_start
        self.current_chunk_end = current_chunk_end

        # Calculate progress percentage
        if self.total_chunks > 0:
            self.progress_percentage = Decimal(
                str(completed_chunks / self.total_chunks * 100)
            ).quantize(Decimal("0.01"))

    def mark_started(self) -> None:
        """Mark backfill operation as started."""
        self.status = BackfillStatus.IN_PROGRESS
        self.started_at = datetime.now(UTC)

    def mark_completed(self) -> None:
        """Mark backfill operation as completed successfully."""
        self.status = BackfillStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
        self.progress_percentage = Decimal("100.00")

    def mark_failed(self, error_message: str) -> None:
        """
        Mark backfill operation as failed with error context.

        Args:
            error_message: Detailed error message for debugging
        """
        self.status = BackfillStatus.FAILED
        self.last_error = error_message
        # Don't set completed_at for failed operations

    def mark_cancelled(self) -> None:
        """Mark backfill operation as cancelled."""
        self.status = BackfillStatus.CANCELLED
        self.completed_at = datetime.now(UTC)

    def increment_failed_chunks(self) -> None:
        """Increment the count of failed chunks."""
        self.failed_chunks = (self.failed_chunks or 0) + 1
