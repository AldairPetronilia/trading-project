# Energy Data Service MVP Architecture

## Overview

A focused MVP that leverages your existing `entsoe_client` to collect GL_MarketDocument data, process it into database-friendly format, and serve it via REST API. Designed for easy extension to additional data sources.

## Database Infrastructure Status

**✅ Database Ready**: TimescaleDB infrastructure is implemented and operational at the project root level:

- **Location**: `../docker-compose.yml` (project root)
- **Service**: TimescaleDB running in Docker container
- **Database**: `energy_data_service` with TimescaleDB extension
- **Data Storage**: `../data/timescaledb/` (persistent local storage)
- **Configuration**: `../.env` with database credentials
- **Initialization**: Minimal setup - only TimescaleDB extension created

**Next Steps**: With database infrastructure ready, the application can now implement the MVP layers starting with configuration and models that will connect to the existing TimescaleDB instance.

## Implementation Progress

**✅ Configuration Layer Completed** (2025-01-18):
- **`app/config/settings.py`**: Production-ready configuration system with Pydantic Settings
  - Environment-aware configuration (development/staging/production)
  - Database configuration with PostgreSQL+AsyncPG URL generation
  - ENTSO-E client configuration with API token validation
  - HTTP configuration for FastAPI timeouts
  - Logging configuration with structured logging support
  - Secure model dumping that redacts sensitive information
- **`app/exceptions/config_validation_error.py`**: Custom exception hierarchy for configuration validation
  - Port validation, API token validation, environment validation
  - Consistent error messages and field tracking
- **`tests/app/config/test_settings.py`**: Comprehensive test suite for configuration system
  - Tests for all configuration classes (DatabaseConfig, EntsoEClientConfig, LoggingConfig, HttpConfig, Settings)
  - Environment variable loading tests
  - .env file loading tests (including project .env file integration)
  - Validation error tests for all custom validators
  - Security tests for sensitive data redaction
  - 30+ test cases covering all configuration scenarios
- **Code Quality**: All code passes ruff linting and mypy type checking
- **Pattern Alignment**: Configuration follows the same patterns as `entsoe_client` for consistency
- **Environment Integration**: Successfully loads from project root `.env` file with actual database credentials

**✅ Database Foundation Layer Completed** (2025-01-24):

### Database Connection Factory
- **`app/config/database.py`**: Production-ready async database connection factory
  - AsyncEngine creation with proper configuration
  - Session factory with async context management
  - Connection lifecycle management with commit/rollback handling
  - Async generator pattern for FastAPI dependency injection
- **Comprehensive test coverage**: Unit tests with async mocking and integration tests with real PostgreSQL via testcontainers
- **Exception-safe session management**: Automatic commit on success, rollback on exception

### Base Database Models
- **`app/models/base.py`**: Abstract base class with automatic audit tracking
  - `TimestampedModel` with `created_at` and `updated_at` fields
  - PostgreSQL `now()` defaults with timezone awareness
  - SQLAlchemy 2.0 type annotations with `Mapped[datetime]`
  - mypy-compatible type annotations using `DeclarativeMeta`

### Core Energy Data Model
- **`app/models/load_data.py`**: Unified table design for all ENTSO-E energy data types
  - **Architecture Decision**: Single `energy_data_points` table instead of separate tables per endpoint
  - **Composite primary key**: `(timestamp, area_code, data_type, business_type)`
  - **EnergyDataType enum**: Supports `actual`, `day_ahead`, `week_ahead`, `month_ahead`, `year_ahead`, `forecast_margin`
  - **Complete GlMarketDocument field mapping** with financial-grade decimal precision (15,3)
  - **Multi-source ready**: `data_source` field for future expansion beyond ENTSO-E
  - **Performance optimized**: Strategic indexes for time-series and analytics queries
- **Comprehensive test suite**: 16 test cases covering model functionality, enum validation, and database schema
- **Data processing architecture**: XML Point mapping with timestamp calculation and area code extraction

