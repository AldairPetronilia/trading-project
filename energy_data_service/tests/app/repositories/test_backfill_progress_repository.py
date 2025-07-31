"""
Unit tests for BackfillProgressRepository.

This test suite verifies the repository pattern implementation resolves
technical debt from direct database operations in the service layer.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.config.database import Database
from app.exceptions.repository_exceptions import DataAccessError
from app.models.backfill_progress import BackfillProgress, BackfillStatus
from app.repositories.backfill_progress_repository import BackfillProgressRepository
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


class TestBackfillProgressRepository:
    """Test suite for BackfillProgressRepository functionality."""

    @pytest.fixture
    def mock_database(self) -> MagicMock:
        """Create mock database instance."""
        database = MagicMock(spec=Database)
        database.session_factory = MagicMock()
        return database

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock async session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_database: MagicMock) -> BackfillProgressRepository:
        """Create repository instance with mocked database."""
        return BackfillProgressRepository(mock_database)

    @pytest.fixture
    def sample_progress(self) -> BackfillProgress:
        """Create sample BackfillProgress instance."""
        return BackfillProgress(
            id=1,
            area_code="DE",
            endpoint_name="actual_load",
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 2, tzinfo=UTC),
            status=BackfillStatus.IN_PROGRESS,
            progress_percentage=Decimal("50.00"),
            completed_chunks=5,
            total_chunks=10,
            total_data_points=1000,
            failed_chunks=0,
            chunk_size_days=1,
            rate_limit_delay=Decimal("1.00"),
        )

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
        sample_progress: BackfillProgress,
    ) -> None:
        """Test successful retrieval of backfill progress by ID."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_progress
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_id(1)

        # Assert
        assert result == sample_progress
        mock_session.execute.assert_called_once()
        mock_result.scalar_one_or_none.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """Test retrieval when backfill progress doesn't exist."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_id(999)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_database_error(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """Test database error handling in get_by_id."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        mock_session.execute.side_effect = SQLAlchemyError("Database connection error")

        # Act & Assert
        with pytest.raises(DataAccessError) as exc_info:
            await repository.get_by_id(1)

        assert "Failed to retrieve BackfillProgress with ID 1" in str(exc_info.value)
        assert exc_info.value.model_type == "BackfillProgress"
        assert exc_info.value.operation == "get_by_id"

    @pytest.mark.asyncio
    async def test_get_all_success(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
        sample_progress: BackfillProgress,
    ) -> None:
        """Test successful retrieval of all backfill progress records."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        progress_list = [sample_progress]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = progress_list
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_all()

        # Assert
        assert result == progress_list
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
        sample_progress: BackfillProgress,
    ) -> None:
        """Test successful deletion of backfill progress."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_progress
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.delete(1)

        # Assert
        assert result is True
        mock_session.delete.assert_called_once_with(sample_progress)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """Test deletion when record doesn't exist."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.delete(999)

        # Assert
        assert result is False
        mock_session.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_active_backfills(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """Test retrieval of active backfill operations."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        active_progress = BackfillProgress(
            id=1,
            area_code="FR",
            endpoint_name="actual_load",
            status=BackfillStatus.IN_PROGRESS,
            chunk_size_days=1,
            rate_limit_delay=Decimal("1.00"),
        )

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [active_progress]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_active_backfills()

        # Assert
        assert len(result) == 1
        assert result[0].status == BackfillStatus.IN_PROGRESS
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_resumable_backfills(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """Test retrieval of resumable backfill operations."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        resumable_progress = BackfillProgress(
            id=2,
            area_code="ES",
            endpoint_name="actual_load",
            status=BackfillStatus.FAILED,
            completed_chunks=3,
            chunk_size_days=1,
            rate_limit_delay=Decimal("1.00"),
        )

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [resumable_progress]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_resumable_backfills()

        # Assert
        assert len(result) == 1
        assert result[0].status == BackfillStatus.FAILED
        assert result[0].completed_chunks > 0

    @pytest.mark.asyncio
    async def test_get_by_area_endpoint(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
        sample_progress: BackfillProgress,
    ) -> None:
        """Test retrieval by area code and endpoint name."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_progress]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_area_endpoint("DE", "actual_load")

        # Assert
        assert len(result) == 1
        assert result[0].area_code == "DE"
        assert result[0].endpoint_name == "actual_load"

    @pytest.mark.asyncio
    async def test_update_progress_by_id_success(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
        sample_progress: BackfillProgress,
    ) -> None:
        """Test successful progress update by ID - eliminates session.merge() debt."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_progress
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.update_progress_by_id(
            1, completed_chunks=7, progress_percentage=Decimal("70.00")
        )

        # Assert
        assert result == sample_progress
        assert sample_progress.completed_chunks == 7
        assert sample_progress.progress_percentage == Decimal("70.00")
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(sample_progress)

    @pytest.mark.asyncio
    async def test_update_progress_by_id_not_found(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """Test progress update when record doesn't exist."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.update_progress_by_id(999, completed_chunks=5)

        # Assert
        assert result is None
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_progress_by_id_database_error(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """Test database error handling in update_progress_by_id."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        mock_session.execute.side_effect = SQLAlchemyError("Update failed")

        # Act & Assert
        with pytest.raises(DataAccessError) as exc_info:
            await repository.update_progress_by_id(1, completed_chunks=5)

        assert "Failed to update BackfillProgress with ID 1" in str(exc_info.value)
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_area_endpoint_period(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
        sample_progress: BackfillProgress,
    ) -> None:
        """Test retrieval by area, endpoint, and period combination."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_progress
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_area_endpoint_period(
            "DE",
            "actual_load",
            datetime(2024, 1, 1, tzinfo=UTC),
            datetime(2024, 1, 2, tzinfo=UTC),
        )

        # Assert
        assert result == sample_progress
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_management_without_cross_session_issues(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """Test that repository properly manages sessions without cross-session object issues."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        # Create fresh progress object in session context
        fresh_progress = BackfillProgress(
            id=1,
            area_code="DE",
            endpoint_name="actual_load",
            status=BackfillStatus.IN_PROGRESS,
            chunk_size_days=1,
            rate_limit_delay=Decimal("1.00"),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fresh_progress
        mock_session.execute.return_value = mock_result

        # Act - This should not require session.merge() workaround
        result = await repository.update_progress_by_id(1, completed_chunks=10)

        # Assert - Verify no merge operations needed
        assert result == fresh_progress
        assert fresh_progress.completed_chunks == 10
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        # The key assertion: no merge() call should be needed
        assert not hasattr(mock_session, "merge") or not mock_session.merge.called

    def test_get_model_name(self, repository: BackfillProgressRepository) -> None:
        """Test model name method for error reporting."""
        assert repository._get_model_name() == "BackfillProgress"

    @pytest.mark.asyncio
    async def test_concurrent_operations_no_session_conflicts(
        self, repository: BackfillProgressRepository, mock_database: MagicMock
    ) -> None:
        """Test that concurrent repository operations don't have session conflicts."""
        # Arrange
        mock_session_1 = AsyncMock(spec=AsyncSession)
        mock_session_2 = AsyncMock(spec=AsyncSession)

        # Mock different sessions for concurrent operations
        session_calls = [mock_session_1, mock_session_2]
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            side_effect=session_calls
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        progress_1 = BackfillProgress(
            id=1,
            area_code="DE",
            endpoint_name="actual_load",
            chunk_size_days=1,
            rate_limit_delay=Decimal("1.00"),
        )
        progress_2 = BackfillProgress(
            id=2,
            area_code="FR",
            endpoint_name="actual_load",
            chunk_size_days=1,
            rate_limit_delay=Decimal("1.00"),
        )

        mock_result_1 = MagicMock()
        mock_result_1.scalar_one_or_none.return_value = progress_1
        mock_session_1.execute.return_value = mock_result_1

        mock_result_2 = MagicMock()
        mock_result_2.scalar_one_or_none.return_value = progress_2
        mock_session_2.execute.return_value = mock_result_2

        # Act - Simulate concurrent operations
        result_1 = await repository.get_by_id(1)
        result_2 = await repository.get_by_id(2)

        # Assert - Each operation uses its own session
        assert result_1 == progress_1
        assert result_2 == progress_2
        mock_session_1.execute.assert_called_once()
        mock_session_2.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_specialized_query_performance(
        self,
        repository: BackfillProgressRepository,
        mock_database: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """Test that specialized queries are optimized for performance."""
        # Arrange
        mock_database.session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_database.session_factory.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act - Call specialized query methods
        await repository.get_active_backfills()
        await repository.get_resumable_backfills()
        await repository.get_by_area_endpoint("DE", "actual_load")

        # Assert - Verify efficient query patterns (no N+1 queries)
        assert mock_session.execute.call_count == 3
        # Each call should be a single optimized query, not multiple queries
