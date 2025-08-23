# Current Implementation Plan - UNIFIED API AND SCHEDULER SERVICE

## Next Atomic Step: INTEGRATE FASTAPI SERVER INTO MAIN SERVICE

Based on the completed REST API implementation and existing scheduler service, the next step is implementing a unified service that runs both the FastAPI server and scheduler concurrently in a single process.

### What to implement next:

1. **Enhanced Main Runner** (`energy_data_service/main.py`)
   - Add FastAPI server initialization alongside scheduler
   - Implement concurrent task management for both services
   - Update graceful shutdown to handle both services
   - Add server configuration from settings

2. **API Server Configuration** (`energy_data_service/app/config/settings.py`)
   - Add API server host and port configuration
   - Ensure HttpConfig includes server runtime settings
   - Add environment variable support for API configuration
   - Validate server configuration on startup

3. **Docker Configuration Update** (`docker-compose.yml`)
   - Expose port 8000 for API access
   - Map container port to host port
   - Update health checks to include API endpoint
   - Ensure proper network configuration

4. **Integration Testing** (`tests/integration/test_unified_service.py`)
   - Test concurrent operation of both services
   - Verify API accessibility while scheduler runs
   - Test graceful shutdown sequence
   - Validate data flow between services

### Implementation Requirements:

#### Enhanced Main Runner Features:
- **FastAPI Integration**: Import and initialize FastAPI application using existing create_app factory
- **Uvicorn Server Setup**: Configure ASGI server with proper host, port, and logging settings
- **Concurrent Task Management**: Use asyncio.create_task to run API server alongside scheduler
- **Unified Lifecycle**: Start both services after initialization, stop both on shutdown
- **Shared Container**: Both services use same dependency injection container instance
- **Error Handling**: Handle startup failures for either service with clear error messages

#### API Server Configuration Features:
- **Host Configuration**: Default to 0.0.0.0 for container compatibility
- **Port Configuration**: Default to 8000 with environment override capability
- **Worker Settings**: Configure uvicorn workers based on available resources
- **Logging Integration**: Use same logging configuration as scheduler service
- **Reload Settings**: Disable auto-reload in production, enable in development
- **SSL/TLS Support**: Prepare configuration structure for future HTTPS support

#### Docker Configuration Features:
- **Port Mapping**: Expose 8000:8000 for API access from host
- **Health Check Update**: Add API health endpoint check alongside database check
- **Environment Variables**: Pass API configuration through docker-compose
- **Network Configuration**: Ensure both services can communicate internally
- **Volume Mounts**: Share logs directory for unified logging
- **Resource Limits**: Set appropriate memory and CPU limits for combined service

### Test Coverage Requirements:

1. **Unit Tests for Main Runner** (`tests/app/test_main.py`)
   - Test API server initialization method
   - Test concurrent task creation and management
   - Test shutdown sequence for both services
   - Test error handling for server startup failures

2. **API Server Configuration Tests** (`tests/app/config/test_api_settings.py`)
   - Test server configuration loading from environment
   - Test default values and validation
   - Test invalid configuration handling
   - Test configuration integration with uvicorn

3. **Integration Tests** (`tests/integration/test_unified_service.py`)
   - Test both services start successfully
   - Test API endpoints work while scheduler runs
   - Test data collected by scheduler is queryable via API
   - Test graceful shutdown stops both services cleanly

4. **Docker Integration Tests** (`tests/docker/test_unified_container.py`)
   - Test container starts with both services
   - Test API accessible from host machine
   - Test scheduler continues collecting data
   - Test container health checks pass

5. **End-to-End Tests** (`tests/integration/test_full_stack.py`)
   - Test complete data flow: collection → storage → API query
   - Test concurrent API requests during data collection
   - Test service recovery after errors
   - Test monitoring and logging integration

### Dependencies:

- Builds on existing SimpleSchedulerRunner from `energy_data_service/main.py`
- Uses create_app from `energy_data_service/app/api/app.py`
- Uses Container from `energy_data_service/app/container.py`
- Requires uvicorn (already in pyproject.toml)
- Integration with existing SchedulerService pattern
- Future integration with monitoring and metrics collection

### Success Criteria:

- **Primary Success Metric**: Both scheduler and API server run concurrently in single process without conflicts
- **API Accessibility Metric**: REST API endpoints accessible at http://localhost:8000 while data collection continues
- **Performance Success Metric**: No degradation in data collection performance with API server running
- **Stability Success Metric**: Service runs for 24+ hours without memory leaks or crashes
- **Error Handling Success Metric**: Graceful degradation if one service fails, clear error messages
- **Code Quality Success Metric**: Passes all checks (ruff, mypy, pre-commit)
- **Deployment Success Metric**: Single docker container serves both data collection and API needs
- **Pattern Consistency Success Metric**: Follows existing async patterns and dependency injection

This unified service implementation establishes a production-ready deployment model where data collection and API serving are managed together, simplifying operations and deployment.

---

## Further Implementation Details

