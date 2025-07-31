# Current Implementation Plan - Scheduler Service & Monitoring Layer

## Next Atomic Step: Automated Data Collection with Monitoring

Based on the completed Service Orchestration Layer, the next step is implementing automated data collection scheduler with comprehensive monitoring and data quality validation to start building historical datasets immediately while ensuring production reliability.

### What to implement next:

1. **SchedulerService** (`app/services/scheduler_service.py`)
   - APScheduler-based job scheduling with database persistence
   - Multi-area data collection coordination across DE, FR, NL
   - Automated gap detection and filling workflows
   - Job health monitoring and failure recovery

2. **MonitoringService** (`app/services/monitoring_service.py`)
   - Collection success/failure tracking with metrics storage
   - API health monitoring and performance analysis
   - System resource monitoring and alerting
   - Daily/weekly reporting and dashboard updates

3. **AlertService** (`app/services/alert_service.py`)
   - Email and webhook notification system
   - Threshold-based alerting with deduplication
   - Recovery notifications and status updates
   - Alert history tracking and analysis

4. **DataQualityService** (`app/services/data_quality_service.py`)
   - Data completeness validation and gap detection
   - Value range validation and anomaly detection
   - Quality scoring and trend analysis
   - Automated remediation scheduling

### Implementation Requirements:

#### SchedulerService Features:
- **Job Scheduling**: APScheduler integration with AsyncIOScheduler and database job store for persistence
- **Collection Orchestration**: Coordinated data collection across multiple areas with configurable intervals
- **Error Handling**: Exponential backoff retry logic with maximum retry limits and failure tracking
- **Gap Management**: Automated gap detection every 4 hours with immediate remediation for small gaps
- **Backfill Coordination**: Daily analysis and scheduling of historical data backfill operations
- **Health Monitoring**: Hourly ENTSO-E API health checks with response time and availability tracking

#### MonitoringService Features:
- **Metrics Collection**: Comprehensive tracking of collection success rates, API response times, and data volumes
- **Performance Analysis**: Database query performance monitoring and system resource usage tracking
- **Anomaly Detection**: Statistical analysis for identifying unusual patterns in collection data
- **Dashboard Integration**: Real-time updates to monitoring dashboards with live collection status
- **Reporting**: Automated daily and weekly reports with trends analysis and recommendations
- **Database Integration**: Persistent storage of all metrics in dedicated collection_metrics table

#### AlertService Features:
- **Multi-Channel Alerts**: Email and webhook notifications with configurable recipient lists
- **Threshold Management**: Configurable alert conditions for failures, performance degradation, and resource issues
- **Deduplication**: Smart alert grouping to prevent notification spam during cascading failures
- **Recovery Tracking**: Automatic recovery notifications when issues are resolved
- **Alert History**: Complete audit trail of all alerts with resolution status and response times
- **Rate Limiting**: Configurable rate limits to prevent alert flooding during system issues

#### DataQualityService Features:
- **Completeness Validation**: 15-minute resolution continuity checks with gap identification
- **Value Validation**: Range checking and outlier detection based on historical patterns
- **Quality Scoring**: Comprehensive quality metrics including completeness, timeliness, and accuracy scores
- **Trend Analysis**: Long-term quality trend monitoring with degradation detection
- **Automated Remediation**: Integration with RemediationService for automatic issue resolution
- **Quality Reporting**: Daily quality reports with per-area and per-data-type analysis

### Test Coverage Requirements:

1. **SchedulerService Tests** (`tests/app/services/test_scheduler_service.py`)
   - Job scheduling and execution with APScheduler integration testing
   - Collection coordination across multiple areas with success/failure scenarios
   - Retry logic testing with exponential backoff validation
   - Gap detection and automatic remediation workflow testing

2. **MonitoringService Tests** (`tests/app/services/test_monitoring_service.py`)
   - Metrics collection and storage with database integration testing
   - Performance monitoring and threshold detection testing
   - Dashboard update and reporting functionality testing
   - Anomaly detection algorithm validation with known patterns

3. **AlertService Tests** (`tests/app/services/test_alert_service.py`)
   - Email and webhook notification delivery testing
   - Alert deduplication and rate limiting functionality
   - Threshold-based alert triggering with various failure scenarios
   - Recovery notification and alert resolution testing

4. **DataQualityService Tests** (`tests/app/services/test_data_quality_service.py`)
   - Completeness validation with known gap patterns
   - Value validation and anomaly detection with synthetic data
   - Quality scoring calculation with various data scenarios
   - Automated remediation scheduling and execution testing

