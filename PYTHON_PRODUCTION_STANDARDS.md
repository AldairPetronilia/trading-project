# Python Production Quality Standards

This document outlines the production quality standards for Python files in the trading project. These standards ensure consistency, maintainability, and reliability across the codebase.

## 1. No Unnecessary Comments

**Standard**: Code should be self-documenting through clear variable names, function names, and structure. Comments are only added when absolutely necessary to explain complex business logic or non-obvious implementation decisions.

**✅ Good Example**:
```python
async def get_actual_total_load(
    self,
    bidding_zone: AreaCode,
    period_start: datetime,
    period_end: datetime,
    offset: int | None = None,
) -> GlMarketDocument:
    request_builder = LoadDomainRequestBuilder(
        out_bidding_zone_domain=bidding_zone,
        period_start=period_start,
        period_end=period_end,
        offset=offset,
    )
    request = request_builder.build_actual_total_load()
    return await self._execute_request(request)
```

**❌ Bad Example**:
```python
async def get_actual_total_load(
    self,
    bidding_zone: AreaCode,  # The bidding zone to query
    period_start: datetime,  # Start of the time period
    period_end: datetime,    # End of the time period
    offset: int | None = None,  # Optional offset parameter
) -> GlMarketDocument:  # Returns market document
    # Create a request builder with the provided parameters
    request_builder = LoadDomainRequestBuilder(
        out_bidding_zone_domain=bidding_zone,
        period_start=period_start,
        period_end=period_end,
        offset=offset,
    )
    # Build the actual total load request
    request = request_builder.build_actual_total_load()
    # Execute the request and return the result
    return await self._execute_request(request)
```

## 2. Dependency Injection

**Standard**: Use the `dependency-injector` library with declarative containers. All dependencies should be injected rather than created directly within classes.

**✅ Good Example**:
```python
# Container definition
class Container(containers.DeclarativeContainer):
    config = providers.Singleton(EntsoEClientConfig)

    retry_handler = providers.Factory(
        RetryHandler,
        config=config.provided.retry,
    )

    http_client = providers.Factory(
        HttpxClient,
        config=config,
        retry_handler=retry_handler,
    )

# Class with injected dependencies
class DefaultEntsoEClient(EntsoEClient):
    def __init__(self, http_client: HttpClient, base_url: str) -> None:
        self.http_client = http_client
        self.base_url = base_url
```

**❌ Bad Example**:
```python
class DefaultEntsoEClient(EntsoEClient):
    def __init__(self, api_key: str, base_url: str) -> None:
        # Direct instantiation - violates DI principle
        self.config = EntsoEClientConfig(api_key=api_key)
        self.retry_handler = RetryHandler(self.config.retry)
        self.http_client = HttpxClient(self.config, self.retry_handler)
        self.base_url = base_url
```

## 3. Docstrings When Needed

**Standard**: Add docstrings for public APIs, complex business logic, abstract methods, and classes. Use Google/Sphinx style formatting.

**✅ Good Example**:
```python
class BaseRepository[ModelType](ABC):
    """Abstract base repository providing common CRUD operations with database session management.

    This repository implements the Repository pattern with:
    - Generic type support for type-safe operations
    - Async database session management with automatic commit/rollback
    - Comprehensive exception handling with proper error context
    - Batch operations for high-performance data processing
    - Production-ready error handling and logging
    """

    async def create(self, model: ModelType) -> ModelType:
        """Create a new record in the database.

        Args:
            model: The model instance to create

        Returns:
            The created model with any database-generated fields populated

        Raises:
            DuplicateDataError: If a unique constraint is violated
            DataValidationError: If the model data is invalid
            DataAccessError: If the database operation fails
        """
```

**✅ When NOT to add docstrings**:
```python
def _get_model_name(self) -> str:
    return "Model"

async def close(self) -> None:
    if self.http_client:
        await self.http_client.close()
```

## 4. Full Type Safety

**Standard**: All functions and methods must have complete type annotations. Follow mypy strict configuration.

**Configuration**: Based on `mypy.ini`:
```ini
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
```

**✅ Good Example**:
```python
async def create_batch(self, models: list[ModelType]) -> list[ModelType]:
    if not models:
        return []

    async with self.database.session_factory() as session:
        try:
            session.add_all(models)
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            raise DataAccessError("Database error") from e
        else:
            return models

def __init__(self, database: Database) -> None:
    self.database = database
```

**❌ Bad Example**:
```python
async def create_batch(self, models):  # Missing type hints
    if not models:
        return []

    async with self.database.session_factory() as session:
        session.add_all(models)
        await session.commit()
        return models

def __init__(self, database):  # Missing type hints
    self.database = database
```

## 5. Code Quality Tools

**Standard**: Use pre-commit hooks for all quality checks. Run `pre-commit run --all-files` instead of individual tools.

**Tools Configuration**:
- **ruff**: Comprehensive linting with 88 character line length
- **black**: Code formatting with 88 character line length
- **mypy**: Strict type checking
- **pre-commit**: Automated quality checks