### Implementation Status Summary
**✅ Completed Foundation:**
- Configuration layer with Pydantic settings and comprehensive validation
- Database connection factory with full async support and test coverage
- Base database models with audit tracking and timezone awareness
- Core EnergyDataPoint model with unified table design for all data types
- Complete test coverage for all foundation components
- Integration testing with real PostgreSQL database via testcontainers

**✅ Repository Pattern Layer Completed** (2025-01-24): Production-ready data access layer with comprehensive integration testing.

### Repository Pattern Implementation Completed

**✅ Exception Hierarchy & Error Handling**:
- **`app/exceptions/repository_exceptions.py`**: Complete exception hierarchy with structured error information, proper exception chaining with `raise ... from e`, and full type annotations
- Domain-specific exceptions: `DataAccessError`, `DataValidationError`, `DuplicateDataError`, `ConstraintViolationError`, `DatabaseConnectionError`
- Production features: Error context preservation, model type tracking, operation tracking, PostgreSQL error code integration

**✅ Abstract Base Repository**:
- **`app/repositories/base_repository.py`**: Production-ready abstract base repository with generic type support `BaseRepository[ModelType]`
- Complete CRUD operations: `create`, `get_by_id`, `get_all`, `update`, `delete` with async session management
- Batch operations: `create_batch`, `update_batch` with transaction safety and error handling
- Database session lifecycle: Automatic commit/rollback, proper exception handling, async context management

**✅ Energy Data Repository**:
- **`app/repositories/energy_data_repository.py`**: Concrete repository implementation for `EnergyDataPoint` with time-series optimization
- Specialized query methods: `get_by_time_range`, `get_by_area`, `get_latest_for_area` with multiple filter combinations
- Batch upsert operations: `upsert_batch` with conflict resolution using PostgreSQL's `ON CONFLICT` clause
- Composite primary key handling: Efficient tuple-based operations and convenience methods
- TimescaleDB optimization: Strategic query patterns for time-series data performance

**✅ Dependency Injection Integration**:
- **`app/container.py`**: Updated DI container with repository providers using Factory pattern
- EntsoE client integration: Proper factory pattern with secret token extraction wrapper function
- Provider scoping: Singleton for database connections, Factory for repository instances
- Complete dependency chain: Settings → Database → Repository with proper injection

**✅ Comprehensive Test Coverage**:
- **Unit Tests**: Complete coverage of all repository functionality with mocked database sessions
  - `tests/app/test_container.py`: Container provider validation, dependency resolution, configuration loading
  - `tests/app/repositories/test_base_repository.py`: Base repository CRUD operations, batch processing, error handling
  - `tests/app/repositories/test_energy_data_repository.py`: Energy repository specialized queries, filtering, batch operations
- **Integration Tests**: **GOLD STANDARD** real database testing with PostgreSQL testcontainers
  - `tests/integration/test_container_integration.py`: Complete DI chain validation, provider scoping, concurrent access, configuration validation
  - `tests/integration/test_repository_integration.py`: TimescaleDB hypertables, time-series operations, concurrent testing, comprehensive database validation

**✅ Production-Ready Features**:
- **Database Infrastructure**: Real TimescaleDB with hypertables, extensions, and time-series optimizations validated
- **Type Safety**: Full mypy compliance demonstrated in both unit and integration testing scenarios
- **Error Handling**: Exception hierarchies and database constraint validation tested with real database
- **Concurrency**: Multi-threaded operations and resource sharing validation proven
- **Resource Management**: Proper database lifecycle, cleanup, and connection handling demonstrated

**✅ Architecture Achievement**: **BATTLE-TESTED, PRODUCTION-READY** repository layer providing the complete data access foundation for the MVP data pipeline with **GOLD STANDARD** integration testing serving as reference examples for the entire project.

## Repository Pattern Purpose & Responsibilities

