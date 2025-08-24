"""
Test suite for PublicationMarketDocumentProcessor.

Comprehensive tests covering transformation of ENTSO-E market documents
to EnergyPricePoint models with full error handling validation.
"""

from datetime import UTC, datetime, timezone
from decimal import Decimal
from unittest.mock import Mock

import pytest
from app.exceptions.processor_exceptions import (
    DataValidationError,
    DocumentParsingError,
    MappingError,
    TimestampCalculationError,
    TransformationError,
)
from app.models.load_data import EnergyDataType
from app.models.price_data import EnergyPricePoint
from app.processors.publication_market_document_processor import (
    DurationComponents,
    PublicationMarketDocumentProcessor,
)

from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.auction_type import AuctionType
from entsoe_client.model.common.business_type import BusinessType
from entsoe_client.model.common.contract_market_agreement_type import (
    ContractMarketAgreementType,
)
from entsoe_client.model.common.curve_type import CurveType
from entsoe_client.model.common.document_type import DocumentType
from entsoe_client.model.common.domain_mrid import DomainMRID
from entsoe_client.model.common.market_role_type import MarketRoleType
from entsoe_client.model.common.process_type import ProcessType
from entsoe_client.model.market.market_domain_mrid import MarketDomainMRID
from entsoe_client.model.market.market_participant_mrid import MarketParticipantMRID
from entsoe_client.model.market.market_period import MarketPeriod
from entsoe_client.model.market.market_point import MarketPoint
from entsoe_client.model.market.market_time_interval import MarketTimeInterval
from entsoe_client.model.market.market_time_series import MarketTimeSeries
from entsoe_client.model.market.publication_market_document import (
    PublicationMarketDocument,
)


@pytest.fixture
def processor() -> PublicationMarketDocumentProcessor:
    """Create a PublicationMarketDocumentProcessor instance."""
    return PublicationMarketDocumentProcessor()


@pytest.fixture
def sample_area_code() -> AreaCode:
    """Create a sample AreaCode."""
    return AreaCode.GERMANY


@pytest.fixture
def sample_domain_mrid(sample_area_code: AreaCode) -> MarketDomainMRID:
    """Create a sample MarketDomainMRID."""
    return MarketDomainMRID(area_code=sample_area_code, coding_scheme="A01")


@pytest.fixture
def sample_business_type() -> BusinessType:
    """Create a sample BusinessType."""
    return BusinessType.from_code("A62")  # Day-ahead prices


@pytest.fixture
def sample_auction_type() -> AuctionType:
    """Create a sample AuctionType."""
    return AuctionType.from_code("A01")  # Day-ahead auction


@pytest.fixture
def sample_contract_type() -> ContractMarketAgreementType:
    """Create a sample ContractMarketAgreementType."""
    return ContractMarketAgreementType.from_code("A01")  # Daily auction


@pytest.fixture
def sample_curve_type() -> CurveType:
    """Create a sample CurveType."""
    return CurveType.from_code("A03")  # Variable sized block


@pytest.fixture
def sample_market_point() -> MarketPoint:
    """Create a sample MarketPoint with price data."""
    return MarketPoint(position=1, price_amount=45.67)


@pytest.fixture
def sample_market_time_interval() -> MarketTimeInterval:
    """Create a sample MarketTimeInterval."""
    start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    end = datetime(2024, 1, 2, 0, 0, tzinfo=UTC)
    return MarketTimeInterval(start=start, end=end)


@pytest.fixture
def sample_market_period(
    sample_market_time_interval: MarketTimeInterval,
    sample_market_point: MarketPoint,
) -> MarketPeriod:
    """Create a sample MarketPeriod."""
    return MarketPeriod(
        timeInterval=sample_market_time_interval,
        resolution="PT60M",
        points=[sample_market_point],
    )


