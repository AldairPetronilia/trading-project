"""
Scheduler service for automated data collection and analysis operations.

This service provides comprehensive scheduling capabilities for the energy data
service, orchestrating real-time data collection, gap analysis, and backfill
operations using APScheduler with database persistence.

Key Features:
- Real-time data collection scheduling with configurable intervals
- Gap analysis scheduling for data quality monitoring
- Daily backfill analysis for historical data management
- Job health monitoring and failure recovery
- Exponential backoff retry logic with configurable parameters
- Database persistence for scheduler state and job recovery
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, ClassVar, Self

from app.exceptions.service_exceptions import (
    SchedulerConfigurationError,
    SchedulerError,
    SchedulerJobError,
    SchedulerStateError,
)
from apscheduler.executors.asyncio import (
    AsyncIOExecutor,
)
from apscheduler.jobstores.sqlalchemy import (
    SQLAlchemyJobStore,
)
from apscheduler.schedulers.asyncio import (
    AsyncIOScheduler,
)
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import (
    IntervalTrigger,
)
from sqlalchemy import text

if TYPE_CHECKING:
    from collections.abc import Callable

if TYPE_CHECKING:
    from app.config.database import Database
    from app.config.settings import SchedulerConfig
    from app.services.backfill_service import BackfillService
    from app.services.entsoe_data_service import EntsoEDataService

# Set up logging
log = logging.getLogger(__name__)

# Constants
JOB_STORE_ALIAS = "default"
EXECUTOR_ALIAS = "default"


@dataclass
class JobExecutionResult:
    """Result of a scheduled job execution."""

    job_id: str
    job_name: str
    job_type: str
    success: bool
    execution_time_seconds: float
    data_points_collected: int = 0
    areas_processed: int = 0
    endpoints_processed: int = 0
    error_message: str | None = None
    retry_count: int = 0
    next_run_time: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for logging."""
        return {
            "job_id": self.job_id,
            "job_name": self.job_name,
            "job_type": self.job_type,
            "success": self.success,
            "execution_time_seconds": self.execution_time_seconds,
            "data_points_collected": self.data_points_collected,
            "areas_processed": self.areas_processed,
            "endpoints_processed": self.endpoints_processed,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "next_run_time": self.next_run_time.isoformat()
            if self.next_run_time
            else None,
        }