**Purpose**: Repositories serve as the **data access layer** that provides a clean abstraction between business logic and the database, acting as an **in-memory collection interface** for database entities.

**Key Responsibilities**:
1. **Abstract database operations** - Hide SQL/ORM complexity behind simple method calls
2. **Provide type-safe data access** - Return proper domain models with full type checking
3. **Enable testability** - Can be easily mocked for unit testing
4. **Centralize query logic** - Keep complex queries in one place
5. **Support the Repository Pattern** - A well-established architectural pattern for data access

**In the Data Flow**:
```
Collector → Processor → Repository → Database
                           ↑
                    Your API queries this
```

The repository sits between **business logic** (services, API endpoints) and the **database**, providing methods like:
```python
# Instead of writing raw SQL everywhere
await energy_repo.get_load_data_by_area_and_time_range("DE", start, end)
await energy_repo.batch_upsert_data_points(processed_data_points)
await energy_repo.get_latest_data_for_areas(["DE", "FR", "NL"])
```

This keeps services clean and focused on business logic rather than database mechanics.

## MVP Repository Structure

```
energy_data_service/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── container.py               # ✅ COMPLETED: Dependency injection container
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py            # ✅ COMPLETED: Pydantic settings
│   │   └── database.py            # ✅ COMPLETED: Database connection factory
│   ├── collectors/                # Data collection layer (your "clients")
│   │   ├── __init__.py
│   │   ├── base_collector.py      # Abstract collector interface
│   │   └── entsoe_collector.py    # ENTSO-E data collection using your client
│   ├── processors/                # Data transformation layer
│   │   ├── __init__.py
│   │   ├── base_processor.py      # Abstract processor interface
│   │   └── entsoe_processor.py    # Transform GL_MarketDocument to DB models
│   ├── repositories/              # ✅ COMPLETED: Data access layer
│   │   ├── __init__.py            # ✅ COMPLETED: Repository package
│   │   ├── base_repository.py     # ✅ COMPLETED: Abstract repository pattern
│   │   └── energy_data_repository.py # ✅ COMPLETED: Energy data storage with time-series optimization
│   ├── models/                    # ✅ COMPLETED: Database models
│   │   ├── __init__.py            # ✅ COMPLETED: Model package
│   │   ├── base.py                # ✅ COMPLETED: Base model with timestamps
│   │   └── load_data.py           # ✅ COMPLETED: Energy data time-series model
│   ├── services/                  # Business logic orchestration
│   │   ├── __init__.py
│   │   ├── data_collection_service.py  # Orchestrates collection + processing + storage
│   │   └── scheduler_service.py   # Task scheduling
│   ├── api/                       # REST API layer
│   │   ├── __init__.py
│   │   ├── dependencies.py        # FastAPI dependencies
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py          # Main API router
│   │       ├── endpoints/
│   │       │   ├── __init__.py
│   │       │   ├── load_data.py   # Load/generation endpoints
│   │       │   └── health.py      # Health checks
│   │       └── schemas/           # Pydantic schemas
│   │           ├── __init__.py
│   │           ├── load_data.py   # Load data response models
│   │           └── common.py      # Common schemas
│   ├── exceptions/                # ✅ COMPLETED: Custom exceptions
│   │   ├── __init__.py
│   │   ├── config_validation_error.py # ✅ COMPLETED: Configuration exceptions
│   │   ├── repository_exceptions.py   # ✅ COMPLETED: Repository exception hierarchy
│   │   ├── collector_exceptions.py
│   │   └── processor_exceptions.py
│   └── utils/                     # Shared utilities
│       ├── __init__.py
│       ├── logging.py             # Structured logging
│       └── time_utils.py          # Time zone utilities
├── tests/
│   ├── __init__.py
│   ├── app/                       # ✅ COMPLETED: Unit tests
│   │   ├── __init__.py
│   │   ├── test_container.py      # ✅ COMPLETED: Container tests
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   ├── test_settings.py   # ✅ COMPLETED: Configuration tests
│   │   │   └── test_database.py   # ✅ COMPLETED: Database tests
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── test_load_data.py  # ✅ COMPLETED: Model tests
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── test_base_repository.py      # ✅ COMPLETED: Base repository tests
│   │       └── test_energy_data_repository.py # ✅ COMPLETED: Energy repository tests
│   ├── integration/               # ✅ COMPLETED: Integration tests (**GOLD STANDARD**)
│   │   ├── __init__.py
│   │   ├── test_container_integration.py    # ✅ COMPLETED: Container integration tests
│   │   ├── test_repository_integration.py  # ✅ COMPLETED: Repository integration tests
│   │   ├── test_database.py       # ✅ COMPLETED: Database integration tests
│   │   └── test_end_to_end.py     # Full collection -> storage -> API flow
│   └── fixtures/
│       ├── __init__.py
│       └── gl_market_document.py  # Sample XML data
├── alembic/                       # Database migrations
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── scripts/
│   ├── __init__.py
│   ├── init_database.py
│   └── backfill_historical_data.py  # Critical for initial X years of data
├── pyproject.toml                  # Updated with all MVP dependencies
├── alembic.ini
├── .env                            # Local database config and API keys
└── .env.example                    # Template for energy_data_service config
```

