# Implementation Plan Template

## Guidelines for Using This Template

This template provides a structured approach for creating comprehensive implementation plans. Replace all `[PLACEHOLDER]` sections with specific details for your implementation step.

---

# Current Implementation Plan - MINIMAL DOCKER DEPLOYMENT

## Next Atomic Step: CONTAINERIZE SCHEDULER SERVICE

Based on the existing Clean Architecture, the next step is implementing minimal Docker containerization to run the SchedulerService and begin collecting energy data from ENTSO-E APIs.

### What to implement next:

1. **Main Entry Point** (`energy_data_service/main.py`)
   - Simple scheduler service initialization
   - Database connection setup
   - Graceful shutdown handling
   - Basic error logging

2. **Docker Container** (`energy_data_service/Dockerfile`)
   - UV package manager integration
   - Workspace dependency resolution (entsoe_client)
   - Multi-stage build for efficiency
   - Non-root user security

3. **Environment Configuration** (`.env`)
   - Database connection parameters
   - ENTSO-E API token configuration
   - Basic application settings
   - Development environment defaults

4. **Service Orchestration** (`docker-compose.yml` update)
   - Energy data service container definition
   - TimescaleDB dependency management
   - Network configuration
   - Volume mounting for logs

### Implementation Requirements:

#### Main Entry Point Features:
- **Service Initialization**: Initialize dependency injection container and resolve SchedulerService
- **Database Connection**: Establish async database connection using existing Database class
- **Scheduler Startup**: Start SchedulerService with configured job scheduling
- **Signal Handling**: Graceful shutdown on SIGINT/SIGTERM signals
- **Error Handling**: Basic exception catching and logging for startup failures
- **Logging Setup**: Configure structured logging for container environment

#### Docker Container Features:
- UV package manager for dependency resolution
- Workspace-aware build (includes entsoe_client)
- Multi-stage build (builder + runtime)
- Security hardening with non-root user
- Health check for container orchestration
- Environment variable configuration

#### Environment Configuration Features:
- **Database Settings**: Host, port, credentials, database name
- **API Configuration**: ENTSO-E API token and client settings
- **Application Settings**: Environment type, debug mode, logging level
- **Scheduler Settings**: Enable/disable scheduling, collection intervals
- **Service Settings**: Basic service configuration parameters
- **Security Settings**: Non-sensitive defaults with secure overrides

### Test Coverage Requirements:

1. **Container Build Tests** (`tests/docker/test_build.py`)
   - Dockerfile builds successfully
   - UV workspace dependencies resolve correctly
   - entsoe_client package is available in container
   - Non-root user configuration works

2. **Integration Tests** (`tests/integration/test_scheduler_docker.py`)
   - Scheduler service starts in container
   - Database connection established
   - Basic job scheduling works
   - Graceful shutdown functions

3. **Environment Tests** (`tests/integration/test_environment.py`)
   - Environment variables loaded correctly
   - Database configuration valid
   - API token configuration secure
   - Service configuration complete

4. **Docker Compose Tests** (`tests/docker/test_compose.py`)
   - Services start in correct order
   - Network connectivity between services
   - Volume mounts work correctly
   - Health checks pass

### Dependencies:

- Builds on existing SchedulerService from `app/services/scheduler_service.py`
- Uses Database class from `app/config/database.py`
- Uses Container from `app/container.py`
- Requires TimescaleDB (already running via docker-compose)
- Integration with entsoe_client workspace package
- Future integration with monitoring when needed

### Success Criteria:

- **Container Build Success**: Dockerfile builds without errors using UV and workspace dependencies
- **Service Startup Success**: SchedulerService starts and begins job execution in container environment
- **Database Integration Success**: Container connects to TimescaleDB and performs database operations
- **Data Collection Success**: ENTSO-E API calls execute and energy data is stored in database
- **Error Handling Success**: Graceful handling of startup failures and shutdown signals
- **Code Quality Success**: Passes all checks (ruff, mypy, pre-commit)
- **Deployment Success**: Docker compose brings up complete stack with functional data collection
- **Minimal Complexity Success**: Implementation focuses only on core scheduling without monitoring overhead

This minimal containerization establishes the foundation needed for automated energy data collection in a production-ready Docker environment.

---

## Further Implementation Details

### 🔍 **Current Deployment Gap Analysis**

#### **Root Cause/Current Issues:**
The energy data service is fully implemented with Clean Architecture but lacks containerization and deployment infrastructure:

- No main entry point to orchestrate service startup
- Missing Dockerfile for containerization with UV workspace support
- No environment configuration for Docker deployment
- Docker compose only has TimescaleDB without the application service
- Cannot run automated data collection in containerized environment

