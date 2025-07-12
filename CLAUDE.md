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

4. **energy_data_service/** - Python data service (Python 3.13+)
   - Async HTTP client using aiohttp
   - Data collection and processing pipeline

## Development Commands

### Python Components (uv workspace)
```bash
# Install dependencies for all workspace members
uv sync

# Run Python tests
uv run pytest entsoe_client/tests/

# Type checking
uv run mypy .

# Linting and formatting
uv run ruff check
uv run ruff format
uv run black .

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

## Testing

- **Java**: JUnit 5 with Mockito and AssertJ
- **Python**: pytest for all testing needs
- Integration tests exist for ENTSO-E API interactions
- Test data includes XML samples in `entsoe-client/src/test/resources/loadXmls/`