## Core Data Flow

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│   ENTSO-E   │───▶│   Collector  │───▶│    Processor    │───▶│  Repository  │
│     API     │    │ (entsoe_client)│    │(GL_MarketDoc   │    │ (TimescaleDB)│
│             │    │               │    │ -> DB models)   │    │              │
└─────────────┘    └──────────────┘    └─────────────────┘    └──────────────┘
                           │                       │                    │
                           ▼                       ▼                    ▼
                   ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
                   │   Service    │───▶│   FastAPI       │───▶│   Modeling   │
                   │ Orchestrator │    │   Endpoints     │    │   Service    │
                   └──────────────┘    └─────────────────┘    └──────────────┘
```

## Core Dependencies (MVP)

```toml
[project.dependencies]
# Web framework
fastapi = "^0.115.0"
uvicorn = "^0.32.0"

# Database (TimescaleDB is PostgreSQL extension)
sqlalchemy = "^2.0.36"
asyncpg = "^0.30.0"
alembic = "^1.14.0"

# Dependency injection (matches your pattern)
dependency-injector = "^4.42.0"

# Data validation
pydantic = "^2.10.2"
pydantic-settings = "^2.6.1"

# Task scheduling (simple for MVP)
apscheduler = "^3.10.4"

# Logging
structlog = "^24.4.0"

# Your existing client
entsoe-client = {path = "../entsoe_client", develop = true}
```

## Database Model for GL_MarketDocument

```python
# models/load_data.py
from sqlalchemy import String, DateTime, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column
from decimal import Decimal
from datetime import datetime
from .base import TimestampedModel

class LoadDataPoint(TimestampedModel):
    """
    Stores individual time-series points from GL_MarketDocument
    Each Point in the XML becomes one row
    """
    __tablename__ = "load_data_points"

    # Primary key components
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    area_code: Mapped[str] = mapped_column(String(20), primary_key=True)  # outBiddingZone_Domain
    business_type: Mapped[str] = mapped_column(String(10), primary_key=True)  # A60, etc.

    # Data values
    quantity_mw: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    # Metadata from GL_MarketDocument
    document_mrid: Mapped[str] = mapped_column(String(50))
    time_series_mrid: Mapped[str] = mapped_column(String(10))
    object_aggregation: Mapped[str] = mapped_column(String(10))  # A01, etc.
    unit_name: Mapped[str] = mapped_column(String(10))  # MAW, MW
    curve_type: Mapped[str] = mapped_column(String(10))  # A01
    resolution_minutes: Mapped[int] = mapped_column(Integer)  # Calculated from resolution

    # Source tracking
    data_source: Mapped[str] = mapped_column(String(20), default="entsoe")