5. **Scheduler Integration Tests** (`tests/integration/test_scheduler_integration.py`)
   - End-to-end scheduled collection with real database and API calls
   - Multi-service coordination testing with monitoring and alerting
   - Long-running scheduler stability testing with job persistence
   - Recovery testing after scheduler restart with job state restoration

### Dependencies:

- Builds on existing EntsoEDataService from `app/services/entsoe_data_service.py`
- Uses BackfillService from `app/services/backfill_service.py`
- Uses EnergyDataRepository from `app/repositories/energy_data_repository.py`
- Uses BackfillProgressRepository from `app/repositories/backfill_progress_repository.py`
- Requires APScheduler (needs to be added to pyproject.toml)
- Requires email utilities (smtplib/aiosmtplib for notifications)
- Integration with existing Container from `app/container.py`
- Future integration point for Strategy Service data consumption

### Success Criteria:

- **Automated Collection**: Successful scheduled data collection running 24/7 with 95%+ success rate
- **Comprehensive Monitoring**: Real-time visibility into collection status, performance, and data quality
- **Reliable Alerting**: Immediate notifications for failures with <5 minute detection time
- **Data Quality Assurance**: Automated detection and remediation of data gaps and quality issues
- **Production Stability**: Scheduler runs continuously with graceful error handling and recovery
- **Code Quality**: Passes all checks (ruff, mypy, pre-commit) with comprehensive test coverage
- **Historical Data Growth**: Continuous accumulation of high-quality historical data for trading analysis
- **Operational Readiness**: Complete monitoring and alerting infrastructure for production deployment

This automated scheduler establishes the foundation for continuous data collection needed for trading system development while ensuring data reliability and quality through comprehensive monitoring.

---

## Further Implementation Details

### 🔍 **Data Collection Gap Analysis**

#### **Current Limitation:**
The completed service orchestration layer provides excellent data collection capabilities, but without automation, data accumulation is manual and inconsistent. Trading strategies require months/years of historical data with high reliability.

**Current Manual Process:**
```python
# ❌ MANUAL: Requires manual execution for data collection
service = container.entsoe_data_service()
await service.collect_and_fill_gaps(["DE"], [EnergyDataType.ACTUAL])
# No automation, no monitoring, no alerting
```

**Why This is a Critical Gap:**
1. **Trading Requirements**: Strategies need continuous, reliable historical data
2. **Data Quality**: Manual collection leads to gaps and inconsistencies
3. **Operational Overhead**: Manual monitoring is unsustainable for 24/7 operations
4. **Time to Market**: Delays in data accumulation delay strategy development

### 🛠️ **Detailed Implementation Strategy**

#### **Core Solution Approach:**
Implement comprehensive automated data collection with industrial-grade monitoring, using APScheduler for reliable job execution and sophisticated alerting for operational excellence.

**New Automated Collection Pattern:**
```python
# ✅ CORRECT: Fully automated data collection with monitoring
@scheduler.scheduled_job('cron', minute='*/30', id='collect_real_time')
async def collect_real_time_data():
    try:
        result = await entsoe_data_service.collect_and_fill_gaps(
            areas=["DE", "FR", "NL"],
            data_types=[EnergyDataType.ACTUAL, EnergyDataType.DAY_AHEAD]
        )
        await monitoring_service.track_collection_result(result)

        if result.has_failures():
            await alert_service.send_collection_failure_alert(result.failures)

    except Exception as e:
        await alert_service.send_system_error_alert(e)
        raise
```

#### **Detailed Component Implementation:**

**SchedulerService Implementation:**
```python
# app/services/scheduler_service.py
class SchedulerService:
    def __init__(
        self,
        entsoe_data_service: EntsoEDataService,
        backfill_service: BackfillService,
        monitoring_service: MonitoringService,
        alert_service: AlertService,
        settings: Settings
    ):
        self.entsoe_service = entsoe_data_service
        self.backfill_service = backfill_service
        self.monitoring = monitoring_service
        self.alerts = alert_service
        self.settings = settings
        self.scheduler = AsyncIOScheduler(
            jobstores={'default': SqlAlchemyJobStore(url=settings.database.url)},
            executors={'default': AsyncIOExecutor()},
            job_defaults={'coalesce': False, 'max_instances': 1}
        )

    async def initialize_scheduler(self) -> None:
        """Setup scheduler with all collection jobs"""
        self.scheduler.start()

        # Real-time data collection every 30 minutes
        self.scheduler.add_job(
            self.collect_real_time_data,
            'cron', minute='*/30',
            id='collect_real_time',
            replace_existing=True
        )

        # Forecast data collection every 6 hours
        self.scheduler.add_job(
            self.collect_forecast_data,
            'cron', hour='*/6',
            id='collect_forecasts',
            replace_existing=True
        )

        # Gap analysis every 4 hours
        self.scheduler.add_job(
            self.analyze_and_fill_gaps,
            'cron', hour='*/4',
            id='gap_analysis',
            replace_existing=True
        )

        # Daily backfill analysis at 2 AM
        self.scheduler.add_job(
            self.run_backfill_analysis,
            'cron', hour=2,
            id='backfill_analysis',
            replace_existing=True
        )
```

