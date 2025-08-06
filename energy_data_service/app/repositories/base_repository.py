from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar

from app.config.database import Database
from app.exceptions.repository_exceptions import (
    ConstraintViolationError,
    DataAccessError,
    DatabaseConnectionError,
    DataValidationError,
    DuplicateDataError,
    RepositoryError,
)
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository[ModelType](ABC):
    """Abstract base repository providing common CRUD operations with database session management.

    This repository implements the Repository pattern with:
    - Generic type support for type-safe operations
    - Async database session management with automatic commit/rollback
    - Comprehensive exception handling with proper error context
    - Batch operations for high-performance data processing
    - Production-ready error handling and logging
    """

    def __init__(self, database: Database) -> None:
        """Initialize repository with database dependency.

        Args:
            database: Database instance for session management
        """
        self.database = database

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
        async with self.database.session_factory() as session:
            try:
                session.add(model)
                await session.flush()
                await session.refresh(model)
                await session.commit()
            except IntegrityError as e:
                await session.rollback()
                model_name = self._get_model_name()
                error_msg = (
                    f"Failed to create {model_name}: unique constraint violation"
                )
                raise DuplicateDataError(
                    error_msg,
                    model_type=model_name,
                    operation="create",
                    context={"error_code": getattr(e.orig, "pgcode", None)},
                ) from e
            except SQLAlchemyError as e:
                await session.rollback()
                model_name = self._get_model_name()
                error_msg = f"Failed to create {model_name}: database error"
                raise DataAccessError(
                    error_msg,
                    model_type=model_name,
                    operation="create",
                ) from e
            except Exception as e:
                await session.rollback()
                model_name = self._get_model_name()
                error_msg = f"Failed to create {model_name}: validation error"
                raise DataValidationError(
                    error_msg,
                    model_type=model_name,
                    operation="create",
                ) from e
            else:
                return model

    @abstractmethod
    async def get_by_id(self, item_id: Any) -> ModelType | None:
        """Retrieve a record by its primary key.

        Args:
            item_id: The primary key value

        Returns:
            The model instance if found, None otherwise

        Raises:
            DataAccessError: If the database operation fails
        """

    @abstractmethod
    async def get_all(self) -> list[ModelType]:
        """Retrieve all records of this model type.

        Returns:
            List of all model instances

        Raises:
            DataAccessError: If the database operation fails
        """

    async def update(self, model: ModelType) -> ModelType:
        """Update an existing record in the database.

        Args:
            model: The model instance with updated data

        Returns:
            The updated model instance

        Raises:
            DuplicateDataError: If a unique constraint is violated
            DataValidationError: If the model data is invalid
            DataAccessError: If the database operation fails
        """
        async with self.database.session_factory() as session:
            try:
                merged_model = await session.merge(model)
                await session.flush()
                await session.refresh(merged_model)
                await session.commit()
            except IntegrityError as e:
                await session.rollback()
                model_name = self._get_model_name()
                error_msg = (
                    f"Failed to update {model_name}: unique constraint violation"
                )
                raise DuplicateDataError(
                    error_msg,
                    model_type=model_name,
                    operation="update",
                    context={"error_code": getattr(e.orig, "pgcode", None)},
                ) from e
            except SQLAlchemyError as e:
                await session.rollback()
                model_name = self._get_model_name()
                error_msg = f"Failed to update {model_name}: database error"
                raise DataAccessError(
                    error_msg,
                    model_type=model_name,
                    operation="update",
                ) from e
            except Exception as e:
                await session.rollback()
                model_name = self._get_model_name()
                error_msg = f"Failed to update {model_name}: validation error"
                raise DataValidationError(
                    error_msg,
                    model_type=model_name,
                    operation="update",
                ) from e
            else:
                return merged_model

    @abstractmethod
    async def delete(self, item_id: Any) -> bool:
        """Delete a record by its primary key.

        Args:
            item_id: The primary key value

        Returns:
            True if the record was deleted, False if not found

        Raises:
            DataAccessError: If the database operation fails
        """

    async def create_batch(self, models: list[ModelType]) -> list[ModelType]:
        """Create multiple records in a single transaction.

        Args:
            models: List of model instances to create

        Returns:
            List of created model instances with database-generated fields

        Raises:
            DuplicateDataError: If any unique constraint is violated
            DataValidationError: If any model data is invalid
            DataAccessError: If the database operation fails
        """
        if not models:
            return []

        async with self.database.session_factory() as session:
            try:
                session.add_all(models)
                await session.flush()
                for model in models:
                    await session.refresh(model)
                await session.commit()
            except IntegrityError as e:
                await session.rollback()
                model_name = self._get_model_name()
                error_msg = f"Failed to create batch of {model_name}: unique constraint violation"
                raise DuplicateDataError(
                    error_msg,
                    model_type=model_name,
                    operation="create_batch",
                    context={
                        "batch_size": len(models),
                        "error_code": getattr(e.orig, "pgcode", None),
                    },
                ) from e
            except SQLAlchemyError as e:
                await session.rollback()
                model_name = self._get_model_name()
                error_msg = f"Failed to create batch of {model_name}: database error"
                raise DataAccessError(
                    error_msg,
                    model_type=model_name,
                    operation="create_batch",
                    context={"batch_size": len(models)},
                ) from e
            except Exception as e:
                await session.rollback()
                model_name = self._get_model_name()
                error_msg = f"Failed to create batch of {model_name}: validation error"
                raise DataValidationError(
                    error_msg,
                    model_type=model_name,
                    operation="create_batch",
                    context={"batch_size": len(models)},
                ) from e
            else:
                return models

    async def update_batch(self, models: list[ModelType]) -> list[ModelType]:
        """Update multiple records in a single transaction.

        Args:
            models: List of model instances to update

        Returns:
            List of updated model instances

        Raises:
            DuplicateDataError: If any unique constraint is violated
            DataValidationError: If any model data is invalid
            DataAccessError: If the database operation fails
        """
        if not models:
            return []

        async with self.database.session_factory() as session:
            try:
                updated_models = []
                for model in models:
                    merged_model = await session.merge(model)
                    updated_models.append(merged_model)

                await session.flush()

                for model in updated_models:
                    await session.refresh(model)

                await session.commit()
            except IntegrityError as e:
                await session.rollback()
                model_name = self._get_model_name()
                error_msg = f"Failed to update batch of {model_name}: unique constraint violation"
                raise DuplicateDataError(
                    error_msg,
                    model_type=model_name,
                    operation="update_batch",
                    context={
                        "batch_size": len(models),
                        "error_code": getattr(e.orig, "pgcode", None),
                    },
                ) from e
            except SQLAlchemyError as e:
                await session.rollback()
                model_name = self._get_model_name()
                error_msg = f"Failed to update batch of {model_name}: database error"
                raise DataAccessError(
                    error_msg,
                    model_type=model_name,
                    operation="update_batch",
                    context={"batch_size": len(models)},
                ) from e
            except Exception as e:
                await session.rollback()
                model_name = self._get_model_name()
                error_msg = f"Failed to update batch of {model_name}: validation error"
                raise DataValidationError(
                    error_msg,
                    model_type=model_name,
                    operation="update_batch",
                    context={"batch_size": len(models)},
                ) from e
            else:
                return updated_models

    def _get_model_name(self) -> str:
        """Get the model type name for error reporting.

        Returns:
            String representation of the model type
        """
        return "Model"

    async def test_connection(self) -> None:
        """Test database connection for health checks.

        Performs a simple database query to verify connectivity.

        Raises:
            DataAccessError: If database connection fails
        """
        async with self.database.session_factory() as session:
            try:
                await session.execute(text("SELECT 1"))
            except SQLAlchemyError as e:
                model_name = self._get_model_name()
                error_msg = f"Database connection test failed for {model_name}"
                raise DataAccessError(
                    error_msg,
                    model_type=model_name,
                    operation="test_connection",
                ) from e