@dataclass
class ScheduleExecutionResult:
    """Result of a scheduler operation."""

    operation: str
    success: bool
    message: str
    timestamp: datetime
    job_results: list[JobExecutionResult] | None = None
    scheduler_state: dict[str, Any] | None = None
    error_context: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for logging."""
        return {
            "operation": self.operation,
            "success": self.success,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "job_results_count": len(self.job_results) if self.job_results else 0,
            "scheduler_state": self.scheduler_state,
            "error_context": self.error_context,
        }


class SchedulerService:
    """
    Service for automated scheduling of data collection and analysis operations.

    This service orchestrates the scheduling of various data operations including:
    - Real-time data collection from ENTSO-E APIs
    - Gap analysis to identify missing data periods
    - Daily backfill analysis to ensure historical data completeness
    - Job health monitoring and failure recovery

    The service uses APScheduler with database persistence to ensure job
    continuity across service restarts and provides comprehensive error
    handling with exponential backoff retry logic.
    """

    # Job type identifiers for tracking and management
    JOB_TYPES: ClassVar[dict[str, str]] = {
        "REAL_TIME_COLLECTION": "real_time_collection",
        "GAP_ANALYSIS": "gap_analysis",
        "DAILY_BACKFILL_ANALYSIS": "daily_backfill_analysis",
        "HEALTH_CHECK": "health_check",
    }

    def __init__(
        self,
        entsoe_data_service: EntsoEDataService,
        backfill_service: BackfillService,
        database: Database,
        config: SchedulerConfig,
    ) -> None:
        """
        Initialize the scheduler service.

        Args:
            entsoe_data_service: Service for ENTSO-E data collection operations
            backfill_service: Service for historical data backfill operations
            database: Database instance for scheduler persistence
            config: Scheduler configuration settings
        """
        self._entsoe_data_service = entsoe_data_service
        self._backfill_service = backfill_service
        self._database = database
        self._config = config
        self._scheduler: AsyncIOScheduler | None = None
        self._is_running = False
        self._job_failure_counts: dict[str, int] = {}
        self._last_successful_runs: dict[str, datetime] = {}

    async def start(self) -> ScheduleExecutionResult:
        """
        Start the scheduler service and configure all scheduled jobs.

        Returns:
            ScheduleExecutionResult with startup status and configuration

        Raises:
            SchedulerStateError: If scheduler fails to start
            SchedulerConfigurationError: If configuration is invalid
        """
        try:
            if self._is_running:
                return ScheduleExecutionResult(
                    operation="start",
                    success=False,
                    message="Scheduler is already running",
                    timestamp=datetime.now(UTC),
                    scheduler_state={"is_running": True},
                )

            if not self._config.enabled:
                return ScheduleExecutionResult(
                    operation="start",
                    success=False,
                    message="Scheduler is disabled in configuration",
                    timestamp=datetime.now(UTC),
                    scheduler_state={"enabled": False},
                )

            # Initialize APScheduler
            await self._initialize_scheduler()

            # Configure scheduled jobs based on configuration
            await self._configure_jobs()

            # Start the scheduler
            if self._scheduler is not None:
                self._scheduler.start()
                self._is_running = True

            msg = "Scheduler service started successfully"
            log.info(msg)

            return ScheduleExecutionResult(
                operation="start",
                success=True,
                message=msg,
                timestamp=datetime.now(UTC),
                scheduler_state=self._get_scheduler_state(),
            )

        except Exception as e:
            msg = f"Failed to start scheduler service: {e}"
            raise SchedulerStateError(
                message=msg,
                expected_state="running",
                actual_state="stopped",
                state_operation="start",
            ) from e

    async def stop(self) -> ScheduleExecutionResult:
        """
        Stop the scheduler service and shut down all scheduled jobs.

        Returns:
            ScheduleExecutionResult with shutdown status

        Raises:
            SchedulerStateError: If scheduler fails to stop properly
        """
        try:
            if not self._is_running or not self._scheduler:
                return ScheduleExecutionResult(
                    operation="stop",
                    success=True,
                    message="Scheduler is already stopped",
                    timestamp=datetime.now(UTC),
                    scheduler_state={"is_running": False},
                )

            # Shutdown scheduler gracefully
            if self._scheduler is not None:
                self._scheduler.shutdown(wait=True)
                self._scheduler = None
                self._is_running = False

            # Clear internal state
            await self._cleanup_resources()

            msg = "Scheduler service stopped successfully"
            log.info(msg)

            return ScheduleExecutionResult(
                operation="stop",
                success=True,
                message=msg,
                timestamp=datetime.now(UTC),
                scheduler_state={"is_running": False},
            )

        except Exception as e:
            msg = f"Failed to stop scheduler service: {e}"
            raise SchedulerStateError(
                message=msg,
                expected_state="stopped",
                actual_state="running",
                state_operation="stop",
            ) from e

    async def get_status(self) -> dict[str, Any]:
        """
        Get current status of the scheduler and all scheduled jobs.

        Returns:
            Dictionary with comprehensive scheduler status information
        """
        try:
            if not self._scheduler:
                return {
                    "is_running": False,
                    "scheduler_state": "not_initialized",
                    "jobs": [],
                    "failure_counts": {},
                    "last_successful_runs": {},
                }

            jobs_info = []
            if self._scheduler is not None:
                for job in self._scheduler.get_jobs():
                    job_info = {
                        "id": job.id,
                        "name": job.name,
                        "next_run_time": job.next_run_time.isoformat()
                        if job.next_run_time
                        else None,
                        "trigger": str(job.trigger),
                        "executor": job.executor,
                        "max_instances": job.max_instances,
                        "misfire_grace_time": job.misfire_grace_time,
                        "failure_count": self._job_failure_counts.get(job.id, 0),
                        "last_successful_run": (
                            self._last_successful_runs[job.id].isoformat()
                            if job.id in self._last_successful_runs
                            else None
                        ),
                    }
                    jobs_info.append(job_info)

            return {
                "is_running": self._is_running,
                "scheduler_state": "running" if self._is_running else "stopped",
                "jobs": jobs_info,
                "failure_counts": dict(self._job_failure_counts),
                "last_successful_runs": {
                    job_id: timestamp.isoformat()
                    for job_id, timestamp in self._last_successful_runs.items()
                },
                "config_enabled": self._config.enabled,
                "total_jobs": len(jobs_info),
            }

        except Exception as e:
            msg = f"Failed to get scheduler status: {e}"
            raise SchedulerError(
                message=msg,
                scheduler_operation="get_status",
            ) from e

    async def trigger_real_time_collection(self) -> ScheduleExecutionResult:
        """
        Manually trigger real-time data collection.

        Returns:
            ScheduleExecutionResult with collection results

        Raises:
            SchedulerJobError: If real-time collection fails
        """
        try:
            start_time = datetime.now(UTC)

            # Execute real-time collection
            results = await self._entsoe_data_service.collect_all_gaps()

            execution_time = (datetime.now(UTC) - start_time).total_seconds()

            # Calculate totals
            total_data_points = sum(
                result.stored_count
                for area_results in results.values()
                for result in area_results.values()
            )
            successful_collections = sum(
                1
                for area_results in results.values()
                for result in area_results.values()
                if result.success
            )

            job_result = JobExecutionResult(
                job_id="manual_real_time_collection",
                job_name="Manual Real-Time Collection",
                job_type=self.JOB_TYPES["REAL_TIME_COLLECTION"],
                success=successful_collections > 0,
                execution_time_seconds=execution_time,
                data_points_collected=total_data_points,
                areas_processed=len(results),
                endpoints_processed=successful_collections,
            )

            return ScheduleExecutionResult(
                operation="trigger_real_time_collection",
                success=job_result.success,
                message=f"Real-time collection completed: {total_data_points} data points collected",
                timestamp=datetime.now(UTC),
                job_results=[job_result],
            )

        except Exception as e:
            msg = f"Manual real-time collection failed: {e}"
            raise SchedulerJobError(
                message=msg,
                job_name="Manual Real-Time Collection",
                job_type=self.JOB_TYPES["REAL_TIME_COLLECTION"],
            ) from e

    async def trigger_gap_analysis(self) -> ScheduleExecutionResult:
        """
        Manually trigger gap analysis.

        Returns:
            ScheduleExecutionResult with gap analysis results

        Raises:
            SchedulerJobError: If gap analysis fails
        """
        try:
            start_time = datetime.now(UTC)

            # Execute gap analysis
            coverage_results = await self._backfill_service.analyze_coverage()

            execution_time = (datetime.now(UTC) - start_time).total_seconds()

            # Count results that need backfill
            backfill_needed = sum(
                1 for result in coverage_results if result.needs_backfill
            )

            job_result = JobExecutionResult(
                job_id="manual_gap_analysis",
                job_name="Manual Gap Analysis",
                job_type=self.JOB_TYPES["GAP_ANALYSIS"],
                success=True,
                execution_time_seconds=execution_time,
                areas_processed=len({result.area_code for result in coverage_results}),
                endpoints_processed=len(coverage_results),
            )

            return ScheduleExecutionResult(
                operation="trigger_gap_analysis",
                success=True,
                message=f"Gap analysis completed: {backfill_needed} areas/endpoints need backfill",
                timestamp=datetime.now(UTC),
                job_results=[job_result],
            )

        except Exception as e:
            msg = f"Manual gap analysis failed: {e}"
            raise SchedulerJobError(
                message=msg,
                job_name="Manual Gap Analysis",
                job_type=self.JOB_TYPES["GAP_ANALYSIS"],
            ) from e

    # Private methods for scheduler management

    def _ensure_scheduler_initialized(self) -> None:
        """Ensure scheduler is initialized, raise error if not."""
        if self._scheduler is None:
            msg = "Scheduler not initialized"
            raise SchedulerConfigurationError(
                message=msg,
                configuration_field="scheduler_initialization",
                suggested_fix="Ensure scheduler is properly initialized before configuring jobs",
            )

    async def _initialize_scheduler(self) -> None:
        """Initialize the APScheduler with database persistence."""
        try:
            # Validate database connectivity before proceeding
            # This ensures that scheduled jobs will have access to the database when they run
            await self._validate_database_connectivity()

            # Configure job store for database persistence
            jobstores = {}
            if self._config.use_persistent_job_store:
                # APScheduler needs a synchronous database URL
                # Convert from postgresql+asyncpg:// to postgresql://
                sync_url = self._database.config.database.url.replace(
                    "postgresql+asyncpg://", "postgresql://"
                )
                jobstore = SQLAlchemyJobStore(
                    url=sync_url,
                    tablename="scheduler_jobs",
                )
                jobstores[JOB_STORE_ALIAS] = jobstore

            # Configure executors
            executors = {
                EXECUTOR_ALIAS: AsyncIOExecutor(),
            }

            # Configure job defaults
            job_defaults = {
                "coalesce": self._config.job_defaults_coalesce,
                "max_instances": self._config.job_defaults_max_instances,
                "misfire_grace_time": self._config.job_defaults_misfire_grace_time_seconds,
            }

            # Create scheduler
            self._scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone=UTC,
            )

            log.info("APScheduler initialized successfully")

        except Exception as e:
            msg = f"Failed to initialize APScheduler: {e}"
            raise SchedulerConfigurationError(
                message=msg,
                configuration_field="scheduler_initialization",
                suggested_fix="Check database connectivity and configuration",
            ) from e

    async def _configure_jobs(self) -> None:
        """Configure all scheduled jobs based on configuration."""
        try:
            # Real-time data collection job
            if self._config.real_time_collection_enabled:
                self._ensure_scheduler_initialized()
                assert self._scheduler is not None  # noqa: S101
                self._scheduler.add_job(
                    func=self._execute_real_time_collection_job,
                    trigger=IntervalTrigger(
                        minutes=self._config.real_time_collection_interval_minutes
                    ),
                    id="real_time_collection",
                    name="Real-Time Data Collection",
                    replace_existing=True,
                )
                log.info(
                    "Configured real-time collection job: every %d minutes",
                    self._config.real_time_collection_interval_minutes,
                )

            # Gap analysis job
            if self._config.gap_analysis_enabled:
                self._ensure_scheduler_initialized()
                assert self._scheduler is not None  # noqa: S101
                self._scheduler.add_job(
                    func=self._execute_gap_analysis_job,
                    trigger=IntervalTrigger(
                        hours=self._config.gap_analysis_interval_hours
                    ),
                    id="gap_analysis",
                    name="Gap Analysis",
                    replace_existing=True,
                )
                log.info(
                    "Configured gap analysis job: every %d hours",
                    self._config.gap_analysis_interval_hours,
                )

            # Daily backfill analysis job
            if self._config.daily_backfill_analysis_enabled:
                self._ensure_scheduler_initialized()
                assert self._scheduler is not None  # noqa: S101
                self._scheduler.add_job(
                    func=self._execute_daily_backfill_analysis_job,
                    trigger=CronTrigger(
                        hour=self._config.daily_backfill_analysis_hour,
                        minute=self._config.daily_backfill_analysis_minute,
                    ),
                    id="daily_backfill_analysis",
                    name="Daily Backfill Analysis",
                    replace_existing=True,
                )
                log.info(
                    "Configured daily backfill analysis job: daily at %02d:%02d",
                    self._config.daily_backfill_analysis_hour,
                    self._config.daily_backfill_analysis_minute,
                )

            # Health check job
            self._ensure_scheduler_initialized()
            assert self._scheduler is not None  # noqa: S101
            self._scheduler.add_job(
                func=self._execute_health_check_job,
                trigger=IntervalTrigger(
                    minutes=self._config.job_health_check_interval_minutes
                ),
                id="health_check",
                name="Job Health Monitor",
                replace_existing=True,
            )
            log.info(
                "Configured health check job: every %d minutes",
                self._config.job_health_check_interval_minutes,
            )

        except Exception as e:
            msg = f"Failed to configure scheduled jobs: {e}"
            raise SchedulerConfigurationError(
                message=msg,
                configuration_field="job_configuration",
                suggested_fix="Check job configuration parameters",
            ) from e

    async def _execute_real_time_collection_job(self) -> None:
        """Execute the real-time data collection job with error handling."""
        job_id = "real_time_collection"
        job_name = "Real-Time Data Collection"
        start_time = datetime.now(UTC)

        try:
            log.info("Starting %s", job_name)

            # Execute real-time collection
            results = await self._entsoe_data_service.collect_all_gaps()

            execution_time = (datetime.now(UTC) - start_time).total_seconds()

            # Calculate totals
            total_data_points = sum(
                result.stored_count
                for area_results in results.values()
                for result in area_results.values()
            )
            successful_collections = sum(
                1
                for area_results in results.values()
                for result in area_results.values()
                if result.success
            )

            # Update tracking
            self._job_failure_counts.pop(job_id, None)  # Reset failure count on success
            self._last_successful_runs[job_id] = datetime.now(UTC)

            log.info(
                "%s completed successfully: %d data points collected "
                "from %d endpoints in %.2fs",
                job_name,
                total_data_points,
                successful_collections,
                execution_time,
            )

        except (SchedulerError, SchedulerJobError) as e:
            await self._handle_job_failure(job_id, job_name, e)
        except Exception as e:  # noqa: BLE001
            scheduler_error = SchedulerJobError(
                message=f"Unexpected error in {job_name}: {e}",
                job_name=job_name,
                job_type=self.JOB_TYPES["REAL_TIME_COLLECTION"],
            )
            await self._handle_job_failure(job_id, job_name, scheduler_error)

    async def _execute_gap_analysis_job(self) -> None:
        """Execute the gap analysis job with error handling."""
        job_id = "gap_analysis"
        job_name = "Gap Analysis"
        start_time = datetime.now(UTC)

        try:
            log.info("Starting %s", job_name)

            # Execute gap analysis
            coverage_results = await self._backfill_service.analyze_coverage()

            execution_time = (datetime.now(UTC) - start_time).total_seconds()

            # Count results that need backfill
            backfill_needed = sum(
                1 for result in coverage_results if result.needs_backfill
            )

            # Update tracking
            self._job_failure_counts.pop(job_id, None)  # Reset failure count on success
            self._last_successful_runs[job_id] = datetime.now(UTC)

            log.info(
                "%s completed successfully: analyzed %d area/endpoint combinations, "
                "%d need backfill in %.2fs",
                job_name,
                len(coverage_results),
                backfill_needed,
                execution_time,
            )

            # Log areas that need backfill for monitoring
            if backfill_needed > 0:
                needing_backfill = [
                    f"{result.area_code}/{result.endpoint_name} ({result.coverage_percentage:.1f}%)"
                    for result in coverage_results
                    if result.needs_backfill
                ]
                log.warning(
                    "Areas/endpoints needing backfill: %s", ", ".join(needing_backfill)
                )

        except (SchedulerError, SchedulerJobError) as e:
            await self._handle_job_failure(job_id, job_name, e)
        except Exception as e:  # noqa: BLE001
            scheduler_error = SchedulerJobError(
                message=f"Unexpected error in {job_name}: {e}",
                job_name=job_name,
                job_type=self.JOB_TYPES["GAP_ANALYSIS"],
            )
            await self._handle_job_failure(job_id, job_name, scheduler_error)

    async def _execute_daily_backfill_analysis_job(self) -> None:
        """Execute the daily backfill analysis job with error handling."""
        job_id = "daily_backfill_analysis"
        job_name = "Daily Backfill Analysis"
        start_time = datetime.now(UTC)

        try:
            log.info("Starting %s", job_name)

            # Execute comprehensive coverage analysis
            coverage_results = await self._backfill_service.analyze_coverage(
                years_back=self._config.max_retry_attempts  # Use config value
            )

            execution_time = (datetime.now(UTC) - start_time).total_seconds()

            # Process results and potentially trigger backfills
            backfill_needed = [
                result for result in coverage_results if result.needs_backfill
            ]

            # Update tracking
            self._job_failure_counts.pop(job_id, None)  # Reset failure count on success
            self._last_successful_runs[job_id] = datetime.now(UTC)

            log.info(
                "%s completed successfully: analyzed %d combinations, "
                "%d need backfill in %.2fs",
                job_name,
                len(coverage_results),
                len(backfill_needed),
                execution_time,
            )

            # Log detailed backfill analysis
            if backfill_needed:
                for result in backfill_needed:
                    log.info(
                        "Backfill needed: %s/%s - Coverage: %.1f%%, Missing: %d data points",
                        result.area_code,
                        result.endpoint_name,
                        result.coverage_percentage,
                        result.total_missing_points,
                    )

        except (SchedulerError, SchedulerJobError) as e:
            await self._handle_job_failure(job_id, job_name, e)
        except Exception as e:  # noqa: BLE001
            scheduler_error = SchedulerJobError(
                message=f"Unexpected error in {job_name}: {e}",
                job_name=job_name,
                job_type=self.JOB_TYPES["DAILY_BACKFILL_ANALYSIS"],
            )
            await self._handle_job_failure(job_id, job_name, scheduler_error)

    async def _execute_health_check_job(self) -> None:
        """Execute health check monitoring for all jobs."""
        job_id = "health_check"
        job_name = "Job Health Monitor"

        try:
            current_time = datetime.now(UTC)
            unhealthy_jobs = []

            # Check all jobs for health issues
            for other_job_id, failure_count in self._job_failure_counts.items():
                if failure_count >= self._config.failed_job_notification_threshold:
                    unhealthy_jobs.append(f"{other_job_id} ({failure_count} failures)")

            if unhealthy_jobs:
                log.warning("Unhealthy jobs detected: %s", ", ".join(unhealthy_jobs))

            # Update tracking for health check job itself
            self._last_successful_runs[job_id] = current_time

            log.debug(
                "%s completed - %d unhealthy jobs detected",
                job_name,
                len(unhealthy_jobs),
            )

        except Exception:
            # Health check failures are logged but don't trigger retry logic
            log.exception("%s failed", job_name)

    async def _handle_job_failure(
        self, job_id: str, job_name: str, error: Exception
    ) -> None:
        """Handle job failure with retry logic and error tracking."""
        try:
            # Increment failure count
            self._job_failure_counts[job_id] = (
                self._job_failure_counts.get(job_id, 0) + 1
            )
            failure_count = self._job_failure_counts[job_id]

            log.error("%s failed (attempt %d): %s", job_name, failure_count, error)

            # Check if we should retry
            if failure_count < self._config.max_retry_attempts:
                # Calculate exponential backoff delay
                delay = min(
                    self._config.retry_backoff_base_seconds
                    * (2 ** (failure_count - 1)),
                    self._config.retry_backoff_max_seconds,
                )

                # Add jitter to prevent thundering herd
                secure_random = secrets.SystemRandom()
                jitter = secure_random.uniform(0.1, 0.3) * delay
                total_delay = delay + jitter

                log.info(
                    "Retrying %s in %.1f seconds (attempt %d)",
                    job_name,
                    total_delay,
                    failure_count + 1,
                )

                # Schedule retry
                retry_time = datetime.now(UTC) + timedelta(seconds=total_delay)
                if self._scheduler is None:
                    log.error(
                        "Cannot schedule retry for %s: scheduler not initialized",
                        job_name,
                    )
                    return
                self._scheduler.add_job(
                    func=self._get_job_function(job_id),
                    trigger="date",
                    run_date=retry_time,
                    id=f"{job_id}_retry_{failure_count}",
                    name=f"{job_name} (Retry {failure_count})",
                    replace_existing=True,
                )
            else:
                log.error(
                    "%s has exceeded maximum retry attempts (%d). Manual intervention required.",
                    job_name,
                    self._config.max_retry_attempts,
                )

        except SchedulerError:
            log.exception("Failed to handle job failure for %s", job_name)
            raise
        except Exception as retry_error:
            log.exception("Unexpected error handling job failure for %s", job_name)
            raise SchedulerError(
                message=f"Unexpected error in job failure handling: {retry_error}",
                scheduler_operation="handle_job_failure",
            ) from retry_error

    def _get_job_function(self, job_id: str) -> Callable[[], Any]:
        """Get the job function based on job ID."""
        job_functions = {
            "real_time_collection": self._execute_real_time_collection_job,
            "gap_analysis": self._execute_gap_analysis_job,
            "daily_backfill_analysis": self._execute_daily_backfill_analysis_job,
            "health_check": self._execute_health_check_job,
        }
        return job_functions.get(job_id, self._execute_health_check_job)

    def _get_scheduler_state(self) -> dict[str, Any]:
        """Get current scheduler state for diagnostics."""
        if not self._scheduler:
            return {"initialized": False}

        return {
            "initialized": True,
            "running": self._scheduler.running,
            "jobs_count": len(self._scheduler.get_jobs()),
            "state": self._scheduler.state,
        }

    async def _validate_database_connectivity(self) -> None:
        """
        Validate database connectivity before starting the scheduler.

        Scheduled jobs require database access, so we validate connectivity
        during scheduler initialization to fail fast if the database is unavailable.

        Raises:
            SchedulerConfigurationError: If database connection fails
        """

        def _raise_validation_error(message: str) -> None:
            """Raise database validation error with proper context."""
            raise SchedulerConfigurationError(
                message=message,
                configuration_field="database_connection",
                suggested_fix="Verify database configuration and ensure database is running",
            ) from None

        try:
            # Test database connectivity by attempting to create a session
            async for session in self._database.get_database_session():
                # Execute a simple query to verify the connection works
                result = await session.execute(text("SELECT 1 as test"))
                test_value = result.scalar()

                if test_value != 1:
                    _raise_validation_error(
                        "Database connectivity test returned unexpected result"
                    )

                # Break out of the loop after the first successful test
                break

            log.info("Database connectivity validated successfully")

        except SchedulerConfigurationError:
            # Re-raise configuration errors as-is
            raise
        except Exception as e:
            msg = f"Database connectivity validation failed: {e}"
            raise SchedulerConfigurationError(
                message=msg,
                configuration_field="database_connection",
                suggested_fix="Verify database configuration and ensure database is running",
            ) from e

    async def _cleanup_resources(self) -> None:
        """Clean up internal resources and state."""
        try:
            # Clear failure tracking
            self._job_failure_counts.clear()
            self._last_successful_runs.clear()

            log.debug("Scheduler resources cleaned up successfully")
        except Exception:
            log.exception("Error during resource cleanup")

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit with cleanup."""
        try:
            await self.stop()
        except Exception:
            log.exception("Error during context manager cleanup")
