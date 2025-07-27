"""Abstract base processor for data transformation operations."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from app.exceptions.processor_exceptions import DataValidationError

InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")


class BaseProcessor[InputType, OutputType](ABC):
    """
    Abstract base class for data processors.

    Defines the contract for transforming raw data from external sources
    into standardized database models with type safety and error handling.
    """

    @abstractmethod
    async def process(self, raw_data: list[InputType]) -> list[OutputType]:
        """
        Transform raw data into processed database models.

        Args:
            raw_data: List of raw data objects from external sources

        Returns:
            List of processed data models ready for database storage

        Raises:
            ProcessorError: For processing-specific errors with context
            DataValidationError: For data quality or validation failures
        """

    async def validate_input(self, raw_data: object) -> None:
        """
        Validate input data before processing.

        Args:
            raw_data: Raw data to validate

        Raises:
            DataValidationError: If input data is invalid
        """
        if not isinstance(raw_data, list):
            msg = "Input data must be a list"
            raise DataValidationError(
                msg,
                field="raw_data",
                value=type(raw_data).__name__,
            )

    async def validate_output(self, processed_data: object) -> None:
        """
        Validate processed data after transformation.

        Args:
            processed_data: Processed data to validate

        Raises:
            DataValidationError: If processed data is invalid
        """
        if not isinstance(processed_data, list):
            msg = "Processed data must be a list"
            raise DataValidationError(
                msg,
                field="processed_data",
                value=type(processed_data).__name__,
            )