```

## Collector Pattern (Your "Clients")

```python
# collectors/base_collector.py
from abc import ABC, abstractmethod
from typing import List, Any
from datetime import datetime

class BaseCollector(ABC):
    """Abstract base for all data collectors"""

    @abstractmethod
    async def collect_load_data(
        self,
        start_time: datetime,
        end_time: datetime,
        area_code: str
    ) -> List[Any]:
        """Collect raw data from external source"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if data source is accessible"""
        pass

# collectors/entsoe_collector.py
from entsoe_client.client.default_entsoe_client import DefaultEntsoeClient
from entsoe_client.api.load_domain_request_builder import LoadDomainRequestBuilder
from entsoe_client.model.load.gl_market_document import GLMarketDocument

class EntsoeCollector(BaseCollector):
    """Collector using your existing entsoe_client"""

    def __init__(self, entsoe_client: DefaultEntsoeClient):
        self.client = entsoe_client
        self.logger = structlog.get_logger()

    async def collect_load_data(
        self,
        start_time: datetime,
        end_time: datetime,
        area_code: str
    ) -> List[GLMarketDocument]:
        """Collect load data using your entsoe_client"""

        try:
            request = (LoadDomainRequestBuilder()
                      .with_period_start(start_time)
                      .with_period_end(end_time)
                      .with_area_code(area_code)
                      .build())

            self.logger.info("Collecting load data",
                           start=start_time, end=end_time, area=area_code)

            documents = await self.client.get_load_data(request)

            self.logger.info("Successfully collected data",
                           document_count=len(documents))

            return documents

        except Exception as e:
            self.logger.error("Failed to collect data", error=str(e))
            raise CollectorError(f"ENTSO-E collection failed: {e}") from e

    async def health_check(self) -> bool:
        """Simple health check"""
        try:
            # Could make a minimal API call
            return True
        except Exception:
            return False
```

## Processor Pattern (XML to Database)

```python
# processors/base_processor.py
from abc import ABC, abstractmethod
from typing import List, Any

class BaseProcessor(ABC):
    """Abstract base for data processors"""

    @abstractmethod
    async def process(self, raw_data: List[Any]) -> List[Any]:
        """Transform raw data into database models"""
        pass

# processors/entsoe_processor.py
from entsoe_client.model.load.gl_market_document import GLMarketDocument
from ..models.load_data import LoadDataPoint
from ..utils.time_utils import parse_resolution_to_minutes, calculate_timestamps

class EntsoeProcessor(BaseProcessor):
    """Process GL_MarketDocument XML into database models"""

    def __init__(self):
        self.logger = structlog.get_logger()

    async def process(self, documents: List[GLMarketDocument]) -> List[LoadDataPoint]:
        """Transform GL_MarketDocument objects into LoadDataPoint models"""

        data_points = []

        for document in documents:
            try:
                data_points.extend(await self._process_document(document))
            except Exception as e:
                self.logger.error("Failed to process document",
                                document_mrid=document.mrid, error=str(e))
                raise ProcessorError(f"Document processing failed: {e}") from e

        self.logger.info("Processed documents",
                        document_count=len(documents),
                        data_point_count=len(data_points))

        return data_points

    async def _process_document(self, document: GLMarketDocument) -> List[LoadDataPoint]:
        """Process a single GL_MarketDocument"""

        data_points = []

        for time_series in document.time_series:
            # Extract metadata
            area_code = self._extract_area_code(time_series.out_bidding_zone_domain_mrid)
            business_type = time_series.business_type

            for period in time_series.periods:
                # Calculate resolution in minutes
                resolution_minutes = parse_resolution_to_minutes(period.resolution)

                # Calculate timestamps for each point
                timestamps = calculate_timestamps(
                    period.time_interval.start,
                    period.time_interval.end,
                    resolution_minutes
                )

                # Create data points
                for i, point in enumerate(period.points):
                    if i < len(timestamps):
                        data_point = LoadDataPoint(
                            timestamp=timestamps[i],
                            area_code=area_code,
                            business_type=business_type,
                            quantity_mw=Decimal(str(point.quantity)),
                            document_mrid=document.mrid,
                            time_series_mrid=time_series.mrid,
                            object_aggregation=time_series.object_aggregation,
                            unit_name=time_series.quantity_measure_unit_name,
                            curve_type=time_series.curve_type,
                            resolution_minutes=resolution_minutes
                        )
                        data_points.append(data_point)

        return data_points

    def _extract_area_code(self, domain_mrid: str) -> str:
        """Extract clean area code from domain MRID"""
        # Example: "10YCZ-CEPS-----N" -> "CZ"
        # Implementation depends on your domain knowledge
        return domain_mrid[2:4] if len(domain_mrid) >= 4 else domain_mrid
