# Current Implementation Plan - BackfillProgressRepository

## Next Atomic Step: Implement BackfillProgressRepository Pattern

Based on the completed Service Orchestration Layer, the next step is implementing a proper repository pattern for BackfillProgress operations to resolve technical debt and improve architectural consistency.

### What to implement next:

1. **BackfillProgressRepository** (`app/repositories/backfill_progress_repository.py`)
   - Inherit from BaseRepository[BackfillProgress] for type safety
   - Implement required abstract methods (get_by_id, get_all, delete)
   - Add specialized query methods for backfill operations
   - Provide clean session management without cross-session object issues

2. **BackfillService Refactoring** (`app/services/backfill_service.py`)
   - Replace direct database operations with repository calls
   - Remove session.merge() workaround for cross-session objects
   - Add backfill_progress_repository dependency injection
   - Maintain existing business logic while improving data access layer

3. **Container Integration** (`app/container.py`)
   - Add BackfillProgressRepository provider using Factory pattern
   - Update BackfillService provider with new repository dependency
   - Maintain proper dependency injection chain

4. **Test Suite Implementation** (`tests/app/repositories/test_backfill_progress_repository.py`)
   - Unit tests for all repository operations with mocked sessions
   - Integration tests with real database operations
   - Error handling and edge case coverage
   - Performance testing for specialized queries

### Implementation Requirements:

#### BackfillProgressRepository Features:
- **Core CRUD Operations**: Implement get_by_id, get_all, delete methods from BaseRepository
- **Specialized Queries**: get_active_backfills() for pending/in_progress operations
- **Area/Endpoint Filtering**: get_by_area_endpoint() for targeted backfill queries
- **Resumable Operations**: get_resumable_backfills() for failed operations with progress
- **Progress Updates**: update_progress_by_id() with fresh object query pattern
- **Session Management**: Proper async session handling without cross-session object attachment

#### BackfillService Refactoring Features:
- **Repository Integration**: Replace _save_progress() direct database calls with repository.create/update
- **Load Operations**: Replace _load_backfill_progress() with repository.get_by_id()
- **Active Backfills**: Replace list_active_backfills() queries with repository.get_active_backfills()
- **Constructor Updates**: Add progress_repository dependency parameter
- **Error Handling**: Propagate repository exceptions through service layer
- **Session Elimination**: Remove direct database session management for progress operations

#### Container Integration Features:
- **Provider Registration**: Add backfill_progress_repository Factory provider
- **Dependency Chain**: Settings ’ Database ’ BackfillProgressRepository ’ BackfillService
- **Service Updates**: Update backfill_service provider with progress_repository parameter
- **Scoping Consistency**: Follow existing singleton/factory patterns
- **Type Safety**: Maintain proper generic type annotations
- **Lifecycle Management**: Proper resource cleanup through dependency injection

### Test Coverage Requirements:

1. **BackfillProgressRepository Unit Tests** (`tests/app/repositories/test_backfill_progress_repository.py`)
   - Test all CRUD operations with mocked async sessions
   - Test specialized query methods (active, resumable, by area/endpoint)
   - Test error handling scenarios (database errors, constraint violations)
   - Test batch operations and transaction boundaries

2. **BackfillService Unit Tests Updates** (`tests/app/services/test_backfill_service.py`)
   - Mock progress_repository dependency instead of direct database
   - Verify repository method calls (create, update, get_by_id)
   - Test error propagation from repository to service layer
   - Maintain existing business logic test coverage

3. **Container Unit Tests Updates** (`tests/app/test_container.py`)
   - Test BackfillProgressRepository provider registration
   - Test BackfillService provider with new repository dependency
   - Test dependency resolution chain
   - Test configuration injection

4. **BackfillProgressRepository Integration Tests** (`tests/integration/test_backfill_progress_repository_integration.py`)
   - Real TimescaleDB operations with testcontainers
   - Test concurrent repository operations
   - Test transaction isolation and rollback scenarios
   - Test performance of specialized queries with real data

5. **BackfillService Integration Tests Updates** (`tests/integration/test_backfill_service_integration.py`)
   - Update tests to use real BackfillProgressRepository instead of direct database
   - Verify end-to-end functionality with repository pattern
   - Maintain existing comprehensive integration test coverage
   - Test session management improvements