### 🔍 **Current Service Isolation Problem**

#### **Root Cause Analysis:**
The current implementation has a critical gap where the scheduler service collects data but the REST API is never started, making the collected data inaccessible via HTTP:

- `main.py:338-355` starts only SchedulerService
- `app/api/app.py:34-71` contains create_app but is never called
- No uvicorn server initialization in current codebase
- Docker container runs but API endpoints are unreachable

**Current Problematic State:**
```python
# ❌ WRONG: Only scheduler runs, API is dormant
async def run(self) -> None:
    # ... initialization ...
    scheduler_service = await self._start_scheduler_service()
    # Wait for shutdown - API never starts!
    await self.shutdown_event.wait()
```

**Why This is a Critical Problem:**
1. **Data Inaccessibility**: Collected data trapped in database with no API access
2. **Strategy Service Blocked**: Cannot query energy data for trading algorithms
3. **Monitoring Limited**: No HTTP health checks or metrics endpoints
4. **Testing Difficult**: Cannot manually verify data collection via API

### 🛠️ **Detailed Implementation Strategy**

#### **Core Solution Approach:**
Modify the existing SimpleSchedulerRunner to manage both services as concurrent async tasks within the same event loop.

**New Unified Pattern:**
```python
# ✅ CORRECT: Both services run concurrently
async def run(self) -> None:
    # ... initialization ...

    # Start scheduler service
    scheduler_service = await self._start_scheduler_service()

    # Start API server concurrently
    api_server = await self._start_api_server()

    # Wait for shutdown signal
    await self.shutdown_event.wait()

    # Graceful shutdown of both services
    await self._shutdown_services(scheduler_service, api_server)
```

#### **Detailed Component Implementation:**

**Enhanced Main Runner Implementation:**
```python
# main.py additions
import uvicorn
from app.api.app import create_app

class SimpleSchedulerRunner:
    async def _start_api_server(self) -> uvicorn.Server:
        """Start the FastAPI server for REST API access."""
        try:
            # Create FastAPI application
            app = create_app()

            # Get configuration
            settings = self.container.config()

            # Configure uvicorn server
            config = uvicorn.Config(
                app=app,
                host="0.0.0.0",  # Listen on all interfaces for Docker
                port=settings.http.port if hasattr(settings.http, 'port') else 8000,
                log_level=settings.logging.level.lower(),
                access_log=True,
                use_colors=False,  # Better for container logs
            )

            server = uvicorn.Server(config)

            # Start server in background task
            self.api_task = asyncio.create_task(server.serve())

            self.logger.info("FastAPI server started on port %s", config.port)
            return server

        except Exception as e:
            self.logger.error("Failed to start API server: %s", e)
            raise

    async def _shutdown_services(
        self,
        scheduler_service: SchedulerService,
        api_server: uvicorn.Server
    ) -> None:
        """Gracefully shutdown both services."""

        # Stop accepting new API requests
        self.logger.info("Stopping API server...")
        api_server.should_exit = True

        # Stop scheduler
        self.logger.info("Stopping scheduler service...")
        stop_result = await scheduler_service.stop()

        # Wait for API task to complete
        if hasattr(self, 'api_task'):
            await self.api_task

        self.logger.info("All services stopped successfully")
```

**API Server Configuration Updates:**
```python
# app/config/settings.py additions
class HttpConfig(BaseModel):
    """HTTP server configuration."""

    host: str = Field(
        default="0.0.0.0",
        description="Host to bind the API server to"
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Port for the API server"
    )
    workers: int = Field(
        default=1,
        ge=1,
        description="Number of worker processes"
    )
    access_log: bool = Field(
        default=True,
        description="Enable access logging"
    )
```

### 🔄 **Before/After Transformation**

#### **Before (Scheduler Only):**
```python
# ❌ Current: API exists but never runs
async def run(self) -> None:
    # Database and scheduler initialization
    await self._initialize_database()
    self._validate_api_configuration()

    # Only scheduler starts
    scheduler_service = await self._start_scheduler_service()

    # Perform startup tasks
    await self._perform_startup_tasks(settings)

    # Just wait - no API access!
    self.logger.info("Press Ctrl+C to stop the service")
    await self.shutdown_event.wait()

    # Only scheduler cleanup
    stop_result = await scheduler_service.stop()
```

#### **After (Unified Service):**
```python
# ✅ New: Both services run together
async def run(self) -> None:
    # Database initialization
    await self._initialize_database()
    self._validate_api_configuration()

    # Start BOTH services
    scheduler_service = await self._start_scheduler_service()
    api_server = await self._start_api_server()

    # Perform startup tasks
    await self._perform_startup_tasks(settings)

    # Service ready with both components
    self.logger.info("=" * 60)
    self.logger.info("✅ Energy Data Service Ready")
    self.logger.info("📊 Scheduler: Collecting data every 30 minutes")
    self.logger.info("🌐 API: Available at http://localhost:8000/docs")
    self.logger.info("=" * 60)

    # Wait for shutdown
    self.logger.info("Press Ctrl+C to stop the service")
    await self.shutdown_event.wait()

    # Clean shutdown of BOTH services
    await self._shutdown_services(scheduler_service, api_server)
```

