from datetime import UTC, datetime, timezone
from typing import Any, Optional


class RepositoryError(Exception):
    """Base class for repository exceptions with structured error information."""

    def __init__(
        self,
        message: str,
        *,
        model_type: str | None = None,
        operation: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.model_type = model_type
        self.operation = operation
        self.context = context or {}
        self.timestamp = datetime.now(UTC)


class DataAccessError(RepositoryError):
    """Exception raised for SQL query execution and transaction failures."""


class DatabaseConnectionError(RepositoryError):
    """Exception raised for database connection and network issues."""


class DataValidationError(RepositoryError):
    """Exception raised for model validation and type conversion errors."""


class ConstraintViolationError(RepositoryError):
    """Exception raised for database constraint violations."""


class DuplicateDataError(RepositoryError):
    """Exception raised for unique constraint violations and duplicate records."""


class ConcurrencyError(RepositoryError):
    """Exception raised for transaction conflicts and optimistic locking failures."""