### Dependencies:

- Builds on existing BaseRepository from `app/repositories/base_repository.py`
- Uses BackfillProgress model from `app/models/backfill_progress.py`
- Uses Database class from `app/config/database.py`
- Uses repository exception hierarchy from `app/exceptions/repository_exceptions.py`
- Integration with existing Container patterns from `app/container.py`
- Follows established patterns from EnergyDataRepository implementation

### Success Criteria:

- **Technical Debt Resolution**: Eliminates session.merge() workaround and cross-session object attachment issues
- **Testing Coverage**: Comprehensive unit and integration tests with 95%+ coverage for new repository
- **Integration Success**: All existing BackfillService integration tests pass with repository pattern
- **Performance Maintenance**: Repository operations perform equally or better than direct database calls
- **Error Handling Consistency**: Repository exceptions properly propagate through service layer with context
- **Code Quality Compliance**: Passes all checks (ruff, mypy, pre-commit) with zero type errors
- **Architecture Consistency**: Follows established repository patterns from EnergyDataRepository
- **Pattern Consistency**: Maintains clean separation between service logic and data access operations

This BackfillProgressRepository implementation resolves documented technical debt while establishing proper repository pattern consistency needed for the upcoming API Layer implementation.

---

## Further Implementation Details

### = **Current Technical Debt Analysis**

#### **Root Cause of Issues:**
The BackfillService currently contains a critical technical debt issue documented in the MVP architecture:

**Problem Location**: `app/services/backfill_service.py:722-733` (`_save_progress` method)

**Current Problematic Code:**
```python
async def _save_progress(self, progress: BackfillProgress) -> None:
    async for session in self._database.get_database_session():
        if progress.id:
            #   WORKAROUND: Using merge() to handle cross-session objects
            await session.merge(progress)  # This is inefficient and architectural debt
        else:
            session.add(progress)
        await session.commit()
```

**Why This is Technical Debt:**
1. **Cross-Session Object Attachment**: BackfillProgress objects are reused across multiple database sessions
2. **SQLAlchemy "Already Attached" Errors**: Objects become attached to one session but used in another
3. **Performance Overhead**: `session.merge()` is less efficient than proper session-scoped operations
4. **Architectural Inconsistency**: Breaks the established repository pattern used elsewhere

### =à **Detailed Repository Implementation Strategy**

#### **Session Management Solution:**
Instead of reusing objects across sessions, the repository will:

**Current Problematic Pattern:**
```python
# L WRONG: Reuse object across sessions
progress = BackfillProgress(...)  # Created in one context
# ... object gets attached to session A
# Later used in different session B - causes conflicts
await session.merge(progress)  # Workaround but inefficient
```

**New Repository Pattern:**
```python
#  CORRECT: Fresh queries in current session
async def update_progress_by_id(self, backfill_id: int, **updates) -> BackfillProgress:
    async with self.database.session_factory() as session:
        # Query fresh object in current session
        stmt = select(BackfillProgress).where(BackfillProgress.id == backfill_id)
        progress = await session.execute(stmt).scalar_one_or_none()

        if progress:
            # Update fields directly on session-attached object
            for field, value in updates.items():
                setattr(progress, field, value)
            await session.commit()
            await session.refresh(progress)
        return progress
```

#### **Specialized Repository Methods:**

```python
class BackfillProgressRepository(BaseRepository[BackfillProgress]):

    async def get_active_backfills(self) -> list[BackfillProgress]:
        """Get all pending/in_progress backfills."""
        async with self.database.session_factory() as session:
            stmt = select(BackfillProgress).where(
                BackfillProgress.status.in_([
                    BackfillStatus.PENDING,
                    BackfillStatus.IN_PROGRESS
                ])
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_resumable_backfills(self) -> list[BackfillProgress]:
        """Get backfills that can be resumed (failed/pending with progress)."""
        async with self.database.session_factory() as session:
            stmt = select(BackfillProgress).where(
                and_(
                    BackfillProgress.status.in_([
                        BackfillStatus.FAILED,
                        BackfillStatus.PENDING
                    ]),
                    BackfillProgress.completed_chunks > 0
                )
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_by_area_endpoint(
        self, area_code: str, endpoint_name: str
    ) -> list[BackfillProgress]:
        """Get backfills for specific area/endpoint combination."""
        async with self.database.session_factory() as session:
            stmt = select(BackfillProgress).where(
                and_(
                    BackfillProgress.area_code == area_code,
                    BackfillProgress.endpoint_name == endpoint_name
                )
            ).order_by(desc(BackfillProgress.created_at))
            result = await session.execute(stmt)
            return list(result.scalars().all())
```

