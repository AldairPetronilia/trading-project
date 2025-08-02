"""
Collection metrics model for monitoring data collection operations.

This module provides database models for tracking the performance and success
of data collection operations, enabling comprehensive monitoring of scheduler
jobs and data pipeline health across different energy areas and data types.

Key Features:
- Collection operation tracking with timing metrics
- Area and data type specificity for granular monitoring
- Success/failure tracking with detailed error context
- Performance metrics for API response times and processing duration
- Job correlation for scheduler integration
- Comprehensive indexing for efficient querying
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import TimestampedModel
from .load_data import EnergyDataType  # noqa: TC001


class CollectionMetrics(TimestampedModel):
    """
    Model for tracking data collection operation metrics and performance monitoring.

    This model provides comprehensive tracking of data collection operations,
    including timing metrics, success rates, and error context for monitoring
    the health and performance of scheduled data collection jobs across
    different energy areas and data types.

    Attributes:
        id: Primary key for the collection metrics record
        job_id: Identifier for the scheduler job that performed the collection
        area_code: Geographic area code for this collection operation (e.g., 'DE', 'FR')
        data_type: Type of energy data being collected (actual, day_ahead, etc.)
        collection_start: Start timestamp of the collection operation
        collection_end: End timestamp of the collection operation
        points_collected: Number of data points successfully collected
        success: Whether the collection operation succeeded completely
        error_message: Detailed error message if the operation failed
        api_response_time: API response time in milliseconds for performance monitoring
        processing_time: Total processing time in milliseconds for the operation
        created_at: Timestamp when this metrics record was created (inherited)
        updated_at: Timestamp when this metrics record was last updated (inherited)
    """

    __tablename__ = "collection_metrics"

    # Primary identification
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key for collection metrics record",
    )

    job_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Scheduler job identifier for correlation",
    )

    # Data identification
    area_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="Geographic area code (e.g., 'DE', 'FR')",
    )

    data_type: Mapped[EnergyDataType] = mapped_column(
        nullable=False, index=True, comment="Type of energy data being collected"
    )

    # Collection timing
    collection_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Start timestamp of collection operation",
    )

    collection_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="End timestamp of collection operation",
    )

    # Collection results
    points_collected: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of data points successfully collected",
    )

    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether collection operation succeeded completely",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Detailed error message if operation failed"
    )

    # Performance metrics
    api_response_time: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="API response time in milliseconds"
    )

    processing_time: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Total processing time in milliseconds"
    )

    # Composite indexes for efficient querying
    __table_args__ = (
        # Index for time-based queries (most common query pattern)
        Index("ix_collection_metrics_time_range", "collection_start", "collection_end"),
        # Index for area and data type filtering with time
        Index(
            "ix_collection_metrics_area_type_time",
            "area_code",
            "data_type",
            "collection_start",
        ),
        # Index for success rate analysis
        Index("ix_collection_metrics_success_time", "success", "collection_start"),
        # Index for job correlation and monitoring
        Index("ix_collection_metrics_job_time", "job_id", "collection_start"),
        {
            "comment": "Collection metrics for monitoring data pipeline health and performance"
        },
    )

    def __repr__(self) -> str:
        """String representation for debugging and logging."""
        return (
            f"CollectionMetrics(id={self.id}, job_id='{self.job_id}', "
            f"area='{self.area_code}', data_type={self.data_type.value}, "
            f"success={self.success}, points={self.points_collected})"
        )

    @property
    def collection_duration_seconds(self) -> float:
        """Calculate collection duration in seconds."""
        duration = self.collection_end - self.collection_start
        return duration.total_seconds()

    @property
    def collection_rate_points_per_second(self) -> float:
        """Calculate collection rate as points per second."""
        duration = self.collection_duration_seconds
        if duration <= 0:
            return 0.0
        return self.points_collected / duration

    @property
    def has_performance_metrics(self) -> bool:
        """Check if performance metrics are available."""
        return self.api_response_time is not None or self.processing_time is not None

    @property
    def total_time_milliseconds(self) -> float | None:
        """Get total operation time including API and processing time."""
        if self.api_response_time is not None and self.processing_time is not None:
            return self.api_response_time + self.processing_time
        return None
