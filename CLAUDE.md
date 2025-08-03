# CLAUDE.md

Directory structure:
└── trading-project/
    ├── CLAUDE.md
    ├── docker-compose.yml
    ├── mypy.ini
    ├── pyproject.toml
    ├── PYTHON_PRODUCTION_STANDARDS.md
    ├── ruff.toml
    ├── uv.lock
    ├── .env.example
    ├── .pre-commit-config.yaml
    ├── data/
    │   └── .gitkeep
    ├── energy_data_service/
    │   ├── README.md
    │   ├── debug_startup.py
    │   ├── Dockerfile
    │   ├── IMPLEMENTATION_PLAN_TEMPLATE.md
    │   ├── main.py
    │   ├── MINIMAL_DOCKER_DEPLOYMENT_PLAN.md
    │   ├── MVP_ARCHITECTURE.md
    │   ├── pyproject.toml
    │   ├── .python-version
    │   ├── app/
    │   │   ├── __init__.py
    │   │   ├── container.py
    │   │   ├── collectors/
    │   │   │   ├── __init__.py
    │   │   │   └── entsoe_collector.py
    │   │   ├── config/
    │   │   │   ├── __init__.py
    │   │   │   ├── database.py
    │   │   │   └── settings.py
    │   │   ├── exceptions/
    │   │   │   ├── __init__.py
    │   │   │   ├── collector_exceptions.py
    │   │   │   ├── config_validation_error.py
    │   │   │   ├── processor_exceptions.py
    │   │   │   ├── repository_exceptions.py
    │   │   │   └── service_exceptions.py
    │   │   ├── models/
    │   │   │   ├── __init__.py
    │   │   │   ├── backfill_progress.py
    │   │   │   ├── base.py
    │   │   │   ├── collection_metrics.py
    │   │   │   └── load_data.py
    │   │   ├── processors/
    │   │   │   ├── __init__.py
    │   │   │   ├── base_processor.py
    │   │   │   └── gl_market_document_processor.py
    │   │   ├── repositories/
    │   │   │   ├── __init__.py
    │   │   │   ├── backfill_progress_repository.py
    │   │   │   ├── base_repository.py
    │   │   │   ├── collection_metrics_repository.py
    │   │   │   └── energy_data_repository.py
    │   │   └── services/
    │   │       ├── __init__.py
    │   │       ├── backfill_service.py
    │   │       ├── entsoe_data_service.py
    │   │       ├── monitoring_service.py
    │   │       └── scheduler_service.py
    │   └── tests/
    │       ├── __init__.py
    │       ├── app/
    │       │   ├── __init__.py
    │       │   ├── test_container.py
    │       │   ├── collectors/
    │       │   │   ├── __init__.py
    │       │   │   └── test_entsoe_collector.py
    │       │   ├── config/
    │       │   │   ├── __init__.py
    │       │   │   ├── test_database.py
    │       │   │   └── test_settings.py
    │       │   ├── exceptions/
    │       │   │   ├── __init__.py
    │       │   │   ├── test_collector_exceptions.py
    │       │   │   ├── test_processor_exceptions.py
    │       │   │   └── test_service_exceptions.py
    │       │   ├── models/
    │       │   │   ├── __init__.py
    │       │   │   ├── test_backfill_progress.py
    │       │   │   └── test_load_data.py
    │       │   ├── processors/
    │       │   │   ├── __init__.py
    │       │   │   ├── test_base_processor.py
    │       │   │   └── test_gl_market_document_processor.py
    │       │   ├── repositories/
    │       │   │   ├── __init__.py
    │       │   │   ├── test_backfill_progress_repository.py
    │       │   │   ├── test_base_repository.py
    │       │   │   └── test_energy_data_repository.py
    │       │   └── services/
    │       │       ├── __init__.py
    │       │       ├── test_backfill_service.py
    │       │       ├── test_entsoe_data_service.py
    │       │       ├── test_monitoring_service.py
    │       │       └── test_scheduler_service.py
    │       └── integration/
    │           ├── __init__.py
    │           ├── test_backfill_progress_repository_integration.py
    │           ├── test_backfill_service_integration.py
    │           ├── test_collector_integration.py
    │           ├── test_container_integration.py
    │           ├── test_database.py
    │           ├── test_entsoe_data_service_integration.py
    │           ├── test_monitoring_service_integration.py
    │           ├── test_processor_integration.py
    │           ├── test_repository_integration.py
    │           └── test_scheduler_service_integration.py
    ├── entsoe_client/
    │   ├── README.md
    │   ├── pyproject.toml
    │   ├── .python-version
    │   ├── src/
    │   │   └── entsoe_client/
    │   │       ├── __init__.py
    │   │       ├── container.py
    │   │       ├── py.typed
    │   │       ├── adapters/
    │   │       │   ├── __init__.py
    │   │       │   └── date_time_adapter.py
    │   │       ├── api/
    │   │       │   ├── __init__.py
    │   │       │   └── load_domain_request_builder.py
    │   │       ├── client/
    │   │       │   ├── __init__.py
    │   │       │   ├── default_entsoe_client.py
    │   │       │   ├── entsoe_client.py
    │   │       │   ├── entsoe_client_error.py
    │   │       │   └── entsoe_client_factory.py
    │   │       ├── config/
    │   │       │   ├── __init__.py
    │   │       │   └── settings.py
    │   │       ├── exceptions/
    │   │       │   ├── __init__.py
    │   │       │   ├── config_validation_error.py
    │   │       │   ├── entsoe_api_request_error.py
    │   │       │   ├── entsoe_client_factory_error.py
    │   │       │   ├── load_domain_request_builder_error.py
    │   │       │   ├── unknown_area_code_error.py
    │   │       │   ├── unknown_auction_category_error.py
    │   │       │   ├── unknown_auction_type_error.py
    │   │       │   ├── unknown_business_type_error.py
    │   │       │   ├── unknown_contract_market_agreement_type_error.py
    │   │       │   ├── unknown_curve_type_error.py
    │   │       │   ├── unknown_direction_error.py
    │   │       │   ├── unknown_doc_status_error.py
    │   │       │   ├── unknown_document_type_error.py
    │   │       │   ├── unknown_market_role_type_error.py
    │   │       │   ├── unknown_object_aggregation_error.py
    │   │       │   ├── unknown_process_type_error.py
    │   │       │   └── unknown_psr_type_error.py
    │   │       ├── http_client/
    │   │       │   ├── __init__.py
    │   │       │   ├── exceptions.py
    │   │       │   ├── http_client.py
    │   │       │   ├── httpx_client.py
    │   │       │   └── retry_handler.py
    │   │       └── model/
    │   │           ├── __init__.py
    │   │           ├── common/
    │   │           │   ├── __init__.py
    │   │           │   ├── area_code.py
    │   │           │   ├── area_type.py
    │   │           │   ├── auction_category.py
    │   │           │   ├── auction_type.py
    │   │           │   ├── business_type.py
    │   │           │   ├── contract_market_agreement_type.py
    │   │           │   ├── curve_type.py
    │   │           │   ├── direction.py
    │   │           │   ├── doc_status.py
    │   │           │   ├── document_type.py
    │   │           │   ├── domain_mrid.py
    │   │           │   ├── entsoe_api_request.py
    │   │           │   ├── market_role_type.py
    │   │           │   ├── object_aggregation.py
    │   │           │   ├── process_type.py
    │   │           │   └── psr_type.py
    │   │           └── load/
    │   │               ├── __init__.py
    │   │               ├── gl_market_document.py
    │   │               ├── load_period.py
    │   │               ├── load_point.py
    │   │               ├── load_time_interval.py
    │   │               ├── load_time_series.py
    │   │               └── market_participant_mrid.py
    │   └── tests/
    │       ├── __init__.py
    │       └── entsoe_client/
    │           ├── __init__.py
    │           ├── api/
    │           │   ├── __init__.py
    │           │   └── test_load_domain_request_builder.py
    │           ├── client/
    │           │   ├── __init__.py
    │           │   ├── test_default_entsoe_client.py
    │           │   ├── test_default_entsoe_client_integration.py
    │           │   └── test_entsoe_client_factory.py
    │           ├── config/
    │           │   ├── __init__.py
    │           │   └── test_settings.py
    │           ├── http_client/
    │           │   ├── __init__.py
    │           │   ├── test_httpx_client.py
    │           │   └── test_retry_handler.py
    │           └── model/
    │               ├── __init__.py
    │               ├── common/
    │               │   ├── __init__.py
    │               │   └── test_area_code.py
    │               └── load/
    │                   ├── __init__.py
    │                   └── test_gl_market_document.py
    ├── scripts/
    │   └── init-db/
    │       └── 01-init-timescaledb.sql
    ├── trading_project/
    │   └── __init__.py
    └── .claude/
        └── settings.local.json

