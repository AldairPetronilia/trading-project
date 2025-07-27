# Current Implementation Plan - Data Collectors Layer

## Next Atomic Step: Implement Data Collectors

Based on the completed Repository Pattern Layer, the next step is implementing the data collection layer that integrates with the existing `entsoe_client` to fetch GL_MarketDocument data from ENTSO-E API.

### What to implement next:

1. **Collector Exception Hierarchy** (`app/exceptions/collector_exceptions.py`) ✅ **COMPLETED**
   - ✅ Define domain-specific exceptions for data collection operations
   - ✅ Provide structured error information with context preservation
   - ✅ Enable proper exception chaining with `raise ... from e` pattern
   - ✅ Support error tracking for different collection failure scenarios

2. **Abstract Base Collector** (`app/collectors/base_collector.py`)
   - Define standardized interface for all data collectors
   - Establish common patterns for data collection operations
   - Provide abstract methods for collect_load_data() and health_check()
   - Enable future extensibility to additional data sources

3. **ENTSO-E Collector Implementation** (`app/collectors/entsoe_collector.py`) ✅ **COMPLETED**
   - ✅ Integrate with existing `entsoe_client.EntsoEClient`
   - ✅ Implement all load data collection methods (actual, day-ahead, week-ahead, month-ahead, year-ahead forecasts plus forecast margin)
   - ✅ Proper async/await patterns with comprehensive type annotations
   - ✅ Return `GlMarketDocument` objects ready for processing layer

4. **Dependency Injection Integration** (`app/container.py`) ✅ **COMPLETED**
   - ✅ Add collector providers using Factory pattern
   - ✅ Wire dependencies: Settings → EntsoeClient → EntsoeCollector
   - ✅ Maintain proper provider scoping and lifecycle management
   - ✅ Follow established DI patterns from repository layer

### Implementation Requirements:

#### Collector Exception Hierarchy Features:
- **Base Collection Error**: Root exception class with operation context tracking
- **Data Source Connection Error**: Network and authentication failure handling
- **API Rate Limit Error**: Specific handling for ENTSO-E rate limiting scenarios
- **Data Format Error**: Invalid or unexpected response format handling
- **Timeout Error**: Request timeout and connection timeout handling
- **Authentication Error**: API token validation and authorization failures

#### Abstract Base Collector Features:
- **Standardized Interface**: Common method signatures for all collector implementations
- **Type Safety**: Full generic type support with proper return type annotations
- **Async Operations**: Native async/await support for non-blocking data collection
- **Error Handling**: Consistent exception handling across all collector implementations
- **Health Monitoring**: Standard health check interface for monitoring and alerting
- **Logging Integration**: Structured logging with operation context and timing

#### ENTSO-E Collector Implementation Features:
- **EntsoeClient Integration**: Proper dependency injection of configured client instance
- **Request Building**: Use LoadDomainRequestBuilder for type-safe API request construction
- **Rate Limiting**: Implement respectful rate limiting to avoid API throttling
- **Error Recovery**: Automatic retry with exponential backoff for transient failures
- **Data Validation**: Basic validation of returned GLMarketDocument objects
- **Performance Monitoring**: Request timing and success rate tracking

### Test Coverage Requirements:

1. **Collector Exception Tests** (`tests/app/exceptions/test_collector_exceptions.py`) ✅ **COMPLETED**
   - ✅ Exception hierarchy validation and proper inheritance
   - ✅ Context preservation and error message formatting
   - ✅ Exception chaining validation with `raise ... from e`
   - ✅ Error code and classification testing

2. **Base Collector Tests** (`tests/app/collectors/test_base_collector.py`)
   - Abstract method enforcement and interface validation
   - Type annotation verification and mypy compliance
   - Common behavior patterns and error handling
   - Mock implementation testing for abstract methods

3. **ENTSO-E Collector Unit Tests** (`tests/app/collectors/test_entsoe_collector.py`) ✅ **COMPLETED**
   - ✅ Mocked entsoe_client integration testing with comprehensive delegation verification
   - ✅ Parameter validation for all collector methods including offset handling
   - ✅ Health check validation and proper initialization testing
   - ✅ Comprehensive async test coverage with proper fixtures

4. **Container Integration Tests** (`tests/app/test_container.py`) ✅ **COMPLETED**
   - ✅ Collector provider registration and resolution
   - ✅ Dependency injection chain validation (Settings → EntsoeClient → EntsoeCollector)
   - ✅ Factory pattern scoping and lifecycle management
   - ✅ Configuration loading and client instantiation with proper mocking

5. **Collector Integration Tests** (`tests/integration/test_collector_integration.py`)
   - Real ENTSO-E API integration testing
   - End-to-end data collection workflow validation
   - Network error handling and recovery testing
   - Performance and rate limiting validation

### Dependencies:

- Builds on existing `DefaultEntsoeClient` from `../entsoe_client/src/entsoe_client/client/default_entsoe_client.py`
- Uses `LoadDomainRequestBuilder` from `../entsoe_client/src/entsoe_client/api/load_domain_request_builder.py`
- Uses `GLMarketDocument` from `../entsoe_client/src/entsoe_client/model/load/gl_market_document.py`
- Uses `Settings` from `app/config/settings.py`
- Uses `Container` from `app/container.py`
- Requires `structlog` (already in pyproject.toml)
- Integration with existing exception patterns from `app/exceptions/repository_exceptions.py`
- Future integration requirement for processors layer

### Success Criteria:

- ✅ **Data Collection Success**: Successfully collect GlMarketDocument data from ENTSO-E API with proper delegation patterns
- ✅ **Testing Success**: Comprehensive unit test coverage with mocked scenarios and dependency injection validation
- ✅ **Integration Success**: Seamless integration with existing entsoe_client and dependency injection container
- ✅ **Error Handling Success**: Robust exception hierarchy with proper context preservation and recovery strategies
- ✅ **Code Quality Success**: Passes all checks (ruff, mypy, pre-commit) with full type safety
- ✅ **Architecture Success**: Establishes clean collector pattern with proper abstraction and delegation
- ✅ **Pattern Consistency Success**: Follows established patterns from repository layer for DI, testing, and error handling

### Completed Items:

- ✅ **Collector Exception Hierarchy**: Complete 8-class exception hierarchy with structured error context, HTTP mapping utilities, and multi-source compatibility
- ✅ **Exception Test Coverage**: Comprehensive test suite with 39 test methods covering inheritance, error mapping, edge cases, and real-world scenarios
- ✅ **ENTSO-E Collector Implementation**: Production-ready collector with 6 load data methods, proper async patterns, comprehensive type safety, and health check functionality
- ✅ **Collector Unit Test Coverage**: Complete test suite with 11 test methods covering delegation verification, parameter validation, offset handling, and initialization
- ✅ **Container Integration**: Full dependency injection integration with Factory providers, proper scoping, and seamless entsoe_client integration
- ✅ **Container Test Coverage**: Comprehensive DI container tests validating provider registration, dependency chains, and configuration handling

## Next Steps: Data Processors Layer

The data collection layer is now complete and production-ready. The next atomic step is implementing the data processing layer that will:

1. **Transform raw GL_MarketDocument data into database-ready models**
2. **Handle time-series data processing and aggregation**
3. **Implement data validation and quality checks**
4. **Prepare data for storage in the TimescaleDB repository**

This data collection layer establishes the foundation for fetching external energy data needed for the processors layer that will transform raw GlMarketDocument data into database-ready models.
