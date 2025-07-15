# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

This is a multi-language trading project focused on ENTSO-E (European Network of Transmission System Operators for Electricity) data collection and processing. The repository contains three main components:

### Components

1. **entsoe-client/** - Java 21 client library for ENTSO-E API
   - Clean architecture with manual dependency injection
   - Uses Lombok, JAXB for XML parsing, SLF4J for logging
   - Emphasizes immutability and clean code principles

2. **energy-data-service/** - Spring Boot web service (Java 24)
   - HTTP client configuration and API endpoints
   - Uses Spring Boot, Lombok, Jakarta validation

3. **entsoe_client/** - Python client library (Python 3.13+)
   - Pydantic models with XML support via pydantic-xml
   - Type-safe data structures and validation
   - Part of uv workspace configuration
   - Clean architecture with dependency injection using `dependency-injector`
   - Comprehensive exception hierarchy for domain-specific errors
   - HTTP client abstraction with retry handling using tenacity

4. **energy_data_service/** - Python data service (Python 3.13+)
   - Async HTTP client using aiohttp
   - Data collection and processing pipeline

## Development Commands

### Python Components (uv workspace)
```bash
# Install dependencies for all workspace members
uv sync

# Run Python tests (requires pytest-asyncio for async tests)
uv run pytest entsoe_client/tests/
uv run pytest                           # Run all tests in workspace

# Run specific test file
uv run pytest entsoe_client/tests/entsoe_client/client/test_default_entsoe_client_integration.py

# Code quality (RECOMMENDED: use pre-commit instead of individual commands)
pre-commit run --all-files              # Run all quality checks
pre-commit run                          # Run on staged files only

# Individual quality tools (alternative to pre-commit)
uv run mypy .                           # Type checking
uv run ruff check                       # Linting
uv run ruff format                      # Ruff formatting
uv run black .                          # Black formatting

# Run specific Python service
uv run python energy_data_service/app/main.py
```

### Java Components

#### ENTSO-E Client (entsoe-client/)
```bash
cd entsoe-client
./gradlew build
./gradlew test
./gradlew spotlessCheck    # Check code formatting
./gradlew spotlessApply    # Apply code formatting
```

#### Energy Data Service (energy-data-service/)
```bash
cd energy-data-service
./gradlew build
./gradlew test
./gradlew bootRun         # Run Spring Boot application
```

## Code Quality Tools

- **Python**: Configured with ruff, black, mypy, and pre-commit hooks
- **Java**: Uses Spotless with Google Java Format for consistent styling
- **Type Safety**: mypy for Python with strict configuration, full type annotations required

### Pre-commit Hooks (Recommended)
The project uses pre-commit hooks to ensure code quality. **Use `pre-commit run --all-files` instead of running individual tools** like mypy and ruff separately.

Configured hooks:
- **black**: Code formatting with 88 character line length
- **ruff**: Linting with auto-fix enabled
- **ruff-format**: Additional formatting checks
- **mypy**: Type checking with strict configuration
- **Standard hooks**: trailing-whitespace, end-of-file-fixer, check-yaml, etc.

```bash
# Install pre-commit hooks (run once)
pre-commit install

# Run all quality checks on all files (preferred method)
pre-commit run --all-files

# Run pre-commit on staged files only
pre-commit run
```

### Important ruff Rules
- `SIM117`: Combine nested `with` statements instead of nesting them
- `B904`: Use `raise ... from err` for exception chaining to preserve context
- `TRY003`: Avoid long exception messages, keep them concise
- `EM101`: Don't use string literals directly in exceptions, assign to variable first

### mypy Configuration
- Global configuration in `mypy.ini` with strict typing enabled
- Test-specific overrides: `[mypy-tests.*]` section allows `disallow_untyped_decorators = false`
- Untyped decorator warnings from pytest fixtures are handled via configuration

## Key Patterns

### Java Components
- Constructor-based dependency injection (no DI framework)
- Immutable data objects using Lombok `@Value`
- Builder patterns for complex request objects
- XML processing with JAXB adapters

### Python Components
- Pydantic models for data validation and serialization
- Type hints required for all functions and methods
- Async/await patterns in data service components
- Custom exception hierarchy for domain-specific errors
- **Dependency injection**: Using `dependency-injector` library with Factory providers
- **Error handling**: Exception chaining with `raise ... from e` to preserve context
- **HTTP client architecture**: Abstract base classes with proper async patterns

## Testing

- **Java**: JUnit 5 with Mockito and AssertJ
- **Python**: pytest for all testing needs
- Integration tests exist for ENTSO-E API interactions
- Test data includes XML samples in `entsoe-client/src/test/resources/loadXmls/`

### Python Testing Best Practices
- **pytest-asyncio**: Required for testing async functions with `@pytest.mark.asyncio`
- **Async mocking**: Use `AsyncMock` for async operations, `patch()` for external dependencies
- **Test fixtures**: Use `@pytest.fixture` for reusable test setup and dependency injection
- **Exception testing**: Use `pytest.raises()` to verify expected exceptions are raised
- **Context managers**: Use `with patch(), pytest.raises():` instead of nested `with` statements
- **Return type annotations**: All test methods should have `-> None` return type annotation

### Key Testing Dependencies
- **tenacity**: Async retry library for robust HTTP request handling
- **types-pytest**: Type stubs for pytest to satisfy mypy strict typing
- **pytest-asyncio**: Plugin for async test support with proper event loop handling

## Working Directory Context

When working in the `entsoe_client/` directory, you're in the Python client library workspace member. This directory contains:

- **Source code**: `src/entsoe_client/` - Main implementation
- **Tests**: `tests/` - Test suite with integration tests
- **Configuration**: `pyproject.toml` - Project dependencies and metadata

Key files for understanding the architecture:
- `src/entsoe_client/container.py` - Dependency injection container setup
- `src/entsoe_client/config/settings.py` - Configuration with Pydantic Settings
- `src/entsoe_client/client/default_entsoe_client.py` - Main client implementation
- `src/entsoe_client/http/httpx_client.py` - HTTP client with retry handling
- `tests/entsoe_client/client/test_default_entsoe_client_integration.py` - Integration tests

## Important Configuration Files

- **Root `pyproject.toml`**: Defines uv workspace and dev dependencies
- **`ruff.toml`**: Comprehensive linting rules with per-file ignores
- **`mypy.ini`**: Strict type checking configuration
- **Individual `pyproject.toml`**: Component-specific dependencies
