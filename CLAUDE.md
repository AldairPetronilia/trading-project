# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

This is a Python-based trading project focused on ENTSO-E (European Network of Transmission System Operators for Electricity) data collection and processing. The repository contains two main components:

### Components

1. **entsoe_client/** - Python client library (Python 3.13+)
   - Pydantic models with XML support via pydantic-xml
   - Type-safe data structures and validation
   - Part of uv workspace configuration
   - Clean architecture with dependency injection using `dependency-injector`
   - Comprehensive exception hierarchy for domain-specific errors
   - HTTP client abstraction with retry handling using tenacity

2. **energy_data_service/** - Python data service (Python 3.13+)
   - Professional data service for energy trading signals
   - Depends on the entsoe_client workspace member
   - MVP architecture with collectors, processors, and repositories
   - Designed for GL_MarketDocument processing and time-series data storage

## Development Commands

### Database Infrastructure
```bash
# Start TimescaleDB database
docker-compose up -d timescaledb

# View database logs
docker-compose logs -f timescaledb

# Connect to database
docker-compose exec timescaledb psql -U energy_user -d energy_data_service

# Stop database
docker-compose down

# Check database status
docker-compose ps
```

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

# IMPORTANT: Always use 'uv run python' instead of 'python' directly
# This ensures proper virtual environment and dependency resolution
```

### Energy Data Service Commands

```bash
# The energy_data_service is currently in early development
# Check the MVP_ARCHITECTURE.md for planned architecture
cd energy_data_service

# Once implemented, it will likely use:
# uv run python -m energy_data_service.app.main
```

## Code Quality Tools

- **Python**: Configured with ruff, black, mypy, and pre-commit hooks
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

### Python Components
- Pydantic models for data validation and serialization
- Type hints required for all functions and methods
- Async/await patterns in data service components
- Custom exception hierarchy for domain-specific errors
- **Dependency injection**: Using `dependency-injector` library with Factory providers
- **Error handling**: Exception chaining with `raise ... from e` to preserve context
- **HTTP client architecture**: Abstract base classes with proper async patterns

## Testing

- **Python**: pytest for all testing needs
- Integration tests exist for ENTSO-E API interactions
- Test data includes XML samples and fixtures

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

### ENTSO-E Client (`entsoe_client/`)
The Python client library workspace member contains:

- **Source code**: `src/entsoe_client/` - Main implementation
- **Tests**: `tests/` - Test suite with integration tests
- **Configuration**: `pyproject.toml` - Project dependencies and metadata

Key files for understanding the architecture:
- `src/entsoe_client/container.py` - Dependency injection container setup
- `src/entsoe_client/config/settings.py` - Configuration with Pydantic Settings
- `src/entsoe_client/client/default_entsoe_client.py` - Main client implementation
- `src/entsoe_client/http_client/httpx_client.py` - HTTP client with retry handling
- `tests/entsoe_client/client/test_default_entsoe_client_integration.py` - Integration tests

### Energy Data Service (`energy_data_service/`)
The data service workspace member is in early development:

- **Architecture**: See `MVP_ARCHITECTURE.md` for planned structure
- **Current state**: Basic project structure with minimal implementation
- **Dependencies**: Uses `entsoe_client` as a workspace dependency
- **Future**: Will implement collectors, processors, and repositories for GL_MarketDocument processing

## Database Infrastructure

The project uses **TimescaleDB** (PostgreSQL extension) for time-series data storage:

### Database Configuration
- **Service**: TimescaleDB running in Docker container
- **Database**: `energy_data_service`
- **User**: `energy_user`
- **Port**: 5432 (mapped to host)
- **Data Storage**: `./data/timescaledb/` (local bind mount for persistence)

### Database Files
- **`docker-compose.yml`**: TimescaleDB service configuration with health checks
- **`.env`**: Database credentials and connection settings
- **`scripts/init-db/01-init-timescaledb.sql`**: Minimal initialization (TimescaleDB extension only)
- **`data/`**: Local database storage directory (ignored by git except `.gitkeep`)

### Database Features
- **Data Persistence**: Survives container restarts via local bind mount
- **TimescaleDB Extension**: Automatically created on first startup
- **Health Checks**: Ensures database ready before application starts
- **Minimal Setup**: Only extension creation in init script - tables created programmatically

### Database Workflow
1. **Start**: `docker-compose up -d timescaledb`
2. **Connect**: `docker-compose exec timescaledb psql -U energy_user -d energy_data_service`
3. **Application**: Creates tables via SQLAlchemy models and Alembic migrations
4. **Data**: Persists in `./data/timescaledb/` between container restarts

## Important Configuration Files

- **Root `pyproject.toml`**: Defines uv workspace and dev dependencies
- **`docker-compose.yml`**: TimescaleDB service and network configuration
- **`.env`**: Database credentials and application settings
- **`ruff.toml`**: Comprehensive linting rules with per-file ignores
- **`mypy.ini`**: Strict type checking configuration
- **Individual `pyproject.toml`**: Component-specific dependencies

## Development Best Practices

### Command Usage
- **ALWAYS use `uv run python` instead of `python` directly**
  - This ensures proper virtual environment and dependency resolution
  - Examples: `uv run python debug_script.py`, `uv run python -m pytest`
  - Common mistake: Running `python script.py` can lead to import errors or wrong dependencies

### Debugging Techniques
- **Create temporary debugging files** to understand complex behavior
  - Example: Create `debug_paths.py` to check file path resolution
  - Example: Create `debug_config.py` to test configuration loading
  - Example: Create `debug_nested.py` to understand nested object behavior
- **Use debugging scripts to:**
  - Verify file paths and existence
  - Test configuration loading with different scenarios
  - Understand how libraries behave in practice vs. documentation
  - Debug complex data structures and nested objects
- **Clean up debugging files** after use to keep repository clean
- **Document findings** in comments or CLAUDE.md for future reference