@pytest.fixture
def sample_market_time_series(
    sample_business_type: BusinessType,
    sample_domain_mrid: MarketDomainMRID,
    sample_auction_type: AuctionType,
    sample_contract_type: ContractMarketAgreementType,
    sample_curve_type: CurveType,
    sample_market_period: MarketPeriod,
) -> MarketTimeSeries:
    """Create a sample MarketTimeSeries."""
    return MarketTimeSeries(
        mRID="1",
        businessType=sample_business_type,
        out_domain_mRID=sample_domain_mrid,
        auction_type=sample_auction_type,
        contract_market_agreement_type=sample_contract_type,
        curveType=sample_curve_type,
        currency_unit_name="EUR",
        price_measure_unit_name="EUR/MWh",
        period=sample_market_period,
    )


@pytest.fixture
def sample_publication_market_document(
    sample_market_time_series: MarketTimeSeries,
) -> PublicationMarketDocument:
    """Create a sample PublicationMarketDocument."""
    start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    end = datetime(2024, 1, 2, 0, 0, tzinfo=UTC)
    time_interval = MarketTimeInterval(start=start, end=end)

    return PublicationMarketDocument(
        mRID="test-document-123",
        revisionNumber=1,
        type=DocumentType.PRICE_DOCUMENT,
        senderMarketParticipantMRID=MarketParticipantMRID(
            value="test-sender", coding_scheme="A01"
        ),
        senderMarketParticipantMarketRoleType=MarketRoleType.from_code("A32"),
        receiverMarketParticipantMRID=MarketParticipantMRID(
            value="test-receiver", coding_scheme="A01"
        ),
        receiverMarketParticipantMarketRoleType=MarketRoleType.from_code("A33"),
        createdDateTime=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        periodTimeInterval=time_interval,
        timeSeries=[sample_market_time_series],
    )


