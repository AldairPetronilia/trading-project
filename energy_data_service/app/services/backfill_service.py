"""
Backfill service for historical data collection and management.

This service provides comprehensive historical data backfill capabilities,
enabling controlled collection of large historical datasets with progress
tracking, resumable operations, and intelligent resource management.

Key Features:
- Coverage analysis to identify historical data gaps
- Chunked historical collection with configurable chunk sizes
- Progress persistence for resumable operations
- Resource management and rate limiting
- Data quality validation and completeness checks
- Multi-area and multi-endpoint orchestration
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, ClassVar, NoReturn

from sqlalchemy import select

from app.exceptions import (
    BackfillCoverageError,
    BackfillDataQualityError,
    BackfillError,
    BackfillProgressError,
    BackfillResourceError,
    create_service_error_from_processor_error,
)
from app.models import (
    BackfillProgress,
    BackfillStatus,
    EnergyDataPoint,
)
from app.models.backfill_progress import (
    BackfillProgress as BackfillProgressModel,
)
from app.models.load_data import EnergyDataType
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.load.gl_market_document import GlMarketDocument

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.collectors.entsoe_collector import EntsoeCollector
    from app.config.database import Database
    from app.config.settings import BackfillConfig
    from app.processors.gl_market_document_processor import (
        GlMarketDocumentProcessor,
    )
    from app.repositories.backfill_progress_repository import (
        BackfillProgressRepository,
    )
    from app.repositories.energy_data_repository import (
        EnergyDataRepository,
    )

# Set up logging
log = logging.getLogger(__name__)

# Constants
MIN_COVERAGE_PERCENTAGE = 95.0  # Minimum coverage percentage to avoid backfill
FULL_COVERAGE_PERCENTAGE = 100.0  # Complete coverage percentage


@dataclass
class CoverageAnalysisParams:
    """Parameters for coverage analysis."""

    area_code: str
    endpoint_name: str
    analysis_period_start: datetime
    analysis_period_end: datetime
    expected_data_points: int
    actual_data_points: int
    coverage_percentage: float
    missing_periods: list[tuple[datetime, datetime]]


@dataclass
class BackfillResultParams:
    """Parameters for backfill result."""

    backfill_id: int
    area_code: str
    endpoint_name: str
    success: bool
    data_points_collected: int
    chunks_processed: int
    chunks_failed: int
    start_time: datetime
    end_time: datetime | None = None
    error_messages: list[str] | None = None


class CoverageAnalysis:
    """Result of coverage analysis for a specific area/endpoint combination."""

    def __init__(self, params: CoverageAnalysisParams) -> None:
        """Initialize coverage analysis result."""
        self.area_code = params.area_code
        self.endpoint_name = params.endpoint_name
        self.analysis_period_start = params.analysis_period_start
        self.analysis_period_end = params.analysis_period_end
        self.expected_data_points = params.expected_data_points
        self.actual_data_points = params.actual_data_points
        self.coverage_percentage = params.coverage_percentage
        self.missing_periods = params.missing_periods

    @property
    def needs_backfill(self) -> bool:
        """Check if this area/endpoint combination needs backfill."""
        return self.coverage_percentage < MIN_COVERAGE_PERCENTAGE

    @property
    def total_missing_points(self) -> int:
        """Calculate total missing data points."""
        return self.expected_data_points - self.actual_data_points

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging and serialization."""
        return {
            "area_code": self.area_code,
            "endpoint_name": self.endpoint_name,
            "analysis_period_start": self.analysis_period_start.isoformat(),
            "analysis_period_end": self.analysis_period_end.isoformat(),
            "expected_data_points": self.expected_data_points,
            "actual_data_points": self.actual_data_points,
            "coverage_percentage": self.coverage_percentage,
            "needs_backfill": self.needs_backfill,
            "total_missing_points": self.total_missing_points,
            "missing_periods_count": len(self.missing_periods),
        }