```

## Service Orchestration

```python
# services/data_collection_service.py
class DataCollectionService:
    """Orchestrates the full data collection pipeline"""

    def __init__(
        self,
        collector: BaseCollector,
        processor: BaseProcessor,
        repository: LoadDataRepository
    ):
        self.collector = collector
        self.processor = processor
        self.repository = repository
        self.logger = structlog.get_logger()

    async def collect_and_store_load_data(
        self,
        start_time: datetime,
        end_time: datetime,
        area_code: str
    ) -> int:
        """Full pipeline: collect -> process -> store"""

        try:
            # Step 1: Collect raw data
            raw_documents = await self.collector.collect_load_data(
                start_time, end_time, area_code
            )

            if not raw_documents:
                self.logger.warning("No data collected",
                                  start=start_time, end=end_time, area=area_code)
                return 0

            # Step 2: Process into database models
            data_points = await self.processor.process(raw_documents)

            # Step 3: Store in database
            stored_count = await self.repository.save_batch(data_points)

            self.logger.info("Successfully collected and stored data",
                           area=area_code,
                           time_range=f"{start_time} to {end_time}",
                           points_stored=stored_count)

            return stored_count

        except Exception as e:
            self.logger.error("Data collection pipeline failed",
                            area=area_code,
                            error=str(e))
            raise DataCollectionError(f"Pipeline failed: {e}") from e
```

## Historical Data Backfill Strategy

```python
# scripts/backfill_historical_data.py
"""
Critical script for initial data collection
Collect X years of historical data before starting regular updates
"""

class HistoricalDataBackfill:
    def __init__(self, data_collection_service: DataCollectionService):
        self.service = data_collection_service
        self.logger = structlog.get_logger()

    async def backfill_area_data(
        self,
        area_code: str,
        start_date: datetime,
        end_date: datetime,
        chunk_days: int = 30  # Collect in monthly chunks
    ) -> None:
        """Backfill historical data for a specific area"""

        current_date = start_date

        while current_date < end_date:
            chunk_end = min(current_date + timedelta(days=chunk_days), end_date)

            try:
                await self.service.collect_and_store_load_data(
                    current_date, chunk_end, area_code
                )

                # Rate limiting - be nice to ENTSO-E
                await asyncio.sleep(2)

            except Exception as e:
                self.logger.error("Backfill chunk failed",
                                area=area_code,
                                chunk_start=current_date,
                                chunk_end=chunk_end,
                                error=str(e))
                # Continue with next chunk

            current_date = chunk_end