---

## TECHNICAL STANDARDS

These principles apply to ALL agents when performing their specialized work:

### Guiding Principles

1. **Maintain Production Quality:** Every piece of code must be robust, efficient, and maintainable. This is a
   production system for energy data trading, and reliability is paramount.
2. **Test-Driven Mentality:** Code without tests is considered incomplete. All new logic requires corresponding tests.
   We have a strong preference for integration tests that validate real-world behavior, especially for I/O operations.
3. **Clarity Through Code, Not Comments:** Follow the standard of "No unnecessary comments." Code should be
   self-documenting. However, this does not mean "no docstrings." **Public-facing classes, methods, and complex business
   logic MUST have comprehensive docstrings** that explain the *why* and the *how*.
4. **Consistency is Key:** Before implementing any new feature, **research the existing codebase**. Replicate
   established patterns (e.g., repository methods, service orchestration, exception handling) to maintain architectural
   consistency. Do not introduce new patterns without a strong justification.
5. **Robust Error Handling:** The project uses a rich hierarchy of custom, domain-specific exceptions. Always catch
   specific exceptions and use exception chaining (`raise NewException from e`) to preserve the full error context.

## Project Structure & Architecture

This is a Python-based energy data trading project using a `uv`-managed monorepo.

- **`energy_data_service/`**: The core service for data collection, processing, and storage.
- **`entsoe_client/`**: A dedicated client library for interacting with the ENTSO-E API.

