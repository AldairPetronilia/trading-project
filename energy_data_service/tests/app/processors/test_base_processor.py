"""
Unit tests for BaseProcessor abstract interface.

Tests the foundational processor interface behavior including validation,
error handling, and type safety requirements.
"""

import pytest
from app.exceptions.processor_exceptions import DataValidationError
from app.processors.base_processor import BaseProcessor

pytestmark = pytest.mark.asyncio


class MockInputType:
    """Mock input type for testing."""

    def __init__(self, value: str) -> None:
        self.value = value


class MockOutputType:
    """Mock output type for testing."""

    def __init__(self, processed_value: str) -> None:
        self.processed_value = processed_value


class ConcreteProcessor(BaseProcessor[MockInputType, MockOutputType]):
    """Concrete processor implementation for testing."""

    async def process(self, raw_data: list[MockInputType]) -> list[MockOutputType]:
        """Transform mock input to mock output."""
        return [MockOutputType(f"processed_{item.value}") for item in raw_data]


class FailingProcessor(BaseProcessor[MockInputType, MockOutputType]):
    """Processor that always fails for error testing."""

    async def process(self, _raw_data: list[MockInputType]) -> list[MockOutputType]:
        """Always raise an exception."""
        msg = "Processing failed"
        raise ValueError(msg)


class TestBaseProcessor:
    """Test suite for BaseProcessor abstract interface."""

    @pytest.fixture
    def processor(self) -> ConcreteProcessor:
        """Create a concrete processor instance."""
        return ConcreteProcessor()

    @pytest.fixture
    def failing_processor(self) -> FailingProcessor:
        """Create a failing processor instance."""
        return FailingProcessor()

    @pytest.fixture
    def mock_input_data(self) -> list[MockInputType]:
        """Create mock input data."""
        return [
            MockInputType("item1"),
            MockInputType("item2"),
            MockInputType("item3"),
        ]

    def test_processor_initialization(self, processor: ConcreteProcessor) -> None:
        """Test processor can be instantiated."""
        assert processor is not None
        assert isinstance(processor, BaseProcessor)

    async def test_successful_processing(
        self,
        processor: ConcreteProcessor,
        mock_input_data: list[MockInputType],
    ) -> None:
        """Test successful data processing."""
        result = await processor.process(mock_input_data)

        assert len(result) == 3
        assert result[0].processed_value == "processed_item1"
        assert result[1].processed_value == "processed_item2"
        assert result[2].processed_value == "processed_item3"

    async def test_validate_input_with_valid_list(
        self,
        processor: ConcreteProcessor,
        mock_input_data: list[MockInputType],
    ) -> None:
        """Test input validation with valid list."""
        # Should not raise any exception
        await processor.validate_input(mock_input_data)

    async def test_validate_input_with_empty_list(
        self,
        processor: ConcreteProcessor,
    ) -> None:
        """Test input validation with empty list."""
        # Should not raise any exception
        await processor.validate_input([])

    async def test_validate_input_with_non_list(
        self,
        processor: ConcreteProcessor,
    ) -> None:
        """Test input validation with non-list input."""
        with pytest.raises(DataValidationError) as exc_info:
            await processor.validate_input("not_a_list")

        error = exc_info.value
        assert "Input data must be a list" in str(error)
        assert error.field == "raw_data"
        assert error.value == "str"

    async def test_validate_output_with_valid_list(
        self,
        processor: ConcreteProcessor,
    ) -> None:
        """Test output validation with valid list."""
        output_data = [MockOutputType("test")]

        # Should not raise any exception
        await processor.validate_output(output_data)

    async def test_validate_output_with_empty_list(
        self,
        processor: ConcreteProcessor,
    ) -> None:
        """Test output validation with empty list."""
        # Should not raise any exception
        await processor.validate_output([])

    async def test_validate_output_with_non_list(
        self,
        processor: ConcreteProcessor,
    ) -> None:
        """Test output validation with non-list output."""
        with pytest.raises(DataValidationError) as exc_info:
            await processor.validate_output("not_a_list")

        error = exc_info.value
        assert "Processed data must be a list" in str(error)
        assert error.field == "processed_data"
        assert error.value == "str"

    async def test_abstract_method_enforcement(self) -> None:
        """Test that BaseProcessor cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseProcessor()  # type: ignore[abstract]

    def test_generic_type_safety(self) -> None:
        """Test that processor maintains type safety through generics."""
        # This test verifies that the processor correctly uses generic types
        # The actual type checking is done by mypy, but we can verify the structure
        processor = ConcreteProcessor()

        # Verify that the processor has the expected generic type structure
        assert hasattr(processor, "__orig_bases__")
        assert len(processor.__orig_bases__) == 1

        # The base class should be parameterized with our mock types
        base_class = processor.__orig_bases__[0]
        assert hasattr(base_class, "__origin__")
        assert base_class.__origin__ is BaseProcessor

    async def test_processor_with_none_input(
        self,
        processor: ConcreteProcessor,
    ) -> None:
        """Test processor behavior with None input."""
        with pytest.raises(DataValidationError) as exc_info:
            await processor.validate_input(None)

        error = exc_info.value
        assert "Input data must be a list" in str(error)
        assert error.field == "raw_data"
        assert error.value == "NoneType"