class BackfillResult:
    """Result of a backfill operation."""

    def __init__(self, params: BackfillResultParams) -> None:
        """Initialize backfill result."""
        self.backfill_id = params.backfill_id
        self.area_code = params.area_code
        self.endpoint_name = params.endpoint_name
        self.success = params.success
        self.data_points_collected = params.data_points_collected
        self.chunks_processed = params.chunks_processed
        self.chunks_failed = params.chunks_failed
        self.start_time = params.start_time
        self.end_time = params.end_time
        self.error_messages = params.error_messages or []

    @property
    def duration_seconds(self) -> float:
        """Calculate operation duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total_chunks = self.chunks_processed + self.chunks_failed
        if total_chunks == 0:
            return 0.0
        return (self.chunks_processed / total_chunks) * 100.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging and serialization."""
        return {
            "backfill_id": self.backfill_id,
            "area_code": self.area_code,
            "endpoint_name": self.endpoint_name,
            "success": self.success,
            "data_points_collected": self.data_points_collected,
            "chunks_processed": self.chunks_processed,
            "chunks_failed": self.chunks_failed,
            "success_rate": self.success_rate,
            "duration_seconds": self.duration_seconds,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error_count": len(self.error_messages),
        }


class BackfillService:
    """
    Service for historical data backfill operations with progress tracking.

    This service provides comprehensive backfill capabilities including:
    - Coverage analysis to identify missing historical data
    - Chunked historical collection with configurable parameters
    - Progress persistence for resumable operations
    - Resource management and rate limiting
    - Data quality validation and completeness checks
    """

    # Expected data intervals for different endpoint types (in minutes)
    ENDPOINT_INTERVALS: ClassVar[dict[str, int]] = {
        "actual_load": 15,  # 15-minute intervals
        "day_ahead_forecast": 60,  # 1-hour intervals
        "week_ahead_forecast": 60,  # 1-hour intervals
        "month_ahead_forecast": 60,  # 1-hour intervals
        "year_ahead_forecast": 60,  # 1-hour intervals
        "forecast_margin": 60,  # 1-hour intervals
    }

    def __init__(
        self,
        collector: EntsoeCollector,
        processor: GlMarketDocumentProcessor,
        repository: EnergyDataRepository,
        database: Database,
        config: BackfillConfig,
        progress_repository: BackfillProgressRepository,
    ) -> None:
        """
        Initialize the backfill service.

        Args:
            collector: ENTSO-E data collector instance
            processor: GL market document processor instance
            repository: Energy data repository instance
            database: Database instance for session management
            config: Backfill configuration settings
            progress_repository: Repository for backfill progress operations
        """
        self._collector = collector
        self._processor = processor
        self._repository = repository
        self._database = database
        self._config = config
        self._progress_repository = progress_repository
        self._active_operations: dict[str, BackfillProgress] = {}

    async def analyze_coverage(
        self,
        areas: list[AreaCode] | None = None,
        endpoints: list[str] | None = None,
        years_back: int | None = None,
    ) -> list[CoverageAnalysis]:
        """
        Analyze historical data coverage for specified areas and endpoints.

        Args:
            areas: List of area codes to analyze (defaults to DE, FR, NL)
            endpoints: List of endpoint names to analyze (defaults to all)
            years_back: Number of years to analyze (defaults to config value)

        Returns:
            List of coverage analysis results

        Raises:
            BackfillCoverageError: If coverage analysis fails
        """
        try:
            # Use defaults if not specified
            if areas is None:
                areas = [AreaCode.GERMANY, AreaCode.FRANCE, AreaCode.NETHERLANDS]
            if endpoints is None:
                endpoints = list(self.ENDPOINT_INTERVALS.keys())
            if years_back is None:
                years_back = self._config.historical_years

            # Calculate analysis period
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(days=years_back * 365)

            msg = (
                f"Starting coverage analysis for {len(areas)} areas, {len(endpoints)} endpoints, "
                f"{years_back} years back (period: {start_time} to {end_time})"
            )
            log.info(msg)

            coverage_results = []

            for area in areas:
                area_code = area.get_country_code() or str(area.code)

                for endpoint_name in endpoints:
                    try:
                        analysis = await self._analyze_area_endpoint_coverage(
                            area_code, endpoint_name, start_time, end_time
                        )
                        coverage_results.append(analysis)

                        msg = (
                            f"Coverage analysis complete for {area_code}/{endpoint_name}: "
                            f"{analysis.coverage_percentage:.1f}% coverage "
                            f"({analysis.actual_data_points}/{analysis.expected_data_points} points)"
                        )
                        log.debug(msg)

                    except Exception as e:
                        msg = (
                            f"Coverage analysis failed for {area_code}/{endpoint_name}"
                        )
                        raise BackfillCoverageError(
                            message=msg,
                            coverage_operation="analyze",
                            area_code=area_code,
                            endpoint_name=endpoint_name,
                            analysis_period={"start": start_time, "end": end_time},
                        ) from e

            msg = f"Coverage analysis complete: {len(coverage_results)} area/endpoint combinations analyzed"
            log.info(msg)

        except BackfillCoverageError:
            raise
        except Exception as e:
            msg = f"Coverage analysis failed: {e}"
            raise BackfillCoverageError(
                message=msg,
                coverage_operation="analyze_all",
                context={
                    "areas_count": len(areas or []),
                    "endpoints_count": len(endpoints or []),
                },
            ) from e
        else:
            return coverage_results

    async def start_backfill(
        self,
        area_code: str,
        endpoint_name: str,
        period_start: datetime,
        period_end: datetime,
        chunk_size_days: int | None = None,
    ) -> BackfillResult:
        """
        Start a new backfill operation for a specific area/endpoint combination.

        Args:
            area_code: The area code to backfill
            endpoint_name: The endpoint name to backfill
            period_start: Start of the historical period to backfill
            period_end: End of the historical period to backfill
            chunk_size_days: Override chunk size (defaults to config value)

        Returns:
            BackfillResult with operation summary

        Raises:
            BackfillError: If backfill operation fails
            BackfillResourceError: If resource limits are exceeded
        """
        try:
            # Check resource limits
            await self._check_resource_limits()

            # Use default chunk size if not specified
            if chunk_size_days is None:
                chunk_size_days = (
                    self._config.chunk_months * 30
                )  # Convert months to days

            msg = (
                f"Starting backfill for {area_code}/{endpoint_name} "
                f"from {period_start} to {period_end} "
                f"(chunk size: {chunk_size_days} days)"
            )
            log.info(msg)

            # Create progress tracking record
            progress = await self._create_backfill_progress(
                area_code, endpoint_name, period_start, period_end, chunk_size_days
            )

            # Register active operation
            operation_key = f"{area_code}_{endpoint_name}_{progress.id}"
            self._active_operations[operation_key] = progress

            try:
                # Mark as started
                progress.mark_started()
                await self._save_progress(progress)

                # Perform the backfill
                result = await self._execute_backfill(progress)

                # Mark as completed or failed
                if result.success:
                    progress.mark_completed()
                else:
                    progress.mark_failed("; ".join(result.error_messages))

                await self._save_progress(progress)
                return result

            finally:
                # Remove from active operations
                self._active_operations.pop(operation_key, None)

        except BackfillResourceError:
            raise
        except Exception as e:
            msg = f"Backfill operation failed for {area_code}/{endpoint_name}"
            raise BackfillError(
                message=msg,
                area_code=area_code,
                endpoint_name=endpoint_name,
                context={
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "chunk_size_days": chunk_size_days,
                },
            ) from e

    async def resume_backfill(self, backfill_id: int) -> BackfillResult:
        """
        Resume an interrupted backfill operation.

        Args:
            backfill_id: ID of the backfill operation to resume

        Returns:
            BackfillResult with operation summary

        Raises:
            BackfillProgressError: If resume operation fails
            BackfillError: If backfill operation fails
        """
        try:
            # Load progress from database
            progress = await self._load_backfill_progress(backfill_id)

            if not progress.can_be_resumed:
                self._raise_cannot_resume_error(backfill_id, progress)

            msg = (
                f"Resuming backfill {backfill_id} for {progress.area_code}/{progress.endpoint_name} "
                f"from chunk {progress.completed_chunks}/{progress.total_chunks}"
            )
            log.info(msg)

            # Check resource limits
            await self._check_resource_limits()

            # Register active operation
            operation_key = (
                f"{progress.area_code}_{progress.endpoint_name}_{progress.id}"
            )
            self._active_operations[operation_key] = progress

            try:
                # Reset status to in-progress
                progress.status = BackfillStatus.IN_PROGRESS
                await self._save_progress(progress)

                # Resume execution from where it left off
                result = await self._execute_backfill(progress, resume=True)

                # Mark as completed or failed
                if result.success:
                    progress.mark_completed()
                else:
                    progress.mark_failed("; ".join(result.error_messages))

                await self._save_progress(progress)
                return result

            finally:
                # Remove from active operations
                self._active_operations.pop(operation_key, None)

        except BackfillProgressError:
            raise
        except Exception as e:
            msg = f"Resume backfill operation failed for backfill {backfill_id}"
            raise BackfillError(
                message=msg,
                backfill_id=backfill_id,
                operation="resume",
            ) from e

    async def get_backfill_status(self, backfill_id: int) -> dict[str, Any]:
        """
        Get current status of a backfill operation.

        Args:
            backfill_id: ID of the backfill operation

        Returns:
            Dictionary with current status information

        Raises:
            BackfillProgressError: If status retrieval fails
        """
        try:
            progress = await self._load_backfill_progress(backfill_id)

            return {
                "backfill_id": progress.id,
                "area_code": progress.area_code,
                "endpoint_name": progress.endpoint_name,
                "status": progress.status.value,
                "progress_percentage": float(progress.progress_percentage),
                "total_chunks": progress.total_chunks,
                "completed_chunks": progress.completed_chunks,
                "failed_chunks": progress.failed_chunks,
                "remaining_chunks": progress.remaining_chunks,
                "total_data_points": progress.total_data_points,
                "success_rate": float(progress.success_rate),
                "started_at": progress.started_at.isoformat()
                if progress.started_at
                else None,
                "completed_at": progress.completed_at.isoformat()
                if progress.completed_at
                else None,
                "estimated_completion": (
                    progress.estimated_completion.isoformat()
                    if progress.estimated_completion
                    else None
                ),
                "last_error": progress.last_error,
                "is_active": progress.is_active,
                "can_be_resumed": progress.can_be_resumed,
                "current_chunk": {
                    "start": progress.current_chunk_start.isoformat()
                    if progress.current_chunk_start
                    else None,
                    "end": progress.current_chunk_end.isoformat()
                    if progress.current_chunk_end
                    else None,
                },
            }

        except Exception as e:
            msg = f"Failed to get backfill status for {backfill_id}"
            raise BackfillProgressError(
                message=msg,
                backfill_id=backfill_id,
                progress_operation="get_status",
            ) from e

    async def list_active_backfills(self) -> list[dict[str, Any]]:
        """
        List all currently active backfill operations using repository pattern.

        Returns:
            List of active backfill operation summaries
        """
        try:
            # Use repository specialized method for active backfills
            active_progresses = await self._progress_repository.get_active_backfills()

            # Convert to summary format
            return [
                self._format_progress_summary(progress)
                for progress in active_progresses
            ]

        except Exception as e:
            msg = f"Failed to list active backfills: {e}"
            raise BackfillProgressError(
                message=msg,
                progress_operation="list_active",
            ) from e

    def _format_progress_summary(self, progress: BackfillProgress) -> dict[str, Any]:
        """Format backfill progress into summary dictionary."""
        return {
            "backfill_id": progress.id,
            "area_code": progress.area_code,
            "endpoint_name": progress.endpoint_name,
            "status": progress.status.value,
            "progress_percentage": float(progress.progress_percentage),
            "completed_chunks": progress.completed_chunks,
            "total_chunks": progress.total_chunks,
            "total_data_points": progress.total_data_points,
            "failed_chunks": progress.failed_chunks,
            "started_at": progress.started_at.isoformat()
            if progress.started_at
            else None,
            "estimated_completion": progress.estimated_completion.isoformat()
            if progress.estimated_completion
            else None,
        }

    # Private helper methods

    async def _analyze_area_endpoint_coverage(
        self,
        area_code: str,
        endpoint_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> CoverageAnalysis:
        """Analyze coverage for a specific area/endpoint combination."""
        try:
            # Get interval for this endpoint
            interval_minutes = self.ENDPOINT_INTERVALS.get(endpoint_name, 60)

            # Calculate expected data points
            total_minutes = int((end_time - start_time).total_seconds() / 60)
            expected_points = total_minutes // interval_minutes

            # Query actual data points from database
            # Map endpoint name to EnergyDataType
            data_type_mapping = {
                "actual_load": "actual",
                "day_ahead_forecast": "day_ahead",
                "week_ahead_forecast": "week_ahead",
                "month_ahead_forecast": "month_ahead",
                "year_ahead_forecast": "year_ahead",
                "forecast_margin": "forecast_margin",
            }

            data_type = data_type_mapping.get(endpoint_name)
            if not data_type:
                self._raise_unknown_endpoint_error(endpoint_name)

            # Query database for actual data points
            # Convert string to enum
            data_type_enum = EnergyDataType(data_type)

            data_points = await self._repository.get_by_time_range(
                start_time=start_time,
                end_time=end_time,
                area_codes=[area_code],
                data_types=[data_type_enum],
            )

            actual_points = len(data_points)
            coverage_percentage = (
                (actual_points / expected_points * 100) if expected_points > 0 else 0.0
            )

            # For now, assume missing periods can be calculated from gaps in data
            # This is a simplified implementation - real implementation would analyze gaps
            missing_periods = []
            if coverage_percentage < FULL_COVERAGE_PERCENTAGE:
                # Add the entire period as missing for simplicity
                # Real implementation would analyze specific gaps
                missing_periods.append((start_time, end_time))

            params = CoverageAnalysisParams(
                area_code=area_code,
                endpoint_name=endpoint_name,
                analysis_period_start=start_time,
                analysis_period_end=end_time,
                expected_data_points=expected_points,
                actual_data_points=actual_points,
                coverage_percentage=coverage_percentage,
                missing_periods=missing_periods,
            )
            return CoverageAnalysis(params)

        except Exception as e:
            msg = f"Coverage analysis failed for {area_code}/{endpoint_name}"
            raise BackfillCoverageError(
                message=msg,
                area_code=area_code,
                endpoint_name=endpoint_name,
                coverage_operation="analyze_area_endpoint",
                analysis_period={"start": start_time, "end": end_time},
            ) from e

    async def _check_resource_limits(self) -> None:
        """Check if resource limits allow starting a new backfill operation."""
        active_count = len(self._active_operations)
        max_concurrent = self._config.max_concurrent_areas

        if active_count >= max_concurrent:
            msg = f"Maximum concurrent backfill operations exceeded ({active_count}/{max_concurrent})"
            raise BackfillResourceError(
                message=msg,
                resource_type="concurrent_operations",
                limit_value=max_concurrent,
                current_value=active_count,
                resource_context={
                    "active_operations": list(self._active_operations.keys())
                },
            )

    async def _create_backfill_progress(
        self,
        area_code: str,
        endpoint_name: str,
        period_start: datetime,
        period_end: datetime,
        chunk_size_days: int,
    ) -> BackfillProgress:
        """Create a new backfill progress record."""
        try:
            # Calculate total chunks
            total_days = (period_end - period_start).days
            total_chunks = max(
                1, (total_days + chunk_size_days - 1) // chunk_size_days
            )  # Ceiling division

            progress = BackfillProgress(
                area_code=area_code,
                endpoint_name=endpoint_name,
                period_start=period_start,
                period_end=period_end,
                status=BackfillStatus.PENDING,
                total_chunks=total_chunks,
                chunk_size_days=chunk_size_days,
                rate_limit_delay=self._config.rate_limit_delay,
            )

            await self._save_progress(progress)

        except Exception as e:
            msg = f"Failed to create backfill progress record for {area_code}/{endpoint_name}"
            raise BackfillProgressError(
                message=msg,
                area_code=area_code,
                endpoint_name=endpoint_name,
                progress_operation="create",
            ) from e
        else:
            return progress

    async def _save_progress(self, progress: BackfillProgress) -> None:
        """Save backfill progress to database using repository pattern."""
        try:
            if progress.id:
                # Update existing record - eliminates session.merge() technical debt
                await self._progress_repository.update(progress)
            else:
                # Create new record and update with generated ID
                created_progress = await self._progress_repository.create(progress)
                progress.id = created_progress.id
        except Exception as e:
            msg = f"Failed to save backfill progress for {progress.area_code}/{progress.endpoint_name}"
            raise BackfillProgressError(
                message=msg,
                backfill_id=progress.id,
                area_code=progress.area_code,
                endpoint_name=progress.endpoint_name,
                progress_operation="save",
                database_error=e,
            ) from e

    async def _load_backfill_progress(self, backfill_id: int) -> BackfillProgress:
        """Load backfill progress from database using repository pattern."""
        try:
            progress = await self._progress_repository.get_by_id(backfill_id)
            if not progress:
                self._raise_progress_not_found_error(backfill_id)
            else:
                return progress
        except BackfillProgressError:
            raise
        except Exception as e:
            msg = f"Failed to load backfill progress for ID {backfill_id}"
            raise BackfillProgressError(
                message=msg,
                backfill_id=backfill_id,
                progress_operation="load",
                database_error=e,
            ) from e

    async def _execute_backfill(
        self, progress: BackfillProgress, *, resume: bool = False
    ) -> BackfillResult:
        """Execute the actual backfill operation with chunking and progress tracking."""
        start_time = datetime.now(UTC)
        error_messages = []
        data_points_collected = 0
        chunks_processed = 0
        chunks_failed = 0

        try:
            # Create time chunks
            chunks = self._create_time_chunks(
                progress.period_start,
                progress.period_end,
                progress.chunk_size_days,
            )

            # Skip completed chunks if resuming
            if resume:
                chunks = chunks[progress.completed_chunks :]
                chunks_processed = progress.completed_chunks
                data_points_collected = progress.total_data_points

            resume_text = "(resuming)" if resume else ""
            msg = (
                f"Executing backfill for {progress.area_code}/{progress.endpoint_name} "
                f"with {len(chunks)} chunks {resume_text}"
            )
            log.info(msg)

            # Process each chunk
            for i, (chunk_start, chunk_end) in enumerate(chunks):
                try:
                    # Update current chunk in progress
                    progress.current_chunk_start = chunk_start
                    progress.current_chunk_end = chunk_end
                    progress.update_progress(
                        completed_chunks=chunks_processed,
                        total_data_points=data_points_collected,
                        current_chunk_start=chunk_start,
                        current_chunk_end=chunk_end,
                    )
                    await self._save_progress(progress)

                    # Collect data for this chunk
                    chunk_data_points = await self._collect_chunk_data(
                        progress.area_code,
                        progress.endpoint_name,
                        chunk_start,
                        chunk_end,
                    )

                    data_points_collected += chunk_data_points
                    chunks_processed += 1

                    msg = (
                        f"Chunk {chunks_processed}/{progress.total_chunks} completed: "
                        f"{chunk_data_points} data points collected"
                    )
                    log.debug(msg)

                    # Rate limiting between chunks
                    if i < len(chunks) - 1:  # Don't sleep after the last chunk
                        await asyncio.sleep(float(progress.rate_limit_delay))

                except (BackfillError, ValueError, ConnectionError) as e:
                    chunks_failed += 1
                    progress.increment_failed_chunks()
                    error_message = (
                        f"Chunk {i + 1} failed ({chunk_start} to {chunk_end}): {e}"
                    )
                    error_messages.append(error_message)
                    log.warning(error_message)

                    # Continue with next chunk rather than failing entirely
                    continue

            # Final progress update
            progress.update_progress(
                completed_chunks=chunks_processed,
                total_data_points=data_points_collected,
            )
            await self._save_progress(progress)

            success = chunks_failed == 0
            end_time = datetime.now(UTC)

            params = BackfillResultParams(
                backfill_id=progress.id,
                area_code=progress.area_code,
                endpoint_name=progress.endpoint_name,
                success=success,
                data_points_collected=data_points_collected,
                chunks_processed=chunks_processed,
                chunks_failed=chunks_failed,
                start_time=start_time,
                end_time=end_time,
                error_messages=error_messages,
            )
            return BackfillResult(params)

        except Exception as e:
            msg = f"Backfill execution failed for {progress.area_code}/{progress.endpoint_name}"
            raise BackfillError(
                message=msg,
                backfill_id=progress.id,
                area_code=progress.area_code,
                endpoint_name=progress.endpoint_name,
                context={
                    "chunks_processed": chunks_processed,
                    "chunks_failed": chunks_failed,
                    "data_points_collected": data_points_collected,
                },
            ) from e

    async def _collect_chunk_data(
        self,
        area_code: str,
        endpoint_name: str,
        chunk_start: datetime,
        chunk_end: datetime,
    ) -> int:
        """Collect data for a single time chunk."""
        try:
            # Validate and get area code
            area = self._get_area_from_code(area_code)

            # Get collector method for endpoint
            collector_method = self._get_collector_method(endpoint_name)

            # Collect raw data
            raw_document = await collector_method(
                bidding_zone=area,
                period_start=chunk_start,
                period_end=chunk_end,
            )

            if not raw_document:
                return 0  # No data available for this period

            # Process and store data
            data_points = await self._process_and_store_data(
                raw_document, area_code, endpoint_name
            )

            return len(data_points)

        except Exception as e:
            msg = f"Chunk data collection failed for {area_code}/{endpoint_name} ({chunk_start} to {chunk_end})"
            raise BackfillError(
                message=msg,
                area_code=area_code,
                endpoint_name=endpoint_name,
                operation="collect_chunk",
                context={
                    "chunk_start": chunk_start.isoformat(),
                    "chunk_end": chunk_end.isoformat(),
                },
            ) from e

    def _create_time_chunks(
        self,
        start_time: datetime,
        end_time: datetime,
        chunk_size_days: int,
    ) -> list[tuple[datetime, datetime]]:
        """Split time range into chunks of specified size."""
        chunks = []
        current_start = start_time
        chunk_delta = timedelta(days=chunk_size_days)

        while current_start < end_time:
            chunk_end = min(current_start + chunk_delta, end_time)
            chunks.append((current_start, chunk_end))
            current_start = chunk_end

        return chunks

    def _get_area_from_code(self, area_code: str) -> AreaCode:  # noqa: RET503
        """Get AreaCode enum from area code string."""
        for area_enum in AreaCode:
            if area_enum.get_country_code() == area_code:
                return area_enum
        self._raise_invalid_area_error(area_code)

    def _get_collector_method(self, endpoint_name: str) -> Callable:
        """Get collector method for the given endpoint name."""
        collector_methods = {
            "actual_load": self._collector.get_actual_total_load,
            "day_ahead_forecast": self._collector.get_day_ahead_load_forecast,
            "week_ahead_forecast": self._collector.get_week_ahead_load_forecast,
            "month_ahead_forecast": self._collector.get_month_ahead_load_forecast,
            "year_ahead_forecast": self._collector.get_year_ahead_load_forecast,
            "forecast_margin": self._collector.get_year_ahead_forecast_margin,
        }

        collector_method = collector_methods.get(endpoint_name)
        if not collector_method:
            self._raise_unknown_endpoint_error(endpoint_name)
        return collector_method

    async def _process_and_store_data(
        self, raw_document: Any, area_code: str, endpoint_name: str
    ) -> list[Any]:
        """Process raw document and store in database."""
        try:
            data_points = await self._processor.process([raw_document])
        except Exception as e:
            raise BackfillError(
                message=f"Processing failed: {e}",
                area_code=area_code,
                endpoint_name=endpoint_name,
                operation="process_chunk",
            ) from e

        # Store in database
        if data_points:
            await self._repository.upsert_batch(data_points)

        return data_points

    def _raise_cannot_resume_error(
        self, backfill_id: int, progress: BackfillProgress
    ) -> NoReturn:
        """Raise error when backfill cannot be resumed."""
        msg = f"Backfill {backfill_id} cannot be resumed (status: {progress.status.value})"
        raise BackfillProgressError(
            message=msg,
            backfill_id=backfill_id,
            progress_operation="resume",
            progress_state={
                "status": progress.status.value,
                "can_resume": progress.can_be_resumed,
            },
        )

    def _raise_progress_not_found_error(self, backfill_id: int) -> NoReturn:
        """Raise error when backfill progress is not found."""
        msg = f"Backfill progress not found for ID {backfill_id}"
        raise BackfillProgressError(
            message=msg,
            backfill_id=backfill_id,
            progress_operation="load",
        )

    def _raise_unknown_endpoint_error(self, endpoint_name: str) -> NoReturn:
        """Raise error for unknown endpoint name."""
        msg = f"Unknown endpoint name: {endpoint_name}"
        raise ValueError(msg)

    def _raise_invalid_area_error(self, area_code: str) -> NoReturn:
        """Raise error for invalid area code."""
        msg = f"Invalid area code: {area_code}"
        raise ValueError(msg)