### = **BackfillService Transformation**

#### **Before (Technical Debt):**
```python
class BackfillService:
    def __init__(self, collector, processor, repository, database, config):
        # Direct database dependency for progress operations
        self._database = database

    async def _save_progress(self, progress: BackfillProgress) -> None:
        # L Direct database session management with merge() workaround
        async for session in self._database.get_database_session():
            if progress.id:
                await session.merge(progress)  # Technical debt
            else:
                session.add(progress)
            await session.commit()

    async def _load_backfill_progress(self, backfill_id: int) -> BackfillProgress:
        # L Raw SQLAlchemy queries in service layer
        async for session in self._database.get_database_session():
            stmt = select(BackfillProgressModel).where(
                BackfillProgressModel.id == backfill_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
```

#### **After (Clean Repository Pattern):**
```python
class BackfillService:
    def __init__(self, collector, processor, repository, database, config, progress_repository):
        # Clean dependency injection with repository
        self._progress_repository = progress_repository

    async def _save_progress(self, progress: BackfillProgress) -> None:
        #  Clean repository operations
        if progress.id:
            await self._progress_repository.update(progress)
        else:
            created_progress = await self._progress_repository.create(progress)
            progress.id = created_progress.id  # Update with generated ID

    async def _load_backfill_progress(self, backfill_id: int) -> BackfillProgress:
        #  Simple repository call
        progress = await self._progress_repository.get_by_id(backfill_id)
        if not progress:
            self._raise_progress_not_found_error(backfill_id)
        return progress

    async def list_active_backfills(self) -> list[dict[str, Any]]:
        #  Use specialized repository method
        active_progresses = await self._progress_repository.get_active_backfills()
        return [self._format_progress_summary(p) for p in active_progresses]
```

### =Ê **Benefits Quantification**

#### **Performance Improvements:**
- **Session Efficiency**: Eliminates unnecessary `merge()` operations (20-30% faster for updates)
- **Query Optimization**: Specialized repository methods reduce query complexity
- **Memory Usage**: Proper session scoping reduces object retention

#### **Code Quality Improvements:**
- **Separation of Concerns**: Service focuses on business logic, repository handles data access
- **Testability**: Repository can be easily mocked for unit testing
- **Type Safety**: Full generic type support with `BaseRepository[BackfillProgress]`
- **Error Handling**: Consistent exception patterns across all data operations

#### **Architectural Consistency:**
- **Pattern Alignment**: Matches existing EnergyDataRepository implementation
- **Dependency Injection**: Clean DI chain without direct database dependencies in services
- **Future Extensibility**: Easy to add new query methods as features grow

### >ê **Comprehensive Testing Strategy**

#### **Repository Unit Tests (New):**
```python
# tests/app/repositories/test_backfill_progress_repository.py
class TestBackfillProgressRepository:
    async def test_get_active_backfills_filters_correctly(self):
        # Test that only PENDING/IN_PROGRESS are returned

    async def test_get_resumable_backfills_has_progress(self):
        # Test resumable logic with completed_chunks > 0

    async def test_update_progress_by_id_fresh_object(self):
        # Test that updates use fresh session objects

    async def test_concurrent_updates_no_session_conflicts(self):
        # Test that concurrent operations don't have session issues
```

#### **Integration Tests (Enhanced):**
```python
# tests/integration/test_backfill_service_integration.py
class TestBackfillServiceIntegration:
    async def test_no_session_merge_workarounds_needed(self):
        # Verify that the old technical debt is resolved
        # Run through complete backfill lifecycle
        # Ensure no SQLAlchemy session attachment errors

    async def test_repository_pattern_end_to_end(self):
        # Test full workflow with repository pattern
        # Verify same functionality as before but cleaner implementation
```

This detailed implementation plan resolves the specific technical debt while establishing a foundation for clean, maintainable data access patterns in the service layer.