**Key ruff Rules**:
- `SIM117`: Combine nested `with` statements
- `B904`: Use `raise ... from err` for exception chaining
- `TRY003`: Avoid long exception messages
- `EM101`: Don't use string literals directly in exceptions

**✅ Good Example**:
```python
# Combined with statements (SIM117)
async with self.database.session_factory() as session:
    try:
        session.add(model)
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        error_msg = f"Failed to create {model_name}: database error"
        raise DataAccessError(error_msg) from e  # B904: Exception chaining
```

## 6. Error Handling

**Standard**: Use exception chaining with `raise ... from e` to preserve error context. Create domain-specific exception hierarchies.

**✅ Good Example**:
```python
try:
    xml_response = await self.http_client.get(self.base_url, query_params)
    return self._parse_xml_response(xml_response)
except HttpClientError as e:
    logger.exception("HTTP request failed for request: %s", request)
    raise EntsoEClientError.http_request_failed(e) from e
except Exception as e:
    logger.exception("XML parsing failed")
    raise EntsoEClientError.xml_parsing_failed(e) from e
```

**❌ Bad Example**:
```python
try:
    xml_response = await self.http_client.get(self.base_url, query_params)
    return self._parse_xml_response(xml_response)
except Exception as e:
    # Lost error context, no chaining
    raise EntsoEClientError("Request failed")
```

## 7. Async Patterns

**Standard**: Use proper async/await patterns for I/O operations. Handle async context managers correctly.

**✅ Good Example**:
```python
async def create(self, model: ModelType) -> ModelType:
    async with self.database.session_factory() as session:
        try:
            session.add(model)
            await session.flush()
            await session.refresh(model)
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            raise DataAccessError("Database error") from e
        else:
            return model

async def close(self) -> None:
    if self.http_client:
        await self.http_client.close()
```

## 8. Testing Standards

**Standard**: Use pytest with asyncio support. Mock external dependencies. Test error conditions.

**✅ Good Example**:
```python
@pytest.mark.asyncio
async def test_create_model_success() -> None:
    mock_database = AsyncMock(spec=Database)
    mock_session = AsyncMock()
    mock_database.session_factory.return_value.__aenter__.return_value = mock_session

    repository = ConcreteRepository(mock_database)
    model = SampleModel(name="test")

    result = await repository.create(model)

    mock_session.add.assert_called_once_with(model)
    mock_session.commit.assert_called_once()
    assert result == model

@pytest.mark.asyncio
async def test_create_model_integrity_error() -> None:
    mock_database = AsyncMock(spec=Database)
    mock_session = AsyncMock()
    mock_session.flush.side_effect = IntegrityError("", "", "")
    mock_database.session_factory.return_value.__aenter__.return_value = mock_session

    repository = ConcreteRepository(mock_database)
    model = SampleModel(name="test")

    with pytest.raises(DuplicateDataError):
        await repository.create(model)

    mock_session.rollback.assert_called_once()
```

## 9. Architecture Patterns

**Standard**: Follow clean architecture principles with clear separation of concerns.

**Patterns Used**:
- **Repository Pattern**: Abstract data access with `BaseRepository`
- **Factory Pattern**: Create objects through dependency injection
- **Command Pattern**: Encapsulate requests as objects (`EntsoEApiRequest`)
- **Strategy Pattern**: Different retry strategies, HTTP clients

**✅ Good Example Structure**:
```
src/
├── client/                 # Application layer
├── http_client/           # Infrastructure layer
├── model/                 # Domain layer
├── exceptions/            # Domain exceptions
├── config/               # Configuration layer
└── container.py          # DI container
```

## 10. Performance Considerations

**Standard**: Optimize for production performance while maintaining code clarity.

**✅ Good Practices**:
```python
# Batch operations for database efficiency
async def create_batch(self, models: list[ModelType]) -> list[ModelType]:
    if not models:
        return []

    async with self.database.session_factory() as session:
        session.add_all(models)  # Single batch operation
        await session.flush()
        for model in models:
            await session.refresh(model)
        await session.commit()
        return models

# Resource cleanup
async def close(self) -> None:
    if self.http_client:
        await self.http_client.close()
```

## Development Workflow

1. **Code Quality**: Always run `pre-commit run --all-files` before commits
2. **Testing**: Use `uv run pytest` for all test execution
3. **Type Checking**: Ensure mypy passes with strict configuration
4. **Dependencies**: Always use `uv run python` instead of `python` directly
5. **Database**: Use `docker-compose up -d timescaledb` for local development

## Enforcement

These standards are enforced through:
- **Pre-commit hooks**: Automated quality checks
- **CI/CD**: All checks must pass before merge
- **Code Reviews**: Manual verification of patterns and standards
- **mypy**: Strict type checking in CI
- **pytest**: Comprehensive test coverage requirements

Following these standards ensures consistent, maintainable, and production-ready Python code across the trading project.
