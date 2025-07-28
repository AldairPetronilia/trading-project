# Current Implementation Plan - Service Orchestration Layer

## Next Atomic Step: Service Layer Implementation

Based on the completed core data pipeline (Collectors → Processors → Repositories), the next step is implementing the Service Orchestration layer that provides gap-filling, backfilling, and business logic coordination.

### What to implement next:

1. **EntsoE Data Service** (`app/services/entsoe_data_service.py`)
   - Gap detection and filling for all endpoint/area combinations
   - Smart database-driven collection scheduling
   - Intelligent chunking and rate limiting for large date ranges
   - Comprehensive error handling and operation logging

2. **Backfill Service** (`app/services/backfill_service.py`)
   - One-time historical data loading with progress tracking
   - Intelligent backfill detection based on database coverage
   - Controlled historical collection with API-friendly chunking
   - Resumable operations for large historical datasets

3. **Service Exceptions** (`app/services/service_exceptions.py`)
   - Service-level error hierarchy with context preservation
   - HTTP status code mapping for API integration
   - Structured error logging for debugging and monitoring
   - Operation context tracking for distributed debugging

4. **Configuration Enhancement** (`app/config/settings.py`)
   - Collection intervals per endpoint type
   - Backfill parameters and historical coverage requirements
   - Rate limiting and chunking configurations
   - Multi-area/region collection settings

### Implementation Requirements:

#### EntsoE Data Service Features:
- **Gap Detection Logic**: Query database for latest timestamp per endpoint/area, calculate gaps from last collection to now
- **Smart Collection Scheduling**: Different collection intervals per endpoint type (actual: 30min, forecasts: 6hrs, margins: daily)
- **Intelligent Chunking**: Split large date ranges into API-friendly chunks (30 days) with rate limiting between chunks
- **Transaction Management**: Ensure data consistency across collector → processor → repository pipeline
- **Error Recovery**: Handle partial failures with retry logic and continuation from last successful point
- **Operation Logging**: Comprehensive structured logging for collection operations, timing, and data volumes

#### Backfill Service Features:
- **Coverage Analysis**: Check database for historical data coverage and identify gaps requiring backfill
- **Controlled Collection**: Backfill historical data without overwhelming ENTSO-E APIs using slower, respectful collection
- **Progress Tracking**: Persist backfill progress to enable resumable operations across service restarts
- **Chunked Processing**: Process large historical periods in manageable chunks with proper rate limiting
- **Data Validation**: Ensure historical data quality and completeness during backfill operations
- **Resource Management**: Monitor and limit resource usage during intensive backfill operations

#### Service Exception Hierarchy Features:
- **Service Error Base**: Context-aware base exception class with operation tracking and timing information
- **Collection Errors**: Specific exceptions for gap detection failures, collection timeouts, and API rate limiting
- **Backfill Errors**: Dedicated exceptions for backfill progress tracking, resume failures, and historical data validation
- **Transaction Errors**: Database transaction and consistency error handling with rollback capabilities
- **HTTP Integration**: Status code mapping for FastAPI error responses and client error handling
- **Structured Logging**: Error context serialization for structured logging and monitoring systems

### Test Coverage Requirements:

1. **EntsoE Data Service Unit Tests** (`tests/app/services/test_entsoe_data_service.py`)
   - Gap detection logic with various database states (empty, partial, complete coverage)
   - Collection scheduling with different endpoint intervals and area combinations
   - Chunking logic with various date ranges and API limits
   - Error handling and retry scenarios with mocked dependencies

2. **Backfill Service Unit Tests** (`tests/app/services/test_backfill_service.py`)
   - Coverage analysis with different historical data scenarios
   - Progress tracking and resume functionality testing
   - Chunked processing with various historical periods
   - Resource management and rate limiting validation

3. **Service Exception Tests** (`tests/app/services/test_service_exceptions.py`)
   - Exception hierarchy inheritance and context preservation
   - HTTP status code mapping for all exception types
   - Structured logging output validation
   - Error context serialization and deserialization

4. **Service Integration Tests** (`tests/integration/test_service_integration.py`)
   - End-to-end pipeline orchestration with real database and collector
   - Gap detection and filling with actual ENTSO-E API calls
   - Backfill operations with historical data collection
   - Performance validation with large datasets and concurrent operations

5. **Container Integration Tests** (`tests/app/test_container.py`)
   - Service provider registration and dependency injection
   - Service composition and lifecycle management
   - Configuration injection and validation

### Dependencies:

- Builds on existing `EntsoeCollector` from `app/collectors/entsoe_collector.py`
- Uses `GlMarketDocumentProcessor` from `app/processors/gl_market_document_processor.py`
- Uses `EnergyDataRepository` from `app/repositories/energy_data_repository.py`
- Uses `Settings` configuration from `app/config/settings.py`
- Requires `Container` dependency injection from `app/container.py`
- Integration with existing exception hierarchies from `app/exceptions/`
- Future integration requirement for API layer and task scheduling

### Success Criteria:

- **Gap Detection Accuracy**: Service correctly identifies missing data periods for all endpoint/area combinations
- **Collection Completeness**: Successfully fills gaps without missing data points or creating duplicates
- **Backfill Efficiency**: Historical data collection completes within reasonable timeframes without API throttling
- **Error Handling Robustness**: Service gracefully handles API failures, database issues, and partial collection failures
- **Performance Requirements**: Handles multiple areas and endpoints efficiently with proper resource management
- **Code Quality Compliance**: Passes all checks (ruff, mypy, pre-commit) with comprehensive type annotations
- **Integration Readiness**: Service layer provides clean interface for API endpoints and task scheduling
- **Pattern Consistency**: Follows established dependency injection, error handling, and testing patterns

This Service Orchestration layer establishes the complete business logic foundation needed for API endpoints and automated scheduling, completing the core MVP data pipeline functionality.