The `energy_data_service` follows **Clean Architecture principles**. The data flows through distinct, decoupled layers:

1. **Collectors (`app/collectors/`)**: Responsible for fetching raw data from external sources (e.g.,
   `EntsoeCollector`).
2. **Processors (`app/processors/`)**: Transform raw data into our domain models (e.g., `GlMarketDocumentProcessor`
   turns ENTSO-E XML into `EnergyDataPoint` models).
3. **Services (`app/services/`)**: Contain the core business logic and orchestrate the flow (e.g., `EntsoeDataService`
   for gap-filling, `BackfillService` for historical data).
4. **Repositories (`app/repositories/`)**: Abstract all database interactions (e.g., `EnergyDataRepository`,
   `BackfillProgressRepository`).
5. **Models (`app/models/`)**: Define the database schema using SQLAlchemy for our TimescaleDB instance.

## Testing Philosophy: The Cornerstone of Quality

Testing is not optional. We enforce a rigorous testing strategy to ensure reliability in our production energy trading system. Our approach follows the **Testing Pyramid** methodology, which guides us to invest testing effort where it returns the most value while maintaining optimal speed and cost efficiency.

### The Testing Pyramid: Our Foundation

The testing pyramid is a thinking tool that helps us create a balanced, efficient testing strategy. It consists of three main layers, each serving a distinct purpose in our quality assurance process:

```
        /\
       /  \     10% - End-to-End Tests
      /____\    (Complete workflows, user journeys)
     /      \
    /        \  20% - Integration Tests
   /__________\ (Component interactions, database, APIs)
  /            \
 /              \ 70% - Unit Tests
/________________\ (Pure logic, transformations, calculations)
```

