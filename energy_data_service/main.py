"""
Main application entry point for the Energy Data Service.

This module provides a production-ready entry point for running the energy data
collection service. Key features include:

- Configurable logging based on environment settings
- Database initialization with TimescaleDB hypertables
- ENTSO-E API configuration validation
- Startup backfill analysis and gap filling
- Data collection verification and summary statistics
- Graceful shutdown handling with signal management
- Comprehensive error handling with user-friendly messages

The service automatically:
1. Validates database connectivity and schema
2. Configures TimescaleDB for time-series data
3. Validates ENTSO-E API credentials
4. Starts the scheduler service for automated data collection
5. Performs startup backfill to fill historical gaps (configurable)
6. Shows data collection summary and statistics
7. Runs continuous data collection until shutdown signal
"""

import asyncio
import logging
import signal
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

from app.container import Container
from app.exceptions.service_exceptions import BackfillError, ServiceError
from app.models.base import Base
from app.models.load_data import EnergyDataPoint
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection

# Constants
MIN_API_TOKEN_LENGTH = 10


class SimpleSchedulerRunner:
    """
    Production application runner for the Energy Data Service.

    Orchestrates the complete lifecycle of the energy data collection service,
    including database setup, configuration validation, scheduler startup,
    backfill operations, and graceful shutdown handling.
    """

    def __init__(self) -> None:
        """Initialize the runner with container and shutdown handling."""
        self.container = Container()
        self.shutdown_event = asyncio.Event()

        # Get settings for logging configuration
        settings = self.container.config()

        # Setup logging based on configuration
        log_level = getattr(logging, settings.logging.level, logging.INFO)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        self.logger = logging.getLogger(__name__)

    def setup_signal_handlers(self) -> None:
        """Setup graceful shutdown signal handlers."""

        def signal_handler(signum: int, _frame: Any) -> None:
            self.logger.info("Received shutdown signal: %s", signum)
            self.shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def _verify_data_collection(self) -> None:
        """Verify data collection by showing summary statistics."""
        try:
            self.logger.info("Verifying data collection...")

            # Get database from container
            database = self.container.database()

            async with database.session_factory() as session:
                # Count total data points
                total_count_stmt = select(func.count(EnergyDataPoint.timestamp))
                total_result = await session.execute(total_count_stmt)
                total_count = total_result.scalar() or 0

                if total_count == 0:
                    self.logger.warning("No data points found in database")
                    return

                # Get date range
                min_date_stmt = select(func.min(EnergyDataPoint.timestamp))
                max_date_stmt = select(func.max(EnergyDataPoint.timestamp))

                min_result = await session.execute(min_date_stmt)
                max_result = await session.execute(max_date_stmt)

                min_date = min_result.scalar()
                max_date = max_result.scalar()

                # Count unique areas
                unique_areas_stmt = select(
                    func.count(func.distinct(EnergyDataPoint.area_code))
                )
                areas_result = await session.execute(unique_areas_stmt)
                unique_areas = areas_result.scalar() or 0

                # Count recent data (last 24 hours)
                recent_cutoff = datetime.now(UTC) - timedelta(days=1)
                recent_count_stmt = select(func.count(EnergyDataPoint.timestamp)).where(
                    EnergyDataPoint.timestamp >= recent_cutoff
                )
                recent_result = await session.execute(recent_count_stmt)
                recent_count = recent_result.scalar() or 0

                # Log summary
                self.logger.info(
                    "Data Collection Summary:\n"
                    "  Total data points: %s\n"
                    "  Date range: %s to %s\n"
                    "  Unique areas: %s\n"
                    "  Recent data (24h): %s points",
                    f"{total_count:,}",
                    min_date,
                    max_date,
                    unique_areas,
                    f"{recent_count:,}",
                )

        except Exception:
            self.logger.exception("Data verification failed")
            # Don't fail startup if verification fails

    async def _perform_startup_backfill(self) -> None:
        """Perform backfill analysis and fill gaps on startup using configured settings."""
        try:
            self.logger.info("Starting startup backfill analysis...")

            # Get backfill service and settings from container
            backfill_service = self.container.backfill_service()
            settings = self.container.config()

            # Calculate coverage analysis period based on backfill config
            analysis_years = settings.backfill.historical_years
            self.logger.info("Analyzing coverage for last %s years", analysis_years)

            coverage_results = await backfill_service.analyze_coverage(
                years_back=analysis_years
            )

            # Find areas that need backfilling
            needed_backfills = [r for r in coverage_results if r.needs_backfill]

            self.logger.info(
                "Coverage analysis complete: %s of %s "
                "area/endpoint combinations need backfilling",
                len(needed_backfills),
                len(coverage_results),
            )

            # Track statistics for summary
            total_areas_processed = 0
            total_data_points = 0
            successful_backfills = 0
            failed_backfills = 0

            if needed_backfills:
                self.logger.info(
                    "Processing backfills for all %s area/endpoint combinations",
                    len(needed_backfills),
                )

                for result in needed_backfills:
                    total_areas_processed += 1
                    self.logger.info(
                        "Backfilling %s - %s (coverage: %.1f%%)",
                        result.area_code,
                        result.endpoint_name,
                        result.coverage_percentage,
                    )

                    try:
                        # Calculate backfill period using configured historical years
                        end_time = datetime.now(UTC)
                        start_time = end_time - timedelta(days=365 * analysis_years)

                        backfill_result = await backfill_service.start_backfill(
                            area_code=result.area_code,
                            endpoint_name=result.endpoint_name,
                            period_start=start_time,
                            period_end=end_time,
                        )

                        if backfill_result.success:
                            successful_backfills += 1
                            total_data_points += backfill_result.data_points_collected
                            self.logger.info(
                                "✓ Backfill completed for %s - %s: "
                                "%s data points collected",
                                result.area_code,
                                result.endpoint_name,
                                backfill_result.data_points_collected,
                            )
                        else:
                            failed_backfills += 1
                            error_msg = (
                                "; ".join(backfill_result.error_messages)
                                if backfill_result.error_messages
                                else "Unknown error"
                            )
                            self.logger.warning(
                                "✗ Backfill failed for %s - %s: %s",
                                result.area_code,
                                result.endpoint_name,
                                error_msg,
                            )

                    except (BackfillError, ServiceError, SQLAlchemyError) as e:
                        failed_backfills += 1
                        self.logger.warning(
                            "✗ Backfill failed for %s - %s: %s",
                            result.area_code,
                            result.endpoint_name,
                            e,
                        )
                        # Continue with other backfills even if one fails

                # Log summary statistics
                self.logger.info(
                    "Startup backfill summary: %s successful, %s failed, "
                    "%s total data points collected",
                    successful_backfills,
                    failed_backfills,
                    total_data_points,
                )
            else:
                self.logger.info("No backfills needed - data coverage is sufficient")

        except Exception:
            self.logger.exception("Startup backfill analysis failed")
            # Don't fail the entire startup if backfill fails
            self.logger.info("Continuing startup despite backfill failure")

    async def _initialize_database(self) -> None:
        """Initialize database connection and create tables."""
        try:
            database = self.container.database()
            self.logger.info("Database connection initialized")
        except Exception:
            self.logger.exception("Failed to initialize database connection")
            self.logger.exception(
                "Please check your database configuration and ensure the database is running"
            )
            sys.exit(1)

        # Create database tables if they don't exist
        try:
            async with database.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await self._setup_timescaledb(conn)
            self.logger.info("Database schema initialized")
        except Exception:
            self.logger.exception("Failed to initialize database schema")
            self.logger.exception(
                "Please ensure TimescaleDB is properly installed and accessible"
            )
            sys.exit(1)

    async def _setup_timescaledb(self, conn: AsyncConnection) -> None:
        """Setup TimescaleDB extensions, hypertables and compression."""
        # Create TimescaleDB extension if not exists
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))

        # Create hypertables for time-series data
        try:
            await conn.execute(
                text(
                    "SELECT create_hypertable('energy_data_points', 'timestamp', "
                    "if_not_exists => TRUE);"
                )
            )
            self.logger.info("TimescaleDB hypertable configured")
        except SQLAlchemyError:
            # Hypertable might already exist or table might not exist yet
            self.logger.debug("Hypertable creation skipped")

        # Enable compression for better storage efficiency
        try:
            await conn.execute(
                text(
                    "ALTER TABLE energy_data_points SET ("
                    "timescaledb.compress, "
                    "timescaledb.compress_segmentby = 'area_code, data_type, business_type', "
                    "timescaledb.compress_orderby = 'timestamp DESC'"
                    ");"
                )
            )
            self.logger.info("TimescaleDB compression enabled")
        except SQLAlchemyError:
            # Compression might already be enabled
            self.logger.debug("Compression setup skipped")

        # Add compression policy to automatically compress chunks older than 7 days
        try:
            await conn.execute(
                text(
                    "SELECT add_compression_policy('energy_data_points', INTERVAL '7 days');"
                )
            )
            self.logger.info("TimescaleDB compression policy configured")
        except SQLAlchemyError:
            # Policy might already exist
            self.logger.debug("Compression policy setup skipped")

    def _validate_api_configuration(self) -> None:
        """Validate ENTSO-E API configuration."""
        try:
            settings = self.container.config()
            api_token = settings.entsoe_client.api_token.get_secret_value()
            if not api_token or len(api_token) < MIN_API_TOKEN_LENGTH:
                self.logger.error("ENTSO-E API token is missing or invalid")
                self.logger.error(
                    "Please set ENTSOE_CLIENT__API_TOKEN environment variable"
                )
                sys.exit(1)
            self.logger.info("ENTSO-E API configuration validated")
        except Exception:
            self.logger.exception("Failed to validate ENTSO-E API configuration")
            sys.exit(1)

    async def _start_scheduler_service(self) -> Any:
        """Start the scheduler service."""
        try:
            scheduler_service = self.container.scheduler_service()
            start_result = await scheduler_service.start()

            if not start_result.success:
                self.logger.error("Failed to start scheduler: %s", start_result.message)
                self.logger.error(
                    "Check your configuration and ensure all required services are available"
                )
                sys.exit(1)
            else:
                self.logger.info("Scheduler service started successfully")
                return scheduler_service
        except Exception:
            self.logger.exception("Failed to initialize scheduler service")
            sys.exit(1)

    async def _perform_startup_tasks(self, settings: Any) -> None:
        """Perform startup backfill and data verification tasks."""
        # Perform startup backfill analysis and fill gaps (if enabled)
        if settings.backfill.startup_backfill_enabled:
            await self._perform_startup_backfill()
            self.logger.info("Startup backfill analysis completed")
        else:
            self.logger.info("Startup backfill disabled in configuration")

        # Verify data collection and show summary (if enabled)
        if settings.backfill.startup_data_verification_enabled:
            await self._verify_data_collection()
        else:
            self.logger.info("Startup data verification disabled in configuration")

    async def run(self) -> None:
        """Run the scheduler service with proper initialization and cleanup."""
        self.setup_signal_handlers()

        try:
            self.logger.info("=" * 60)
            self.logger.info("🔋 Energy Data Service Starting")
            self.logger.info("=" * 60)

            # Initialize database and create tables
            await self._initialize_database()

            # Validate ENTSO-E API configuration
            self._validate_api_configuration()
            settings = self.container.config()

            # Start scheduler service
            scheduler_service = await self._start_scheduler_service()

            # Perform startup tasks
            await self._perform_startup_tasks(settings)

            # Startup complete
            self.logger.info("=" * 60)
            self.logger.info("✅ Energy Data Service Ready - Collecting Data")
            self.logger.info("=" * 60)

            # Wait for shutdown signal
            self.logger.info("Press Ctrl+C to stop the service")
            await self.shutdown_event.wait()

            # Stop scheduler service
            self.logger.info("Stopping scheduler service...")
            stop_result = await scheduler_service.stop()
            if stop_result.success:
                self.logger.info("Scheduler service stopped successfully")
            else:
                self.logger.error("Error stopping scheduler: %s", stop_result.message)

        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception:
            self.logger.exception("Application error")
            sys.exit(1)
        finally:
            self.logger.info("Shutdown complete")


async def main() -> None:
    """Main entry point."""
    runner = SimpleSchedulerRunner()
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