**Current Problematic State:**
```bash
# ❌ WRONG: Cannot run the service in production
# Only TimescaleDB is containerized
docker-compose up -d  # Only starts database
# No way to start the energy data service
```

**Why This is a Deployment Blocker:**
1. **No Containerization**: Service cannot run in isolated, reproducible environment
2. **No Orchestration**: Cannot coordinate service startup with database dependencies
3. **No Configuration Management**: Environment-specific settings not externalized
4. **No Production Readiness**: Manual execution only, not suitable for automated deployment

### 🛠️ **Detailed Implementation Strategy**

#### **Core Solution Approach:**
Create minimal containerization focusing only on SchedulerService execution with proper UV workspace support.

**New Deployment Pattern:**
```bash
# ✅ CORRECT: Complete containerized deployment
docker-compose up -d  # Starts both TimescaleDB and energy-data-service
# Scheduler automatically begins data collection
# Data flows: ENTSO-E API -> SchedulerService -> TimescaleDB
```

#### **Detailed Component Implementation:**

**Main Entry Point Implementation:**
```python
# energy_data_service/main.py
import asyncio
import logging
import signal
from contextlib import AsyncExitStack

from app.container import Container
from app.services.scheduler_service import SchedulerService

class SimpleSchedulerRunner:
    def __init__(self):
        self.container = Container()
        self.exit_stack = AsyncExitStack()
        self.shutdown_event = asyncio.Event()

    async def run(self):
        # Initialize database
        database = self.container.database()
        await self.exit_stack.enter_async_context(database)

        # Start scheduler service
        scheduler = self.container.scheduler_service()
        await self.exit_stack.enter_async_context(scheduler)

        # Wait for shutdown
        await self.shutdown_event.wait()

async def main():
    runner = SimpleSchedulerRunner()
    await runner.run()
```

**Dockerfile Implementation:**
```dockerfile
FROM python:3.13-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY ../entsoe_client ../entsoe_client
RUN uv sync --frozen --no-dev

FROM python:3.13-slim-bookworm AS production
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /app/.venv /app/.venv
WORKDIR /app
COPY app/ ./app/
COPY main.py ./
USER 1000:1000
CMD ["python", "main.py"]
```

### 🔄 **Before/After Transformation**

#### **Before (Manual Development Only):**
```bash
# ❌ Current problematic deployment
cd energy_data_service
uv run pytest  # Tests pass but no production deployment
# No way to run service automatically
# No containerization
# No environment configuration
```

#### **After (Containerized Production):**
```bash
# ✅ New clean deployment
cp .env.example .env  # Configure environment
docker-compose up -d  # Complete stack deployment
docker-compose logs -f energy-data-service  # Monitor data collection
# Automated scheduling and data collection
```

### 📊 **Benefits Quantification**

#### **Deployment Improvements:**
- **Time to Deploy**: Reduced from manual setup to single command (90% faster)
- **Environment Consistency**: 100% reproducible deployments across environments
- **Dependency Management**: UV workspace ensures consistent package resolution

#### **Operations Improvements:**
- **Startup Reliability**: Dependency injection container ensures proper service initialization
- **Error Visibility**: Structured logging in container environment
- **Resource Isolation**: Container limits and security boundaries

#### **Development Improvements:**
- **Local Testing**: Identical environment to production deployment
- **CI/CD Ready**: Container-based deployment supports automated pipelines
- **Scalability Foundation**: Container architecture supports future horizontal scaling

### 🧪 **Comprehensive Testing Strategy**

#### **Container Integration Tests:**
```python
class TestSchedulerContainer:
    async def test_scheduler_startup_in_container(self):
        # Test that scheduler starts successfully in container
        # Verify database connection established
        # Confirm job scheduling begins

    async def test_data_collection_end_to_end(self):
        # Run container for short period
        # Verify ENTSO-E API calls made
        # Confirm data stored in TimescaleDB
```

#### **Environment Configuration Tests:**
```python
class TestEnvironmentConfig:
    async def test_database_connection_from_env(self):
        # Test database configuration from environment variables

    async def test_api_token_configuration(self):
        # Test ENTSO-E API token configuration
```

### 🎯 **Migration/Rollout Strategy**

#### **Implementation Phases:**
1. **Phase 1**: Create main.py and basic Dockerfile (core containerization)
2. **Phase 2**: Add environment configuration and docker-compose integration
3. **Phase 3**: Test deployment and verify data collection

#### **Risk Mitigation:**
- **Build Failures**: Multi-stage Dockerfile with clear error handling
- **Dependency Issues**: UV lock file ensures reproducible builds
- **Runtime Failures**: Health checks and graceful error handling

---
