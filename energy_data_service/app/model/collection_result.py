from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.model.collection_status import CollectionStatus
from app.model.raw_data_point import RawDataPoint


@dataclass
class CollectionResult:
    """
    Container for data collection attempt results.

    Provides structured feedback about collection success/failure
    enabling proper error handling, monitoring, and debugging.

    Design Principles:
    - Clear success/failure semantics
    - Rich error context for debugging
    - Metadata for monitoring and alerting
    - Immutable result state once marked complete
    """

    source: str
    status: CollectionStatus = CollectionStatus.FAILED
    data_points: list[RawDataPoint] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    collection_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    start_requested: datetime | None = None
    end_requested: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_successful(self) -> bool:
        """Check if the collection was successful."""
        return self.status in [
            CollectionStatus.SUCCESS,
            CollectionStatus.PARTIAL_SUCCESS,
        ]

    @property
    def point_count(self) -> int:
        """Get the number of data points collected."""
        return len(self.data_points)

    @property
    def has_errors(self) -> bool:
        """Check if there were any errors during collection."""
        return len(self.errors) > 0

    def add_error(self, error: str) -> None:
        """Add an error message to the collection result."""
        self.errors.append(error)
        if self.status == CollectionStatus.SUCCESS:
            self.status = CollectionStatus.PARTIAL_SUCCESS

    def add_warning(self, warning: str) -> None:
        """Add a warning message to the collection result."""
        self.warnings.append(warning)

    def mark_success(self) -> None:
        """Mark the collection as successful."""
        if not self.errors:
            self.status = CollectionStatus.SUCCESS
        else:
            self.status = CollectionStatus.PARTIAL_SUCCESS

    def mark_failed(self, reason: str) -> None:
        """Mark the collection as failed."""
        self.status = CollectionStatus.FAILED
        self.add_error(reason)

    def mark_rate_limited(self) -> None:
        """Mark the collection as rate limited."""
        self.status = CollectionStatus.RATE_LIMITED
        self.add_warning("Rate limit exceeded, retry later.")

    def mark_no_data(self) -> None:
        """Mark the collection as having no data available."""
        self.status = CollectionStatus.NO_DATA_AVAILABLE
        self.add_warning("No data available for requested period.")