### Test Distribution Guidelines

Our target distribution follows industry best practices adapted for energy trading systems:

- **70% Unit Tests**: Fast, isolated tests for business logic and transformations
- **20% Integration Tests**: Component interactions, database operations, service orchestration
- **10% End-to-End Tests**: Complete workflows from data collection to storage and retrieval

### Test Categories and Implementation

#### 1. Unit Tests (`tests/app/`) - Foundation Layer (70%)

**Purpose**: Validate individual components in complete isolation using mocks and stubs.

**What to Test**:
- **Pure Business Logic**: Price calculations, energy consumption formulas, trading algorithms
- **Data Transformations**: ENTSO-E XML parsing, data model conversions, validation rules
- **Individual Methods**: Repository methods, service operations, processor functions
- **Error Handling**: Exception scenarios, edge cases, boundary conditions

**Examples**:
```python
# Energy price calculation logic
def test_calculate_hourly_average_price()

# Data validation and transformation
def test_transform_entsoe_xml_to_energy_data_point()

# Business rule validation
def test_validate_trading_window_constraints()
```

#### 2. Integration Tests (`tests/integration/`) - Middle Layer (20%)

**Purpose**: Validate component interactions and external dependencies using real database and mocked external APIs.

**What to Test**:
- **Database Operations**: TimescaleDB hypertable interactions, time-series queries, data persistence
- **Service Orchestration**: BackfillService coordination, data collection pipelines, dependency injection
- **Repository Patterns**: Complex queries, transaction handling, data integrity
- **Component Interactions**: Collector → Processor → Repository workflows

**Key Features**:
- **Real TimescaleDB**: Using Testcontainers for authentic database testing
- **Mocked External APIs**: ENTSO-E client calls stubbed for reliability
- **Full Dependency Injection**: Testing complete container resolution

**Examples**:
```python
# Complete data collection workflow
def test_collect_process_store_energy_data_integration()

# Backfill service with real database
def test_backfill_service_resume_operation_integration()

# Repository complex queries
def test_energy_data_repository_time_range_queries()
```

#### 3. End-to-End Tests (Future Implementation) - Top Layer (10%)

**Purpose**: Validate complete user workflows and system behavior from external perspective.

**What to Test**:
- **Complete Data Pipelines**: From external API to database storage and retrieval
- **Scheduler Operations**: Automated data collection cycles, backfill processes
- **System Recovery**: Failure scenarios, restart behavior, data consistency
- **Performance Under Load**: High-volume data scenarios, concurrent operations

**Implementation Strategy**:
- Run against staging environment with production-like data volumes
- Include real ENTSO-E API calls (rate-limited for testing)
- Validate data quality and completeness over time windows

### Test Execution Strategy

#### Development Workflow
```bash
# Fast feedback loop during development (< 5 seconds)
uv run pytest tests/app/ -x --ff

# Pre-commit validation (< 2 minutes)
uv run pytest tests/app/ tests/integration/

# Full test suite (< 5 minutes)
uv run pytest
```

### Anti-Patterns to Avoid

#### The Ice Cream Cone (Inverted Pyramid)
Never prioritize slow E2E tests over fast unit tests. This leads to:
- Slow feedback loops during development
- Expensive test maintenance
- Brittle test suites that break frequently

#### Over-Mocking in Integration Tests
While unit tests should mock extensively, integration tests should use real dependencies where possible:
- Use real TimescaleDB instances (via Testcontainers)
- Mock only external APIs that are unreliable or rate-limited
- Prefer fakes over mocks for internal dependencies

#### Testing Implementation Details
Focus on behavior, not implementation:
- Test public interfaces, not private methods
- Validate outcomes, not internal state changes
- Write tests that survive refactoring

### Quality Metrics and Coverage

#### Coverage Targets
- **Unit Tests**: 90%+ coverage of pure business logic
- **Integration Tests**: 100% of critical data paths
- **Overall**: 85%+ total coverage (prioritize quality over percentage)

