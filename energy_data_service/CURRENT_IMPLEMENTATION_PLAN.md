# Current Implementation Plan - Dependency Injection + Repository Pattern Layer

## Next Atomic Step: Dependency Injection Container + Repository Pattern

Based on the completed database foundation layer, the next step is implementing dependency injection (following `entsoe_client` patterns) and the repository pattern for data access operations.

### What to implement next:

1. **Dependency injection container** (`app/container.py`)
   - Production-ready container following `entsoe_client` patterns
   - Configuration providers for Settings and Database components
   - Factory providers for repositories and future service layers
   - Async startup/shutdown hooks for resource management

2. **Base repository pattern** (`app/repositories/base_repository.py`)
   - Abstract base class for all repositories
   - Common CRUD operations interface
   - Async database session management
   - Generic type support for different models

3. **EnergyDataPoint repository** (`app/repositories/energy_data_repository.py`)
   - Concrete implementation for EnergyDataPoint model
   - Time-series specific query methods
   - Batch insert operations for high-volume data
   - Query by area, time range, data type filtering
   - Specialized methods for energy data analytics

4. **Repository exception hierarchy** (`app/exceptions/repository_exceptions.py`)
   - Base repository exceptions with proper exception chaining
   - Specific exceptions for data conflicts, validation errors
   - Context preservation with `raise ... from e` pattern

### Implementation Requirements:

#### Dependency Injection Container Features:
- **Configuration providers**: Settings, DatabaseConfig, EntsoEClientConfig
- **Database providers**: Database class, AsyncEngine, session factory
- **Repository providers**: Factory providers for base and energy repositories
- **Resource lifecycle**: Async startup/shutdown for database connections
- **Environment handling**: Development/staging/production configurations
- **Provider scoping**: Singleton vs factory patterns for different components

#### Base Repository Features:
- Generic type support: `BaseRepository[ModelType]`
- Session management using injected Database class from container
- Standard CRUD operations: `create`, `get_by_id`, `get_all`, `update`, `delete`
- Batch operations: `create_batch`, `update_batch`
- Exception handling with custom repository exceptions
- Proper async context management with database sessions

#### Energy Data Repository Features:
- **Time-range queries**: Get data points between start/end timestamps
- **Area filtering**: Query by specific area codes or multiple areas
- **Data type filtering**: Filter by EnergyDataType enum values
- **Business type filtering**: Filter by business type codes
- **Aggregation queries**: Support for time-based aggregations (hourly, daily, monthly)
- **Latest data queries**: Get most recent data points for areas
- **Batch upsert**: Handle duplicate data points gracefully with conflict resolution
- **Performance optimization**: Strategic query optimization for TimescaleDB

### Test Coverage Requirements:

1. **Container unit tests** (`tests/app/test_container.py`)
   - Provider registration and dependency resolution
   - Configuration loading with different environments
   - Database provider lifecycle management
   - Repository provider creation and injection

2. **Base repository unit tests** (`tests/app/repositories/test_base_repository.py`)
   - Test all CRUD operations with mocked database sessions
   - Exception handling tests with proper error propagation
   - Generic type behavior validation
   - Session management and transaction handling

3. **Energy repository unit tests** (`tests/app/repositories/test_energy_data_repository.py`)
   - All specialized query methods with various filters
   - Batch operations with different data scenarios
   - Filter combinations and edge cases
   - Performance considerations for large datasets
   - Enum validation and type safety

4. **Integration tests** (`tests/integration/test_repository_integration.py`)
   - Real database operations using testcontainers
   - Container + repository integration with actual database
   - Complex query scenarios with real data
   - Transaction behavior validation
   - Concurrent access patterns

5. **Container integration tests** (`tests/integration/test_container_integration.py`)
   - Full dependency injection chain with real database
   - Configuration loading from actual environment
   - Resource lifecycle management validation

### Dependencies:

- Builds on existing Database class from `app/config/database.py`
- Uses Settings configuration from `app/config/settings.py`
- Uses EnergyDataPoint model from `app/models/load_data.py`
- Requires `dependency-injector` library (already in pyproject.toml)
- Integration with existing exception hierarchy patterns
- FastAPI dependency integration for future API layer

### Success Criteria:

- **Container properly configured**: All providers registered and working
- **Repository methods tested**: All CRUD and specialized methods with comprehensive coverage
- **Dependency injection working**: Clean dependency resolution throughout application
- **Database optimization**: Efficient query performance for time-series operations
- **Error handling**: Proper exception handling and logging throughout
- **Code quality**: Passes all checks (ruff, mypy, pre-commit)
- **Integration ready**: Foundation prepared for collector, processor, and API layers
- **Pattern consistency**: Follows same dependency injection patterns as `entsoe_client`

This foundation establishes the complete dependency injection and data access architecture needed for the MVP data pipeline: collect → process → store → serve.
