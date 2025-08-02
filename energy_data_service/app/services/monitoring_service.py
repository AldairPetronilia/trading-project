"""
Monitoring service for data collection performance and health tracking.

This service provides comprehensive monitoring capabilities for the energy data
collection pipeline, offering real-time performance metrics, success rate analysis,
and anomaly detection across different energy areas and data types.

Key Features:
- Collection operation tracking with detailed metrics
- Success rate calculations and performance analytics
- Anomaly detection for identifying operational issues
- Trend analysis for capacity planning and optimization
- System health monitoring with configurable thresholds
- Data retention management for monitoring metrics
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.exceptions.service_exceptions import ServiceError
from app.models.collection_metrics import CollectionMetrics
from app.models.load_data import EnergyDataType

if TYPE_CHECKING:
    from app.config.database import Database
    from app.config.settings import MonitoringConfig
    from app.repositories.collection_metrics_repository import (
        CollectionMetricsRepository,
    )

# Set up logging
log = logging.getLogger(__name__)


class MonitoringError(ServiceError):
    """Exception for monitoring service operations."""

    def __init__(
        self,
        message: str,
        *,
        monitoring_operation: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize monitoring error with operation context.

        Args:
            message: Human-readable error description
            monitoring_operation: Specific monitoring operation that failed
            context: Additional context information for debugging
        """
        super().__init__(
            message,
            service_name="MonitoringService",
            operation=monitoring_operation or "unknown_monitoring_operation",
            context=context,
        )