**MonitoringService Implementation:**
```python
# app/services/monitoring_service.py
class MonitoringService:
    def __init__(
        self,
        metrics_repository: CollectionMetricsRepository,
        alert_service: AlertService,
        settings: Settings
    ):
        self.metrics_repo = metrics_repository
        self.alerts = alert_service
        self.settings = settings

    async def track_collection_result(self, result: CollectionResult) -> None:
        """Record detailed collection metrics"""
        for area_result in result.area_results:
            metric = CollectionMetrics(
                job_id=result.job_id,
                area_code=area_result.area_code,
                data_type=area_result.data_type,
                collection_start=result.start_time,
                collection_end=result.end_time,
                points_collected=area_result.points_collected,
                success=area_result.success,
                error_message=area_result.error_message,
                api_response_time=area_result.api_response_time,
                processing_time=area_result.processing_time
            )
            await self.metrics_repo.create(metric)

        # Check alert conditions
        await self._evaluate_alert_conditions(result)

    async def calculate_success_rates(self, period: timedelta) -> Dict[str, float]:
        """Calculate success rates by area and data type"""
        end_time = datetime.utcnow()
        start_time = end_time - period

        metrics = await self.metrics_repo.get_by_time_range(start_time, end_time)

        success_rates = {}
        for area in ["DE", "FR", "NL"]:
            area_metrics = [m for m in metrics if m.area_code == area]
            if area_metrics:
                success_count = sum(1 for m in area_metrics if m.success)
                success_rates[area] = success_count / len(area_metrics)

        return success_rates
```

### 🔄 **Before/After Transformation**

#### **Before (Manual Data Collection):**
```python
# ❌ Current: Manual, unreliable data collection
import asyncio
from app.container import Container

async def manual_collection():
    container = Container()
    service = container.entsoe_data_service()

    # Manual execution - no automation
    result = await service.collect_and_fill_gaps(["DE"], [EnergyDataType.ACTUAL])
    print(f"Collected {result.total_points} points")  # Basic logging

    # No monitoring, no alerts, no quality checks
    # No systematic gap detection or remediation
    # Requires manual execution every time

# Must remember to run this manually
asyncio.run(manual_collection())
```

#### **After (Automated Production System):**
```python
# ✅ New: Fully automated, monitored, production-ready system
class EnergyDataApplication:
    async def run_application(self) -> None:
        """Production application with full automation"""
        container = Container()

        # Initialize all services
        scheduler = container.scheduler_service()
        monitoring = container.monitoring_service()
        alerts = container.alert_service()

        # Start automated collection
        await scheduler.initialize_scheduler()
        await monitoring.start_background_monitoring()
        await alerts.initialize_notification_channels()

        # Application runs continuously with:
        # - Automated data collection every 30 minutes
        # - Continuous monitoring and alerting
        # - Automatic gap detection and remediation
        # - Quality validation and reporting
        # - Health checks and system monitoring

        await self._run_until_shutdown()
```

### 📊 **Benefits Quantification**

#### **Operational Improvements:**
- **Data Collection Reliability**: 95%+ uptime with automated retry logic and error recovery
- **Monitoring Coverage**: 100% visibility into collection status, performance, and data quality
- **Alert Response Time**: <5 minutes from failure detection to notification delivery

#### **Development Velocity Improvements:**
- **Historical Data Accumulation**: Continuous 24/7 data collection building months of trading data
- **Quality Assurance**: Automated data validation prevents quality issues from impacting strategies
- **Operational Efficiency**: Zero manual intervention required for routine data collection

#### **Trading System Preparation:**
- **Data Readiness**: Months of high-quality historical data available when Strategy Service is developed
- **Production Stability**: Industrial-grade monitoring and alerting infrastructure for trading operations
- **Scalability Foundation**: Automated system ready for additional data sources and increased collection frequency