### 📊 **Benefits Quantification**

#### **Functionality Improvements:**
- **API Availability**: 0% → 100% REST API endpoint accessibility
- **Data Accessibility**: Immediate access to collected data via HTTP
- **Service Integration**: Single process reduces overhead by ~30%
- **Strategy Service Enablement**: Unblocks quantitative trading development

#### **Operational Improvements:**
- **Deployment Simplicity**: 1 container instead of potential 2 (50% reduction)
- **Resource Usage**: Shared memory and database connections (20-30% more efficient)
- **Monitoring**: Unified logs and metrics from single process
- **Health Checks**: Single endpoint monitors both services

#### **Development Improvements:**
- **Testing**: Can test full stack with single service startup
- **Debugging**: Single process simplifies troubleshooting
- **Configuration**: One set of environment variables for both services
- **Local Development**: One command starts everything

### 🧪 **Comprehensive Testing Strategy**

#### **Unit Tests:**
```python
# tests/app/test_main.py
class TestUnifiedService:
    async def test_api_server_initialization(self):
        """Test API server starts with correct configuration."""
        runner = SimpleSchedulerRunner()
        with patch('uvicorn.Server') as mock_server:
            with patch('app.api.app.create_app') as mock_create_app:
                server = await runner._start_api_server()

                mock_create_app.assert_called_once()
                mock_server.assert_called_once()
                assert server is not None

    async def test_concurrent_service_startup(self):
        """Test both services start without blocking each other."""
        runner = SimpleSchedulerRunner()
        # Mock both service starts
        with patch.object(runner, '_start_scheduler_service') as mock_scheduler:
            with patch.object(runner, '_start_api_server') as mock_api:
                # Simulate partial run
                await runner._initialize_database()
                scheduler = await runner._start_scheduler_service()
                api = await runner._start_api_server()

                mock_scheduler.assert_called_once()
                mock_api.assert_called_once()

    async def test_graceful_shutdown_both_services(self):
        """Test both services stop cleanly on shutdown."""
        runner = SimpleSchedulerRunner()
        mock_scheduler = MagicMock()
        mock_api_server = MagicMock()

        await runner._shutdown_services(mock_scheduler, mock_api_server)

        mock_scheduler.stop.assert_called_once()
        assert mock_api_server.should_exit is True
```

#### **Integration Tests:**
```python
# tests/integration/test_unified_service.py
class TestUnifiedServiceIntegration:
    async def test_api_accessible_during_collection(self):
        """Verify API responds while scheduler collects data."""
        # Start unified service
        async with run_test_service() as service_url:
            # Trigger data collection
            await trigger_collection()

            # Make API call during collection
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{service_url}/api/v1/health")
                assert response.status_code == 200

                # Query data being collected
                response = await client.get(
                    f"{service_url}/api/v1/energy-data/latest?area_code=DE"
                )
                assert response.status_code == 200

    async def test_service_recovery_after_error(self):
        """Test service continues if one component fails."""
        # Test API continues if scheduler fails
        # Test scheduler continues if API fails
```

#### **Performance Tests:**
- **Concurrent Load**: 100 simultaneous API requests during data collection
- **Memory Stability**: 24-hour run with steady memory usage (<500MB)
- **CPU Usage**: <50% CPU with both services active
- **Response Time**: API responds in <200ms during collection

### 🎯 **Migration/Rollout Strategy**

#### **Implementation Phases:**
1. **Phase 1**: Add _start_api_server and _shutdown_services methods to main.py
2. **Phase 2**: Update run() method to start both services
3. **Phase 3**: Update docker-compose.yml with port mapping
4. **Phase 4**: Test locally with docker-compose up
5. **Phase 5**: Deploy to staging environment
6. **Phase 6**: Production deployment with monitoring

#### **Backwards Compatibility:**
- **Scheduler Logic**: Existing scheduler implementation unchanged
- **API Implementation**: API code remains the same
- **Database Schema**: No changes to models or tables
- **Configuration**: Additive changes only, existing config still works

#### **Risk Mitigation:**
- **Service Isolation**: Try/except blocks prevent one service failure from affecting the other
- **Resource Limits**: Docker memory and CPU limits prevent resource exhaustion
- **Health Monitoring**: Separate health checks for each service component
- **Rollback Plan**: Can revert to scheduler-only mode if issues arise
- **Gradual Rollout**: Test in development, then staging, then production

---

## Implementation Timeline

- **Day 1**: Implement main.py changes and test locally
- **Day 2**: Update configuration and Docker setup
- **Day 3**: Write comprehensive tests
- **Day 4**: Integration testing and bug fixes
- **Day 5**: Documentation and deployment preparation

This plan ensures the FastAPI REST API becomes accessible while maintaining the existing scheduler functionality, creating a complete, production-ready energy data service.