class TestPublicationMarketDocumentProcessor:
    """Test suite for PublicationMarketDocumentProcessor."""

    async def test_process_valid_document_success(
        self,
        processor: PublicationMarketDocumentProcessor,
        sample_publication_market_document: PublicationMarketDocument,
    ) -> None:
        """Test successful processing of valid market document."""
        documents = [sample_publication_market_document]

        result = await processor.process(documents)

        assert len(result) == 1
        price_point = result[0]
        assert isinstance(price_point, EnergyPricePoint)

        # Test basic price and market data
        assert price_point.price_amount == Decimal("45.67")
        assert price_point.currency_unit_name == "EUR"
        assert price_point.price_measure_unit_name == "EUR/MWh"
        assert price_point.area_code == "DE"
        assert price_point.data_type == EnergyDataType.DAY_AHEAD
        assert price_point.business_type == "A62"
        assert price_point.auction_type == "A01"
        assert price_point.contract_market_agreement_type == "A01"

        # Test required database fields (nullable=False)
        assert price_point.document_mrid == sample_publication_market_document.mRID
        assert (
            price_point.time_series_mrid
            == sample_publication_market_document.timeSeries[0].mRID
        )
        assert price_point.resolution == "PT60M"
        assert (
            price_point.document_created_at
            == sample_publication_market_document.createdDateTime
        )
        assert price_point.position == 1  # First point position
        assert price_point.period_start == datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        assert price_point.period_end == datetime(2024, 1, 2, 0, 0, tzinfo=UTC)

    async def test_process_validates_all_required_database_fields(
        self,
        processor: PublicationMarketDocumentProcessor,
        sample_publication_market_document: PublicationMarketDocument,
    ) -> None:
        """Test that all required database fields (nullable=False) are properly populated."""
        result = await processor.process([sample_publication_market_document])

        assert len(result) == 1
        price_point = result[0]

        # These fields caused the original database constraint violation bug
        # Ensure they are all populated (not None) and have correct values
        required_fields = [
            ("document_mrid", sample_publication_market_document.mRID),
            ("time_series_mrid", sample_publication_market_document.timeSeries[0].mRID),
            ("resolution", "PT60M"),
            ("document_created_at", sample_publication_market_document.createdDateTime),
            ("position", 1),
            ("period_start", datetime(2024, 1, 1, 0, 0, tzinfo=UTC)),
            ("period_end", datetime(2024, 1, 2, 0, 0, tzinfo=UTC)),
        ]

        for field_name, expected_value in required_fields:
            actual_value = getattr(price_point, field_name)
            assert actual_value is not None, (
                f"Required field '{field_name}' is None (nullable=False constraint violation)"
            )
            assert actual_value == expected_value, (
                f"Field '{field_name}' has incorrect value: {actual_value} != {expected_value}"
            )

        # Verify these are the exact fields that were missing in the original bug
        # All 7 required database fields are properly populated

        # Test optional fields are also populated correctly
        assert (
            price_point.revision_number
            == sample_publication_market_document.revisionNumber
        )
        # curve_type should be populated from time series curveType
        expected_curve_type = sample_publication_market_document.timeSeries[0].curveType
        if expected_curve_type:
            assert price_point.curve_type == expected_curve_type.code
        else:
            assert price_point.curve_type is None

    async def test_process_multiple_documents_success(
        self,
        processor: PublicationMarketDocumentProcessor,
        sample_publication_market_document: PublicationMarketDocument,
    ) -> None:
        """Test processing multiple documents."""
        # Create second document with different MRID
        document2 = sample_publication_market_document.model_copy()
        document2.mRID = "test-document-456"
        documents = [sample_publication_market_document, document2]

        result = await processor.process(documents)

        assert len(result) == 2
        assert all(isinstance(point, EnergyPricePoint) for point in result)
        assert all(point.price_amount == Decimal("45.67") for point in result)

    async def test_process_document_with_multiple_time_series(
        self,
        processor: PublicationMarketDocumentProcessor,
        sample_publication_market_document: PublicationMarketDocument,
        sample_market_time_series: MarketTimeSeries,
    ) -> None:
        """Test processing document with multiple time series."""
        # Add second time series
        time_series2 = sample_market_time_series.model_copy()
        time_series2.mRID = "2"
        sample_publication_market_document.timeSeries.append(time_series2)

        result = await processor.process([sample_publication_market_document])

        assert len(result) == 2
        assert all(isinstance(point, EnergyPricePoint) for point in result)

    async def test_process_document_with_multiple_points(
        self,
        processor: PublicationMarketDocumentProcessor,
        sample_publication_market_document: PublicationMarketDocument,
    ) -> None:
        """Test processing document with multiple price points."""
        # Add second point to the period
        point2 = MarketPoint(position=2, price_amount=52.34)
        sample_publication_market_document.timeSeries[0].period.points.append(point2)

        result = await processor.process([sample_publication_market_document])

        assert len(result) == 2
        assert result[0].price_amount == Decimal("45.67")
        assert result[1].price_amount == Decimal("52.34")
        # Second point should be one hour later (PT60M resolution)
        expected_timestamp = result[0].timestamp.replace(hour=1)
        assert result[1].timestamp == expected_timestamp

    async def test_process_skips_null_price_amounts(
        self,
        processor: PublicationMarketDocumentProcessor,
        sample_publication_market_document: PublicationMarketDocument,
    ) -> None:
        """Test that points with null price amounts are skipped."""
        # Add point with null price_amount
        null_point = MarketPoint(position=2, price_amount=None)
        sample_publication_market_document.timeSeries[0].period.points.append(
            null_point
        )

        result = await processor.process([sample_publication_market_document])

        # Only the first point should be processed
        assert len(result) == 1
        assert result[0].price_amount == Decimal("45.67")

    async def test_process_skips_null_positions(
        self,
        processor: PublicationMarketDocumentProcessor,
        sample_publication_market_document: PublicationMarketDocument,
    ) -> None:
        """Test that points with null positions are skipped."""
        # Add point with null position
        null_point = MarketPoint(position=None, price_amount=42.0)
        sample_publication_market_document.timeSeries[0].period.points.append(
            null_point
        )

        result = await processor.process([sample_publication_market_document])

        # Only the first point should be processed
        assert len(result) == 1
        assert result[0].price_amount == Decimal("45.67")

    async def test_process_default_currency_when_none(
        self,
        processor: PublicationMarketDocumentProcessor,
        sample_publication_market_document: PublicationMarketDocument,
    ) -> None:
        """Test default currency handling when currency_unit_name is None."""
        sample_publication_market_document.timeSeries[0].currency_unit_name = None

        result = await processor.process([sample_publication_market_document])

        assert len(result) == 1
        assert result[0].currency_unit_name == "EUR"  # Default value

    async def test_process_default_price_unit_when_none(
        self,
        processor: PublicationMarketDocumentProcessor,
        sample_publication_market_document: PublicationMarketDocument,
    ) -> None:
        """Test default price measure unit when price_measure_unit_name is None."""
        sample_publication_market_document.timeSeries[0].price_measure_unit_name = None

        result = await processor.process([sample_publication_market_document])

        assert len(result) == 1
        assert result[0].price_measure_unit_name == "EUR/MWh"  # Default value

    async def test_process_null_auction_type(
        self,
        processor: PublicationMarketDocumentProcessor,
        sample_publication_market_document: PublicationMarketDocument,
    ) -> None:
        """Test handling of null auction type."""
        sample_publication_market_document.timeSeries[0].auction_type = None

        result = await processor.process([sample_publication_market_document])

        assert len(result) == 1
        assert result[0].auction_type is None

    async def test_process_null_contract_agreement_type(
        self,
        processor: PublicationMarketDocumentProcessor,
        sample_publication_market_document: PublicationMarketDocument,
    ) -> None:
        """Test handling of null contract market agreement type."""
        sample_publication_market_document.timeSeries[
            0
        ].contract_market_agreement_type = None

        result = await processor.process([sample_publication_market_document])

        assert len(result) == 1
        assert result[0].contract_market_agreement_type is None

    async def test_process_invalid_input_data_validation_error(
        self, processor: PublicationMarketDocumentProcessor
    ) -> None:
        """Test that invalid input raises DataValidationError."""
        with pytest.raises(DataValidationError):
            await processor.process("invalid_input")  # type: ignore[arg-type]

    async def test_process_document_parsing_error(
        self,
        processor: PublicationMarketDocumentProcessor,
    ) -> None:
        """Test DocumentParsingError when document processing fails."""
        # Create a mock document that will cause an error
        mock_document = Mock()
        mock_document.mRID = "error-document"
        mock_document.type = DocumentType.PRICE_DOCUMENT
        mock_document.timeSeries = []  # Empty time series
        # Make attribute access raise an exception
        mock_document.timeSeries = Mock(side_effect=Exception("Mock error"))

        with pytest.raises(
            TransformationError, match="Failed to process document error-document"
        ):
            await processor.process([mock_document])

    async def test_calculate_point_timestamp_hourly_resolution(
        self, processor: PublicationMarketDocumentProcessor
    ) -> None:
        """Test timestamp calculation for hourly resolution (PT60M)."""
        period_start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        # Position 1 should be at period start
        timestamp1 = processor._calculate_point_timestamp(period_start, "PT60M", 1)
        assert timestamp1 == period_start

        # Position 2 should be 1 hour later
        timestamp2 = processor._calculate_point_timestamp(period_start, "PT60M", 2)
        expected = period_start.replace(hour=1)
        assert timestamp2 == expected

    async def test_calculate_point_timestamp_15min_resolution(
        self, processor: PublicationMarketDocumentProcessor
    ) -> None:
        """Test timestamp calculation for 15-minute resolution (PT15M)."""
        period_start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        # Position 2 should be 15 minutes later
        timestamp = processor._calculate_point_timestamp(period_start, "PT15M", 2)
        expected = period_start.replace(minute=15)
        assert timestamp == expected

    async def test_calculate_point_timestamp_daily_resolution(
        self, processor: PublicationMarketDocumentProcessor
    ) -> None:
        """Test timestamp calculation for daily resolution (P1D)."""
        period_start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)

        # Position 2 should be 1 day later
        timestamp = processor._calculate_point_timestamp(period_start, "P1D", 2)
        expected = period_start.replace(day=2)
        assert timestamp == expected

    def test_parse_iso_duration_to_components_hourly(
        self, processor: PublicationMarketDocumentProcessor
    ) -> None:
        """Test parsing of hourly ISO 8601 duration."""
        duration = processor._parse_iso_duration_to_components("PT1H")
        assert duration.hours == 1
        assert duration.minutes == 0
        assert duration.days == 0

    def test_parse_iso_duration_to_components_15min(
        self, processor: PublicationMarketDocumentProcessor
    ) -> None:
        """Test parsing of 15-minute ISO 8601 duration."""
        duration = processor._parse_iso_duration_to_components("PT15M")
        assert duration.minutes == 15
        assert duration.hours == 0
        assert duration.days == 0

    def test_parse_iso_duration_to_components_daily(
        self, processor: PublicationMarketDocumentProcessor
    ) -> None:
        """Test parsing of daily ISO 8601 duration."""
        duration = processor._parse_iso_duration_to_components("P1D")
        assert duration.days == 1
        assert duration.hours == 0
        assert duration.minutes == 0

    def test_parse_iso_duration_invalid_format(
        self, processor: PublicationMarketDocumentProcessor
    ) -> None:
        """Test parsing invalid ISO 8601 duration format."""
        with pytest.raises(ValueError, match="Invalid ISO 8601 duration format"):
            processor._parse_iso_duration_to_components("INVALID")

    def test_parse_iso_duration_empty_components(
        self, processor: PublicationMarketDocumentProcessor
    ) -> None:
        """Test parsing ISO 8601 duration with no components."""
        with pytest.raises(ValueError, match="Could not parse any duration components"):
            processor._parse_iso_duration_to_components("P")

    def test_map_document_to_energy_data_type_success(
        self, processor: PublicationMarketDocumentProcessor
    ) -> None:
        """Test successful document type mapping."""
        data_type = processor._map_document_to_energy_data_type(
            ProcessType.DAY_AHEAD, DocumentType.PRICE_DOCUMENT
        )
        assert data_type == EnergyDataType.DAY_AHEAD

    def test_map_document_to_energy_data_type_unsupported(
        self, processor: PublicationMarketDocumentProcessor
    ) -> None:
        """Test mapping error for unsupported combination."""
        with pytest.raises(
            MappingError, match="Unsupported ProcessType\\+DocumentType combination"
        ):
            processor._map_document_to_energy_data_type(
                ProcessType.REALISED, DocumentType.SYSTEM_TOTAL_LOAD
            )

    def test_extract_area_code_success(
        self,
        processor: PublicationMarketDocumentProcessor,
        sample_domain_mrid: MarketDomainMRID,
    ) -> None:
        """Test successful area code extraction."""
        area_code = processor._extract_area_code(sample_domain_mrid)
        assert area_code == "DE"

    def test_extract_area_code_none_domain(
        self, processor: PublicationMarketDocumentProcessor
    ) -> None:
        """Test area code extraction with None domain."""
        area_code = processor._extract_area_code(None)
        assert area_code == "UNKNOWN"

    def test_extract_area_code_extraction_error(
        self, processor: PublicationMarketDocumentProcessor
    ) -> None:
        """Test area code extraction error handling."""
        # Create mock that raises exception when accessing nested attributes
        from unittest.mock import PropertyMock

        mock_domain = Mock()
        # Configure area_code property to raise exception
        type(mock_domain).area_code = PropertyMock(side_effect=Exception("Mock error"))
        mock_domain.value = "mock-value"

        with pytest.raises(TransformationError, match="Failed to extract area code"):
            processor._extract_area_code(mock_domain)


class TestDurationComponents:
    """Test suite for DurationComponents helper class."""

    def test_init_default_values(self) -> None:
        """Test DurationComponents initialization with default values."""
        duration = DurationComponents()
        assert duration.years == 0
        assert duration.months == 0
        assert duration.days == 0
        assert duration.hours == 0
        assert duration.minutes == 0

    def test_init_custom_values(self) -> None:
        """Test DurationComponents initialization with custom values."""
        duration = DurationComponents(years=1, months=2, days=3, hours=4, minutes=5)
        assert duration.years == 1
        assert duration.months == 2
        assert duration.days == 3
        assert duration.hours == 4
        assert duration.minutes == 5