### 🧪 **Comprehensive Testing Strategy**

#### **Unit Tests Details:**
```python
# tests/app/services/test_scheduler_service.py
class TestSchedulerService:
    async def test_collect_real_time_data_success(self, mock_services):
        scheduler = SchedulerService(
            entsoe_data_service=mock_services.entsoe,
            monitoring_service=mock_services.monitoring,
            alert_service=mock_services.alerts,
            settings=mock_services.settings
        )

        # Mock successful collection
        mock_services.entsoe.collect_and_fill_gaps.return_value = CollectionResult(
            job_id="test-job",
            total_points=1000,
            success=True
        )

        # Execute collection job
        await scheduler.collect_real_time_data()

        # Verify service calls
        mock_services.entsoe.collect_and_fill_gaps.assert_called_once()
        mock_services.monitoring.track_collection_result.assert_called_once()

    async def test_collection_failure_triggers_alert(self, mock_services):
        scheduler = SchedulerService(
            entsoe_data_service=mock_services.entsoe,
            monitoring_service=mock_services.monitoring,
            alert_service=mock_services.alerts,
            settings=mock_services.settings
        )

        # Mock collection failure
        mock_services.entsoe.collect_and_fill_gaps.side_effect = CollectionError("API unavailable")

        # Execute collection job
        with pytest.raises(CollectionError):
            await scheduler.collect_real_time_data()

        # Verify alert was sent
        mock_services.alerts.send_system_error_alert.assert_called_once()
```

#### **Integration Tests Details:**
```python
# tests/integration/test_scheduler_integration.py
class TestSchedulerIntegration:
    async def test_end_to_end_scheduled_collection(self, postgres_container, real_container):
        """Test complete scheduled collection with real database"""
        scheduler = real_container.scheduler_service()
        monitoring = real_container.monitoring_service()

        # Initialize scheduler
        await scheduler.initialize_scheduler()

        # Wait for one collection cycle (in test, use shorter intervals)
        await asyncio.sleep(5)  # Test with 5-second intervals

        # Verify data was collected
        metrics = await monitoring.get_recent_metrics(minutes=10)
        assert len(metrics) > 0
        assert any(m.success for m in metrics)

        # Verify monitoring data
        success_rates = await monitoring.calculate_success_rates(timedelta(minutes=10))
        assert all(rate > 0 for rate in success_rates.values())

    async def test_scheduler_persistence_after_restart(self, postgres_container, real_container):
        """Test scheduler job persistence across restarts"""
        scheduler1 = real_container.scheduler_service()
        await scheduler1.initialize_scheduler()

        # Verify jobs are scheduled
        jobs = scheduler1.scheduler.get_jobs()
        assert len(jobs) >= 4  # real-time, forecasts, gaps, backfill

        # Simulate restart
        scheduler1.scheduler.shutdown()

        # Create new scheduler instance
        scheduler2 = real_container.scheduler_service()
        await scheduler2.initialize_scheduler()

        # Verify jobs were restored from database
        restored_jobs = scheduler2.scheduler.get_jobs()
        assert len(restored_jobs) >= 4
```

#### **Performance/Load Tests:**
- **Concurrent Collection**: Test scheduler handling multiple simultaneous collection jobs without resource exhaustion
- **Long-Running Stability**: 24-hour continuous operation test with memory and resource monitoring
- **Database Performance**: Test metrics storage performance under high-frequency collection scenarios

### 🎯 **Migration/Rollout Strategy**

#### **Implementation Phases:**
1. **Phase 1**: Implement basic SchedulerService with simple collection jobs and basic monitoring
2. **Phase 2**: Add comprehensive MonitoringService with metrics storage and AlertService integration
3. **Phase 3**: Implement DataQualityService with automated remediation and advanced reporting

#### **Backwards Compatibility:**
- **Service Layer Unchanged**: Existing services continue to work unchanged, scheduler adds automation layer
- **Manual Override**: Manual collection remains available for testing and emergency operations
- **Configuration Driven**: All scheduling parameters configurable via environment variables

#### **Risk Mitigation:**
- **Gradual Rollout**: Start with longer collection intervals, gradually increase frequency as stability proven
- **Monitoring First**: Implement comprehensive monitoring before increasing automation complexity
- **Fallback Plan**: Manual collection procedures documented and tested for emergency situations
- **Resource Management**: CPU and memory monitoring to prevent resource exhaustion during collection