#### Quality Over Quantity
- High coverage percentage is valuable, but test quality is paramount
- Focus on testing critical business logic and error scenarios
- Avoid writing tests just to increase coverage metrics

### Testing Tools and Infrastructure

#### Primary Testing Stack
- **pytest**: Primary testing framework with extensive plugin ecosystem
- **pytest-asyncio**: For testing async/await patterns in collectors and services
- **Testcontainers**: Real TimescaleDB instances for integration testing
- **pytest-benchmark**: Performance regression detection
- **pytest-cov**: Coverage reporting and analysis

#### Development Tools
- **pytest-xdist**: Parallel test execution for faster feedback
- **pytest-mock**: Enhanced mocking capabilities
- **pytest-factoryboy**: Test data generation for complex models

### Running Tests

```bash
# Run all tests (unit and integration)
uv run pytest

# Run only integration tests
uv run pytest tests/integration/

# Run only unit tests for the application logic
uv run pytest tests/app/

# Run a specific test file or function
uv run pytest tests/app/services/test_backfill_service.py::TestBackfillService::test_resume_backfill_success
```

## Code Standards & Key Patterns

Adhere strictly to these patterns. Research them in the codebase before writing new code.

1. **Full Type Safety (mypy --strict)**: All code must be fully type-annotated. There are no exceptions. Our `mypy.ini`
   is configured for strict mode.

2. **Dependency Injection**: All dependencies are managed through the `dependency-injector` container (
   `app/container.py`). Components receive their dependencies via constructor injection. **Never instantiate a
   dependency directly** (e.g., `repo = EnergyDataRepository(db)`). Instead, resolve it from the container.

3. **Repository Pattern**: All database access is funneled through repository classes that inherit from the generic
   `BaseRepository[ModelType]`. This abstracts away the database, provides a consistent interface for data access, and
   centralizes query logic.
    - **Base Class**: `app/repositories/base_repository.py`
    - **Examples**: `EnergyDataRepository`, `BackfillProgressRepository`

4. **Robust Error Handling**: We have a detailed custom exception hierarchy. Use the most specific exception possible
   and always chain them.
    - `app/exceptions/collector_exceptions.py`: For data fetching errors.
    - `app/exceptions/processor_exceptions.py`: For data transformation errors.
    - `app/exceptions/repository_exceptions.py`: For database errors.
    - `app/exceptions/service_exceptions.py`: For business logic errors.
    - **Golden Rule**: Always use `raise CustomException(...) from original_exception`.

5. **Self-Documenting Code & Docstrings**: Avoid explanatory comments (`# This loop does...`). Instead, write clean
   code. **Provide detailed docstrings for all public classes and methods**, explaining their purpose, arguments, and
   what they return, following the existing style.

## Development Workflow: A Step-by-Step Guide

Follow this process for every contribution to ensure quality and consistency.

1. **Research First**: Before writing a line of code, review existing services, repositories, and tests to understand
   the established patterns.
2. **Write/Update Tests First**: Add or update tests in `tests/integration/` or `tests/app/` that cover your changes.
   Your new tests should initially fail.
3. **Implement the Logic**: Write your implementation, ensuring it is fully type-annotated and adheres to the Clean
   Architecture layers. Your goal is to make the tests pass.
4. **Write Docstrings**: Add comprehensive docstrings to any new public classes or methods you've created.
5. **Run Quality Checks**: Before committing, run all checks to fix formatting, linting, and type errors.
   ```bash
   pre-commit run --all-files
   ```
6. **Commit**: Write a clear and descriptive commit message.

## Core Commands

### Environment Setup

```bash
# Install all dependencies from uv.lock
uv sync

# Activate the virtual environment managed by uv
# (uv automatically handles this when using `uv run`)
```

### Running Code

```bash
# Always use `uv run` to ensure you're using the project's environment
uv run python <path_to_script.py>
uv run pytest
```

### Database

```bash
# Start a local TimescaleDB instance for development
docker-compose up -d timescaledb

# Connect using credentials from your local .env file
# (DB_NAME, DB_USER, DB_PASSWORD, DB_PORT)
```