```

## API Design (Simple but Complete)

```python
# api/v1/endpoints/load_data.py
@router.get("/load-data", response_model=List[LoadDataResponse])
async def get_load_data(
    area_code: str = Query(..., description="Area code (e.g., 'DE', 'FR')"),
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    business_type: Optional[str] = Query(None),
    repository: LoadDataRepository = Depends(get_load_data_repository)
) -> List[LoadDataResponse]:
    """Get load/generation data for modeling service"""

    data_points = await repository.get_by_criteria(
        area_code=area_code,
        start_time=start_time,
        end_time=end_time,
        business_type=business_type
    )

    return [LoadDataResponse.model_validate(point) for point in data_points]

@router.post("/collect-data")
async def trigger_data_collection(
    request: CollectionRequest,
    service: DataCollectionService = Depends(get_data_collection_service)
) -> CollectionResponse:
    """Manually trigger data collection (useful for testing/backfill)"""

    count = await service.collect_and_store_load_data(
        request.start_time,
        request.end_time,
        request.area_code
    )

    return CollectionResponse(points_collected=count)
```

## Key MVP Features

### 1. **Focused Scope**
- Single data source (ENTSO-E via your client)
- Single data type (Load/Generation from GL_MarketDocument)
- Simple scheduling (APScheduler, not Celery)

### 2. **Extensible Design**
- Abstract base classes for Collectors and Processors
- Easy to add new data sources later
- Repository pattern ready for complex queries

### 3. **Production Considerations**
- **Historical backfill** capability for X years of data
- **TimescaleDB** optimizations for time-series
- **Health checks** and monitoring
- **Structured logging** throughout

### 4. **Testing Strategy**
- Unit tests for each layer
- Integration tests for full pipeline
- Fixtures with real GL_MarketDocument XML

## Application Lifecycle Management

**Resource Management Philosophy**: Database connection lifecycle should be managed at the application level (FastAPI startup/shutdown events), not within the dependency injection container. The DI container's responsibility is purely dependency resolution and injection.

**Implementation Pattern**:
```python
# In FastAPI application or main entry point
async def startup():
    container = Container()
    # Test database connection
    await container.database().engine.begin()

async def shutdown():
    # Cleanup database connections
    await container.database().engine.dispose()
```

**Container Responsibility**: The `Container` class should focus solely on dependency injection without lifecycle management methods. Resource cleanup is handled by the application framework or main application entry point.

## 🎯 CURRENT MVP STATUS: FOUNDATION LAYERS COMPLETE

**✅ COMPLETED LAYERS (Production-Ready with Gold Standard Testing)**:
1. **Configuration Layer**: Environment-aware settings with comprehensive validation
2. **Database Foundation**: Async connection factory with TimescaleDB optimization
3. **Data Models**: Unified energy data model with composite primary keys
4. **Repository Pattern**: Complete data access layer with time-series optimization
5. **Dependency Injection**: Production container with proper provider scoping
6. **Exception Handling**: Comprehensive error hierarchies with context preservation
7. **Integration Testing**: **GOLD STANDARD** tests with real database validation

**🚧 NEXT IMPLEMENTATION PHASES**:
1. **Data Collectors**: Services to fetch data from ENTSO-E API using existing `entsoe_client`
2. **Data Processors**: Business logic for transforming GL_MarketDocument XML to database models
3. **Service Orchestration**: Business logic layer coordinating collection → processing → storage
4. **API Layer**: FastAPI endpoints for serving energy data to modeling services
5. **Task Scheduling**: Automated data collection and historical backfill capabilities

**🏗️ MVP FOUNDATION ACHIEVEMENT**: This MVP provides a **BATTLE-TESTED, PRODUCTION-READY** foundation that handles the complex database infrastructure and data access patterns needed for time-series energy data. The foundation layers are complete with **GOLD STANDARD** integration testing that serves as reference examples for implementing the remaining application layers.

The completed foundation makes it straightforward to implement the remaining layers since all the complex database operations, error handling, dependency injection, and testing patterns are already established and proven with real database operations.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "create-mvp-architecture", "content": "Create refined MVP architecture combining collectors, processors, and repositories for GL_MarketDocument processing", "status": "completed", "priority": "high"}]