class MonitoringService:
    """
    Service for monitoring data collection performance and operational health.

    This service provides comprehensive monitoring capabilities for tracking
    collection performance, calculating success rates, detecting anomalies,
    and maintaining system health across different energy areas and data types.

    The service integrates with the collection metrics repository to provide
    real-time insights into data pipeline operations and supports configurable
    thresholds for alerting and anomaly detection.

    Key capabilities:
    - Collection result tracking with detailed performance metrics
    - Success rate calculations across time periods and dimensions
    - Performance analytics for API response times and processing
    - Recent metrics retrieval for real-time monitoring dashboards
    - Anomaly detection based on historical patterns
    - Data retention management for operational efficiency
    - Trend analysis for capacity planning and optimization
    - System health assessment with configurable thresholds
    """

    def __init__(
        self,
        metrics_repository: CollectionMetricsRepository,
        database: Database,
        config: MonitoringConfig,
    ) -> None:
        """
        Initialize the monitoring service.

        Args:
            metrics_repository: Repository for collection metrics operations
            database: Database instance for transaction management
            config: Monitoring configuration settings
        """
        self._metrics_repository = metrics_repository
        self._database = database
        self._config = config

    async def track_collection_result(self, result: Any) -> None:
        """
        Record detailed collection metrics for a data collection operation.

        This method processes collection results and stores comprehensive metrics
        including timing information, success rates, and error context for
        monitoring and analysis purposes.

        Args:
            result: Collection result object with job_id, area_results, start_time, end_time

        Raises:
            MonitoringError: If metrics tracking fails
        """

        def _raise_invalid_format_error() -> None:
            """Raise invalid collection result format error."""
            error_msg = "Invalid collection result format"
            raise MonitoringError(
                error_msg,
                monitoring_operation="track_collection_result",
                context={"result_type": type(result).__name__},
            )

        try:
            if not hasattr(result, "job_id") or not hasattr(result, "area_results"):
                _raise_invalid_format_error()

            # Process each area result and create metrics records
            metrics_to_store = []

            for area_result in result.area_results:
                # Extract timing information
                collection_start = getattr(result, "start_time", datetime.now(UTC))
                collection_end = getattr(result, "end_time", datetime.now(UTC))

                # Calculate performance metrics
                api_response_time = getattr(area_result, "api_response_time_ms", None)
                processing_time = getattr(area_result, "processing_time_ms", None)

                # Create collection metrics record
                metrics = CollectionMetrics(
                    job_id=result.job_id,
                    area_code=getattr(area_result, "area_code", "unknown"),
                    data_type=getattr(area_result, "data_type", EnergyDataType.ACTUAL),
                    collection_start=collection_start,
                    collection_end=collection_end,
                    points_collected=getattr(area_result, "points_collected", 0),
                    success=getattr(area_result, "success", False),
                    error_message=getattr(area_result, "error_message", None),
                    api_response_time=api_response_time,
                    processing_time=processing_time,
                )

                metrics_to_store.append(metrics)

            # Store all metrics in a single transaction
            async with self._database.session_factory() as session:
                for metrics in metrics_to_store:
                    session.add(metrics)
                await session.commit()

            log.debug(
                "Tracked collection metrics for job %s: %d area results processed",
                result.job_id,
                len(metrics_to_store),
            )

        except MonitoringError:
            raise
        except Exception as e:
            error_msg = f"Failed to track collection result: {e}"
            raise MonitoringError(
                error_msg,
                monitoring_operation="track_collection_result",
                context={
                    "job_id": getattr(result, "job_id", "unknown"),
                    "error_type": type(e).__name__,
                },
            ) from e

    async def calculate_success_rates(self, period: timedelta) -> dict[str, float]:
        """
        Calculate success rates by area and data type for a given time period.

        Args:
            period: Time period to calculate success rates for

        Returns:
            Dictionary mapping area_code/data_type combinations to success rates

        Raises:
            MonitoringError: If success rate calculation fails
        """
        try:
            end_time = datetime.now(UTC)
            start_time = end_time - period

            # Get all metrics for the period
            metrics = await self._metrics_repository.get_by_time_range(
                start_time=start_time,
                end_time=end_time,
            )

            if not metrics:
                return {}

            # Group by area_code and data_type combinations
            success_rates = {}
            combinations = {}

            for metric in metrics:
                key = f"{metric.area_code}/{metric.data_type.value}"

                if key not in combinations:
                    combinations[key] = {"total": 0, "successful": 0}

                combinations[key]["total"] += 1
                if metric.success:
                    combinations[key]["successful"] += 1

            # Calculate success rates
            for key, counts in combinations.items():
                success_rates[key] = counts["successful"] / counts["total"]

            log.debug(
                "Calculated success rates for %d area/data type combinations over %s period",
                len(success_rates),
                period,
            )
        except Exception as e:
            error_msg = f"Failed to calculate success rates: {e}"
            raise MonitoringError(
                error_msg,
                monitoring_operation="calculate_success_rates",
                context={"period_seconds": period.total_seconds()},
            ) from e
        else:
            return success_rates

    async def get_performance_metrics(self, period: timedelta) -> dict[str, Any]:
        """
        Get aggregated performance metrics for API response times and processing.

        Args:
            period: Time period to analyze performance metrics for

        Returns:
            Dictionary with performance metrics including averages, min/max values

        Raises:
            MonitoringError: If performance metrics retrieval fails
        """
        try:
            end_time = datetime.now(UTC)
            start_time = end_time - period

            # Get performance metrics from repository
            performance_data = await self._metrics_repository.get_performance_metrics(
                start_time=start_time,
                end_time=end_time,
            )

            # Enhance with additional calculations
            recent_metrics = await self._metrics_repository.get_by_time_range(
                start_time=start_time,
                end_time=end_time,
            )

            total_operations = len(recent_metrics)
            successful_operations = sum(1 for m in recent_metrics if m.success)
            failed_operations = total_operations - successful_operations

            enhanced_metrics = {
                **performance_data,
                "total_operations": total_operations,
                "successful_operations": successful_operations,
                "failed_operations": failed_operations,
                "overall_success_rate": successful_operations / total_operations
                if total_operations > 0
                else 0.0,
                "period_start": start_time.isoformat(),
                "period_end": end_time.isoformat(),
                "period_duration_seconds": period.total_seconds(),
            }

            log.debug(
                "Retrieved performance metrics for %d operations over %s period",
                total_operations,
                period,
            )
        except Exception as e:
            error_msg = f"Failed to get performance metrics: {e}"
            raise MonitoringError(
                error_msg,
                monitoring_operation="get_performance_metrics",
                context={"period_seconds": period.total_seconds()},
            ) from e
        else:
            return enhanced_metrics

    async def get_recent_metrics(self, minutes: int) -> list[CollectionMetrics]:
        """
        Retrieve recent collection metrics for real-time monitoring.

        Args:
            minutes: Number of minutes back to retrieve metrics from

        Returns:
            List of recent collection metrics ordered by collection start time

        Raises:
            MonitoringError: If recent metrics retrieval fails
        """
        try:
            metrics = await self._metrics_repository.get_recent_metrics(minutes)

            log.debug(
                "Retrieved %d collection metrics from last %d minutes",
                len(metrics),
                minutes,
            )
        except Exception as e:
            error_msg = f"Failed to get recent metrics: {e}"
            raise MonitoringError(
                error_msg,
                monitoring_operation="get_recent_metrics",
                context={"minutes": minutes},
            ) from e
        else:
            return metrics

    async def detect_anomalies(
        self, area_code: str, data_type: EnergyDataType, period: timedelta
    ) -> dict[str, Any]:
        """
        Detect anomalies in collection patterns for a specific area and data type.

        Args:
            area_code: Geographic area code to analyze
            data_type: Type of energy data to analyze
            period: Time period for anomaly detection

        Returns:
            Dictionary with anomaly detection results and analysis

        Raises:
            MonitoringError: If anomaly detection fails
        """
        try:
            if not self._config.anomaly_detection_enabled:
                return {
                    "anomaly_detection_enabled": False,
                    "message": "Anomaly detection is disabled in configuration",
                }

            end_time = datetime.now(UTC)
            start_time = end_time - period

            # Get metrics for the specific area and data type
            metrics = await self._metrics_repository.get_by_time_range(
                start_time=start_time,
                end_time=end_time,
                area_codes=[area_code],
                data_types=[data_type],
            )

            if not metrics:
                return {
                    "anomaly_detection_enabled": True,
                    "area_code": area_code,
                    "data_type": data_type.value,
                    "period_analyzed": period.total_seconds(),
                    "anomalies_detected": [],
                    "message": "No data available for anomaly detection",
                }

            # Analyze patterns
            anomalies = []
            total_operations = len(metrics)
            successful_operations = sum(1 for m in metrics if m.success)
            success_rate = successful_operations / total_operations

            # Check success rate anomaly
            if success_rate < self._config.success_rate_threshold:
                anomalies.append(
                    {
                        "type": "low_success_rate",
                        "description": f"Success rate ({success_rate:.2%}) below threshold ({self._config.success_rate_threshold:.2%})",
                        "severity": "high" if success_rate < 0.8 else "medium",  # noqa: PLR2004
                        "value": success_rate,
                        "threshold": self._config.success_rate_threshold,
                    }
                )

            # Check performance anomalies
            response_times = [
                m.api_response_time for m in metrics if m.api_response_time is not None
            ]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                if avg_response_time > self._config.performance_threshold_ms:
                    anomalies.append(
                        {
                            "type": "high_response_time",
                            "description": f"Average response time ({avg_response_time:.1f}ms) exceeds threshold ({self._config.performance_threshold_ms}ms)",
                            "severity": "medium",
                            "value": avg_response_time,
                            "threshold": self._config.performance_threshold_ms,
                        }
                    )

            # Check for data collection gaps (no operations in expected intervals)
            if total_operations == 0:
                anomalies.append(
                    {
                        "type": "no_data_collection",
                        "description": f"No data collection operations found in the last {period}",
                        "severity": "high",
                        "value": 0,
                        "threshold": 1,
                    }
                )

            result = {
                "anomaly_detection_enabled": True,
                "area_code": area_code,
                "data_type": data_type.value,
                "period_analyzed": period.total_seconds(),
                "total_operations": total_operations,
                "success_rate": success_rate,
                "anomalies_detected": anomalies,
                "anomaly_count": len(anomalies),
                "analysis_timestamp": datetime.now(UTC).isoformat(),
            }

            log.debug(
                "Anomaly detection for %s/%s: %d anomalies detected from %d operations",
                area_code,
                data_type.value,
                len(anomalies),
                total_operations,
            )
        except Exception as e:
            error_msg = f"Failed to detect anomalies: {e}"
            raise MonitoringError(
                error_msg,
                monitoring_operation="detect_anomalies",
                context={
                    "area_code": area_code,
                    "data_type": data_type.value,
                    "period_seconds": period.total_seconds(),
                },
            ) from e
        else:
            return result

    async def cleanup_old_metrics(self) -> int:
        """
        Remove old metrics based on configured retention period.

        Returns:
            Number of deleted metrics records

        Raises:
            MonitoringError: If cleanup operation fails
        """
        try:
            deleted_count = await self._metrics_repository.cleanup_old_metrics(
                retention_days=self._config.metrics_retention_days
            )

            log.info(
                "Cleaned up %d old collection metrics (retention: %d days)",
                deleted_count,
                self._config.metrics_retention_days,
            )
        except Exception as e:
            error_msg = f"Failed to cleanup old metrics: {e}"
            raise MonitoringError(
                error_msg,
                monitoring_operation="cleanup_old_metrics",
                context={"retention_days": self._config.metrics_retention_days},
            ) from e
        else:
            return deleted_count

    def _process_daily_metrics(
        self, metrics: list[CollectionMetrics]
    ) -> dict[str, dict[str, Any]]:
        """Process metrics into daily statistics groupings."""
        daily_stats: dict[str, dict[str, Any]] = {}
        for metric in metrics:
            date_key = metric.collection_start.date().isoformat()

            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    "total_operations": 0,
                    "successful_operations": 0,
                    "total_points": 0,
                    "avg_response_time": 0,
                    "response_times": [],
                }

            daily_stats[date_key]["total_operations"] += 1
            if metric.success:
                daily_stats[date_key]["successful_operations"] += 1
            daily_stats[date_key]["total_points"] += metric.points_collected

            if metric.api_response_time is not None:
                daily_stats[date_key]["response_times"].append(metric.api_response_time)
        return daily_stats

    def _calculate_daily_averages(self, daily_stats: dict[str, dict[str, Any]]) -> None:
        """Calculate averages and success rates for daily statistics."""
        for stats in daily_stats.values():
            response_times = stats["response_times"]
            if response_times:
                stats["avg_response_time"] = sum(response_times) / len(response_times)
            total_ops = stats["total_operations"]
            successful_ops = stats["successful_operations"]
            stats["success_rate"] = successful_ops / total_ops if total_ops > 0 else 0
            # Remove raw response times to keep response clean
            del stats["response_times"]

    def _calculate_trend_direction(self, daily_stats: dict[str, dict[str, Any]]) -> str:
        """Calculate trend direction based on early vs recent period comparison."""
        sorted_dates = sorted(daily_stats.keys())
        min_dates_for_trend = 3
        if len(sorted_dates) < min_dates_for_trend:
            return "insufficient_data"

        recent_avg = (
            sum(
                daily_stats[date]["total_operations"]
                for date in sorted_dates[-min_dates_for_trend:]
            )
            / min_dates_for_trend
        )
        early_avg = (
            sum(
                daily_stats[date]["total_operations"]
                for date in sorted_dates[:min_dates_for_trend]
            )
            / min_dates_for_trend
        )

        if recent_avg > early_avg:
            return "increasing"
        if recent_avg < early_avg:
            return "decreasing"
        return "stable"

    async def get_collection_trends(self, days: int) -> dict[str, Any]:
        """
        Analyze collection trends over a specified number of days.

        Args:
            days: Number of days to analyze for trend patterns

        Returns:
            Dictionary with trend analysis including daily patterns and growth rates

        Raises:
            MonitoringError: If trend analysis fails
        """
        try:
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(days=days)

            # Get all metrics for the period
            metrics = await self._metrics_repository.get_by_time_range(
                start_time=start_time,
                end_time=end_time,
            )

            if not metrics:
                return {
                    "period_days": days,
                    "total_operations": 0,
                    "message": "No data available for trend analysis",
                }

            # Process metrics into daily statistics
            daily_stats = self._process_daily_metrics(metrics)
            self._calculate_daily_averages(daily_stats)

            # Calculate overall totals
            total_operations = sum(
                stats["total_operations"] for stats in daily_stats.values()
            )
            total_successful = sum(
                stats["successful_operations"] for stats in daily_stats.values()
            )
            total_points = sum(stats["total_points"] for stats in daily_stats.values())

            # Calculate trend direction
            trend_direction = self._calculate_trend_direction(daily_stats)

            result = {
                "period_days": days,
                "analysis_start": start_time.isoformat(),
                "analysis_end": end_time.isoformat(),
                "total_operations": total_operations,
                "total_successful_operations": total_successful,
                "total_points_collected": total_points,
                "overall_success_rate": total_successful / total_operations
                if total_operations > 0
                else 0,
                "daily_statistics": daily_stats,
                "trend_direction": trend_direction,
                "analysis_timestamp": datetime.now(UTC).isoformat(),
            }

            log.debug(
                "Analyzed collection trends over %d days: %d total operations, trend direction: %s",
                days,
                total_operations,
                trend_direction,
            )
        except Exception as e:
            error_msg = f"Failed to get collection trends: {e}"
            raise MonitoringError(
                error_msg,
                monitoring_operation="get_collection_trends",
                context={"days": days},
            ) from e
        else:
            return result

    async def get_system_health_summary(self) -> dict[str, Any]:
        """
        Get overall system health status based on recent metrics and thresholds.

        Returns:
            Dictionary with comprehensive system health assessment

        Raises:
            MonitoringError: If system health assessment fails
        """
        try:
            # Analyze recent performance (last hour)
            recent_period = timedelta(hours=1)
            performance_metrics = await self.get_performance_metrics(recent_period)

            # Get recent metrics for additional analysis
            recent_metrics = await self.get_recent_metrics(60)  # Last hour

            # Calculate health indicators
            health_indicators: dict[str, Any] = {
                "overall_status": "healthy",
                "status_reasons": [],
                "performance_status": "good",
                "availability_status": "good",
                "data_quality_status": "good",
            }

            # Check performance health
            if (
                performance_metrics.get("avg_api_response_time")
                and performance_metrics["avg_api_response_time"]
                > self._config.performance_threshold_ms
            ):
                health_indicators["performance_status"] = "degraded"
                health_indicators["status_reasons"].append(
                    f"High average response time: {performance_metrics['avg_api_response_time']:.1f}ms"
                )

            # Check availability health
            success_rate = performance_metrics.get("overall_success_rate", 0)
            if success_rate < self._config.success_rate_threshold:
                health_indicators["availability_status"] = "degraded"
                health_indicators["status_reasons"].append(
                    f"Low success rate: {success_rate:.2%}"
                )

            # Check data quality (recent operations)
            if len(recent_metrics) == 0:
                health_indicators["data_quality_status"] = "degraded"
                health_indicators["status_reasons"].append(
                    "No recent data collection operations"
                )

            # Determine overall status
            if any(
                status != "good"
                for status in [
                    health_indicators["performance_status"],
                    health_indicators["availability_status"],
                    health_indicators["data_quality_status"],
                ]
            ):
                health_indicators["overall_status"] = "degraded"

            # Add summary statistics
            result = {
                "health_assessment": health_indicators,
                "performance_metrics": performance_metrics,
                "recent_operations_count": len(recent_metrics),
                "assessment_timestamp": datetime.now(UTC).isoformat(),
                "configuration": {
                    "performance_threshold_ms": self._config.performance_threshold_ms,
                    "success_rate_threshold": self._config.success_rate_threshold,
                    "anomaly_detection_enabled": self._config.anomaly_detection_enabled,
                },
            }

            log.debug(
                "System health assessment: %s status with %d status reasons",
                health_indicators["overall_status"],
                len(health_indicators["status_reasons"]),
            )
        except Exception as e:
            error_msg = f"Failed to get system health summary: {e}"
            raise MonitoringError(
                error_msg,
                monitoring_operation="get_system_health_summary",
            ) from e
        else:
            return result

    def _analyze_failure_patterns_by_categories(
        self, failed_metrics: list[CollectionMetrics]
    ) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
        """Analyze failure patterns by area, data type, and error messages."""
        failure_by_area: dict[str, int] = {}
        failure_by_data_type: dict[str, int] = {}
        error_message_patterns: dict[str, int] = {}

        for failed_metric in failed_metrics:
            # Count failures by area
            area = failed_metric.area_code
            failure_by_area[area] = failure_by_area.get(area, 0) + 1

            # Count failures by data type
            data_type = failed_metric.data_type.value
            failure_by_data_type[data_type] = failure_by_data_type.get(data_type, 0) + 1

            # Analyze error messages
            if failed_metric.error_message:
                # Extract first word of error message as pattern
                error_pattern = (
                    failed_metric.error_message.split()[0]
                    if failed_metric.error_message.split()
                    else "unknown"
                )
                error_message_patterns[error_pattern] = (
                    error_message_patterns.get(error_pattern, 0) + 1
                )

        return failure_by_area, failure_by_data_type, error_message_patterns

    def _generate_failure_recommendations(
        self,
        top_failing_areas: list[tuple[str, int]],
        top_failing_data_types: list[tuple[str, int]],
        failed_operations: int,
    ) -> list[str]:
        """Generate recommendations based on failure patterns."""
        recommendations = []
        significant_failure_threshold = 0.5
        if top_failing_areas:
            most_failing_area = top_failing_areas[0]
            if (
                most_failing_area[1] / failed_operations
                >= significant_failure_threshold
            ):
                recommendations.append(
                    f"Focus on area '{most_failing_area[0]}' - responsible for {most_failing_area[1]}/{failed_operations} failures"
                )

        if top_failing_data_types:
            most_failing_type = top_failing_data_types[0]
            if (
                most_failing_type[1] / failed_operations
                >= significant_failure_threshold
            ):
                recommendations.append(
                    f"Investigate data type '{most_failing_type[0]}' - responsible for {most_failing_type[1]}/{failed_operations} failures"
                )

        return recommendations

    async def analyze_failure_patterns(self, period: timedelta) -> dict[str, Any]:
        """
        Analyze failure patterns to identify common issues and trends.

        Args:
            period: Time period to analyze failure patterns for

        Returns:
            Dictionary with failure pattern analysis and recommendations

        Raises:
            MonitoringError: If failure pattern analysis fails
        """
        try:
            end_time = datetime.now(UTC)
            start_time = end_time - period

            # Get all metrics for the period
            metrics = await self._metrics_repository.get_by_time_range(
                start_time=start_time,
                end_time=end_time,
            )

            if not metrics:
                return {
                    "period_analyzed": period.total_seconds(),
                    "total_operations": 0,
                    "message": "No data available for failure pattern analysis",
                }

            # Separate failed operations
            failed_metrics = [m for m in metrics if not m.success]
            total_operations = len(metrics)
            failed_operations = len(failed_metrics)

            if failed_operations == 0:
                return {
                    "period_analyzed": period.total_seconds(),
                    "total_operations": total_operations,
                    "failed_operations": 0,
                    "failure_rate": 0.0,
                    "message": "No failures detected in the analyzed period",
                }

            # Analyze failure patterns
            failure_by_area, failure_by_data_type, error_message_patterns = (
                self._analyze_failure_patterns_by_categories(failed_metrics)
            )

            # Sort patterns by frequency
            top_failing_areas = sorted(
                failure_by_area.items(), key=lambda x: x[1], reverse=True
            )
            top_failing_data_types = sorted(
                failure_by_data_type.items(), key=lambda x: x[1], reverse=True
            )
            top_error_patterns = sorted(
                error_message_patterns.items(), key=lambda x: x[1], reverse=True
            )

            # Generate recommendations
            recommendations = self._generate_failure_recommendations(
                top_failing_areas, top_failing_data_types, failed_operations
            )

            result = {
                "period_analyzed": period.total_seconds(),
                "analysis_start": start_time.isoformat(),
                "analysis_end": end_time.isoformat(),
                "total_operations": total_operations,
                "failed_operations": failed_operations,
                "failure_rate": failed_operations / total_operations,
                "failure_patterns": {
                    "by_area_code": dict(top_failing_areas),
                    "by_data_type": dict(top_failing_data_types),
                    "by_error_pattern": dict(top_error_patterns),
                },
                "top_failures": {
                    "areas": top_failing_areas[:5],  # Top 5
                    "data_types": top_failing_data_types[:5],
                    "error_patterns": top_error_patterns[:5],
                },
                "recommendations": recommendations,
                "analysis_timestamp": datetime.now(UTC).isoformat(),
            }

            log.debug(
                "Analyzed failure patterns: %d failures out of %d operations (%.2%% failure rate)",
                failed_operations,
                total_operations,
                (failed_operations / total_operations) * 100,
            )
        except Exception as e:
            error_msg = f"Failed to analyze failure patterns: {e}"
            raise MonitoringError(
                error_msg,
                monitoring_operation="analyze_failure_patterns",
                context={"period_seconds": period.total_seconds()},
            ) from e
        else:
            return result
