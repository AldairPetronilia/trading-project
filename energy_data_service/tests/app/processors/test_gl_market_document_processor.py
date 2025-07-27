"""Tests for GL_MarketDocument processor transformation logic."""

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
from app.models.load_data import EnergyDataPoint, EnergyDataType
from app.processors.gl_market_document_processor import GlMarketDocumentProcessor

from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.business_type import BusinessType
from entsoe_client.model.common.curve_type import CurveType
from entsoe_client.model.common.document_type import DocumentType
from entsoe_client.model.common.domain_mrid import DomainMRID
from entsoe_client.model.common.market_role_type import MarketRoleType
from entsoe_client.model.common.object_aggregation import ObjectAggregation
from entsoe_client.model.common.process_type import ProcessType
from entsoe_client.model.load.gl_market_document import GlMarketDocument
from entsoe_client.model.load.load_period import LoadPeriod
from entsoe_client.model.load.load_point import LoadPoint
from entsoe_client.model.load.load_time_interval import LoadTimeInterval
from entsoe_client.model.load.load_time_series import LoadTimeSeries
from entsoe_client.model.load.market_participant_mrid import MarketParticipantMRID

pytestmark = pytest.mark.asyncio


class TestGlMarketDocumentProcessor:
    """Test suite for GL_MarketDocument processor."""

    @pytest.fixture
    def processor(self) -> GlMarketDocumentProcessor:
        """Create processor instance for testing."""
        return GlMarketDocumentProcessor()

    @pytest.fixture
    def sample_document(self) -> GlMarketDocument:
        """Create sample GL_MarketDocument for testing."""
        # Create mock objects for the document structure
        time_interval = LoadTimeInterval(
            start=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            end=datetime(2023, 1, 1, 1, 0, tzinfo=UTC),
        )

        points = [
            LoadPoint(position=1, quantity=100.5),
            LoadPoint(position=2, quantity=95.3),
            LoadPoint(position=3, quantity=102.7),
            LoadPoint(position=4, quantity=98.1),
        ]

        period = LoadPeriod(
            timeInterval=time_interval,
            resolution="PT15M",
            points=points,
        )

        time_series = LoadTimeSeries(
            mRID="TS123456789",
            businessType=BusinessType.CONSUMPTION,
            objectAggregation=ObjectAggregation.AGGREGATED,
            outBiddingZoneDomainMRID=DomainMRID(area_code=AreaCode.GERMANY),
            quantityMeasureUnitName="MAW",
            curveType=CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK,
            period=period,
        )

        return GlMarketDocument(
            mRID="DOC123456789",
            revisionNumber=1,
            type=DocumentType.SYSTEM_TOTAL_LOAD,  # Use correct DocumentType for standard load data
            processType=ProcessType.REALISED,
            senderMarketParticipantMRID=MarketParticipantMRID(
                value="10X1001A1001A450", coding_scheme=None
            ),
            senderMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
            receiverMarketParticipantMRID=MarketParticipantMRID(
                value="10X1001A1001A450", coding_scheme=None
            ),
            receiverMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
            createdDateTime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
            timePeriodTimeInterval=time_interval,
            timeSeries=time_series,
        )

    async def test_process_single_document_success(
        self,
        processor: GlMarketDocumentProcessor,
        sample_document: GlMarketDocument,
    ) -> None:
        """Test successful processing of a single GL_MarketDocument."""
        result = await processor.process([sample_document])

        assert len(result) == 4  # 4 points in the sample document

        # Check first point details
        first_point = result[0]
        assert isinstance(first_point, EnergyDataPoint)
        assert first_point.timestamp == datetime(2023, 1, 1, 0, 0, tzinfo=UTC)
        assert first_point.area_code == "DE"
        assert first_point.data_type == EnergyDataType.ACTUAL
        assert first_point.business_type == "A04"  # BusinessType.CONSUMPTION code
        assert first_point.quantity == Decimal("100.5")
        assert first_point.unit == "MAW"
        assert first_point.data_source == "entsoe"
        assert first_point.document_mrid == "DOC123456789"
        assert first_point.revision_number == 1
        assert first_point.position == 1

        # Check timestamp progression
        assert result[1].timestamp == datetime(2023, 1, 1, 0, 15, tzinfo=UTC)
        assert result[2].timestamp == datetime(2023, 1, 1, 0, 30, tzinfo=UTC)
        assert result[3].timestamp == datetime(2023, 1, 1, 0, 45, tzinfo=UTC)

    async def test_process_multiple_documents(
        self,
        processor: GlMarketDocumentProcessor,
        sample_document: GlMarketDocument,
    ) -> None:
        """Test processing multiple GL_MarketDocuments."""
        # Create second document with different mRID
        second_document = GlMarketDocument(**sample_document.model_dump())
        second_document.mRID = "DOC987654321"

        result = await processor.process([sample_document, second_document])

        assert len(result) == 8  # 4 points * 2 documents

        # Check that we have points from both documents
        doc_mrids = {point.document_mrid for point in result}
        assert doc_mrids == {"DOC123456789", "DOC987654321"}

    async def test_process_empty_list(
        self, processor: GlMarketDocumentProcessor
    ) -> None:
        """Test processing empty document list."""
        result = await processor.process([])
        assert result == []

    async def test_process_invalid_input_type(
        self, processor: GlMarketDocumentProcessor
    ) -> None:
        """Test validation error for invalid input type."""
        with pytest.raises(DataValidationError) as exc_info:
            await processor.process("not_a_list")  # type: ignore[arg-type]

        assert "Input data must be a list" in str(exc_info.value)
        assert exc_info.value.field == "raw_data"

    async def test_document_type_mapping_success(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test ProcessType + DocumentType combination to EnergyDataType mapping."""
        # Test all supported mappings
        test_cases = [
            (
                ProcessType.DAY_AHEAD,
                DocumentType.SYSTEM_TOTAL_LOAD,
                EnergyDataType.DAY_AHEAD,
            ),
            (
                ProcessType.REALISED,
                DocumentType.SYSTEM_TOTAL_LOAD,
                EnergyDataType.ACTUAL,
            ),
            (
                ProcessType.WEEK_AHEAD,
                DocumentType.SYSTEM_TOTAL_LOAD,
                EnergyDataType.WEEK_AHEAD,
            ),
            (
                ProcessType.MONTH_AHEAD,
                DocumentType.SYSTEM_TOTAL_LOAD,
                EnergyDataType.MONTH_AHEAD,
            ),
            (
                ProcessType.YEAR_AHEAD,
                DocumentType.SYSTEM_TOTAL_LOAD,
                EnergyDataType.YEAR_AHEAD,
            ),
            (
                ProcessType.YEAR_AHEAD,
                DocumentType.LOAD_FORECAST_MARGIN,
                EnergyDataType.FORECAST_MARGIN,
            ),
        ]

        for process_type, document_type, expected_energy_type in test_cases:
            result = processor._map_document_to_energy_data_type(
                process_type, document_type
            )
            assert result == expected_energy_type

    async def test_document_type_mapping_unsupported(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test error handling for unsupported ProcessType + DocumentType combination."""
        with pytest.raises(MappingError) as exc_info:
            processor._map_document_to_energy_data_type(
                ProcessType.INTRA_DAY_INCREMENTAL, DocumentType.SYSTEM_TOTAL_LOAD
            )

        error = exc_info.value
        assert "Unsupported ProcessType+DocumentType combination: A02+A65" in str(error)
        assert error.source_code == "A02+A65"
        assert error.source_type == "ProcessType+DocumentType"
        assert error.target_type == "EnergyDataType"

    async def test_area_code_extraction_success(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test area code extraction using AreaCode.get_country_code() method."""
        test_cases = [
            (AreaCode.GERMANY, "DE"),
            (AreaCode.FRANCE, "FR"),
            (AreaCode.NETHERLANDS, "NL"),
            (AreaCode.AUSTRIA, "AT"),
            (AreaCode.BELGIUM, "BE"),
        ]

        for area_code, expected_country in test_cases:
            # Create a DomainMRID with the area code
            domain_mrid = DomainMRID(area_code=area_code)
            result = processor._extract_area_code(domain_mrid)
            assert result == expected_country

    async def test_timestamp_calculation_15min_resolution(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test timestamp calculation for 15-minute resolution."""
        period_start = datetime(2023, 1, 1, 0, 0, tzinfo=UTC)

        # Test positions 1-4 (1-based)
        expected_timestamps = [
            datetime(2023, 1, 1, 0, 0, tzinfo=UTC),  # Position 1
            datetime(2023, 1, 1, 0, 15, tzinfo=UTC),  # Position 2
            datetime(2023, 1, 1, 0, 30, tzinfo=UTC),  # Position 3
            datetime(2023, 1, 1, 0, 45, tzinfo=UTC),  # Position 4
        ]

        for position, expected_timestamp in enumerate(expected_timestamps, 1):
            result = processor._calculate_point_timestamp(
                period_start=period_start,
                resolution="PT15M",
                position=position,
            )
            assert result == expected_timestamp

    async def test_timestamp_calculation_60min_resolution(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test timestamp calculation for 60-minute resolution."""
        period_start = datetime(2023, 1, 1, 0, 0, tzinfo=UTC)

        result = processor._calculate_point_timestamp(
            period_start=period_start,
            resolution="PT60M",
            position=2,
        )

        expected = datetime(2023, 1, 1, 1, 0, tzinfo=UTC)
        assert result == expected

    async def test_timestamp_calculation_hour_format(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test timestamp calculation for hour format (PT1H)."""
        period_start = datetime(2023, 1, 1, 0, 0, tzinfo=UTC)

        result = processor._calculate_point_timestamp(
            period_start=period_start,
            resolution="PT1H",
            position=3,
        )

        expected = datetime(2023, 1, 1, 2, 0, tzinfo=UTC)
        assert result == expected

    async def test_timestamp_calculation_mixed_format(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test timestamp calculation for mixed hour/minute format."""
        period_start = datetime(2023, 1, 1, 0, 0, tzinfo=UTC)

        result = processor._calculate_point_timestamp(
            period_start=period_start,
            resolution="PT1H30M",  # 90 minutes
            position=2,
        )

        expected = datetime(2023, 1, 1, 1, 30, tzinfo=UTC)
        assert result == expected

    async def test_timestamp_calculation_daily_resolution(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test timestamp calculation for daily resolution (P1D)."""
        period_start = datetime(2023, 1, 1, 0, 0, tzinfo=UTC)

        # Test first few days
        test_cases = [
            (1, datetime(2023, 1, 1, 0, 0, tzinfo=UTC)),  # Position 1 = start
            (2, datetime(2023, 1, 2, 0, 0, tzinfo=UTC)),  # Position 2 = +1 day
            (7, datetime(2023, 1, 7, 0, 0, tzinfo=UTC)),  # Position 7 = +6 days
        ]

        for position, expected_timestamp in test_cases:
            result = processor._calculate_point_timestamp(
                period_start=period_start,
                resolution="P1D",
                position=position,
            )
            assert result == expected_timestamp

    async def test_timestamp_calculation_yearly_resolution(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test timestamp calculation for yearly resolution (P1Y)."""
        period_start = datetime(2023, 1, 1, 0, 0, tzinfo=UTC)

        result = processor._calculate_point_timestamp(
            period_start=period_start,
            resolution="P1Y",
            position=2,  # Second year
        )

        # Should add exactly 1 year using relativedelta (position 2 = offset 1)
        # This properly handles leap years and calendar complexities
        expected = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)  # Exactly 1 year later
        assert result == expected

    async def test_iso_duration_parsing_success(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test ISO 8601 duration parsing to components for all supported formats."""
        from app.processors.gl_market_document_processor import DurationComponents

        test_cases = [
            # Time-only durations
            ("PT15M", DurationComponents(minutes=15)),
            ("PT60M", DurationComponents(minutes=60)),
            ("PT1H", DurationComponents(hours=1)),
            ("PT2H", DurationComponents(hours=2)),
            ("PT1H30M", DurationComponents(hours=1, minutes=30)),
            ("PT2H15M", DurationComponents(hours=2, minutes=15)),
            # Date-only durations
            ("P1D", DurationComponents(days=1)),
            ("P7D", DurationComponents(days=7)),
            ("P1Y", DurationComponents(years=1)),
            ("P1M", DurationComponents(months=1)),
            # Combined date and time durations
            ("P1DT1H", DurationComponents(days=1, hours=1)),
            ("P1DT30M", DurationComponents(days=1, minutes=30)),
            ("P1YT15M", DurationComponents(years=1, minutes=15)),
        ]

        for duration_str, expected_components in test_cases:
            result = processor._parse_iso_duration_to_components(duration_str)
            assert result == expected_components

    async def test_iso_duration_parsing_invalid_format(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test error handling for invalid ISO duration format."""
        # Test cases that fail format validation
        invalid_format_durations = ["15M", "T1H", "INVALID", ""]
        for duration in invalid_format_durations:
            with pytest.raises(ValueError, match="Invalid ISO 8601 duration format"):
                processor._parse_iso_duration_to_components(duration)

        # Test cases that fail component parsing validation
        empty_component_durations = ["P", "PT"]
        for duration in empty_component_durations:
            with pytest.raises(
                ValueError, match="Could not parse any duration components"
            ):
                processor._parse_iso_duration_to_components(duration)

    async def test_timestamp_calculation_error_handling(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test error handling in timestamp calculation."""
        period_start = datetime(2023, 1, 1, 0, 0, tzinfo=UTC)

        with pytest.raises(TimestampCalculationError) as exc_info:
            processor._calculate_point_timestamp(
                period_start=period_start,
                resolution="INVALID",
                position=1,
            )

        error = exc_info.value
        assert error.resolution == "INVALID"
        assert error.position == 1

    async def test_document_with_none_values(
        self,
        processor: GlMarketDocumentProcessor,
        sample_document: GlMarketDocument,
    ) -> None:
        """Test handling of points with None values."""
        # Add points with None values
        sample_document.timeSeries.period.points.extend(
            [
                LoadPoint(position=None, quantity=100.0),  # None position
                LoadPoint(position=5, quantity=None),  # None quantity
                LoadPoint(position=6, quantity=105.5),  # Valid point
            ]
        )

        result = await processor.process([sample_document])

        # Should have 4 original points + 1 valid additional point = 5 total
        assert len(result) == 5

        # Last point should be the valid one with position 6
        last_point = result[-1]
        assert last_point.position == 6
        assert last_point.quantity == Decimal("105.5")

    async def test_transformation_error_propagation(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test that transformation errors are properly wrapped."""
        # Create invalid document that will cause transformation error
        invalid_document = Mock(spec=GlMarketDocument)
        invalid_document.mRID = "INVALID_DOC"
        invalid_document.processType = None  # This will cause AttributeError

        with pytest.raises(TransformationError) as exc_info:
            await processor.process([invalid_document])

        error = exc_info.value
        assert "Failed to process document INVALID_DOC" in str(error)
        assert error.processor_type == "GlMarketDocumentProcessor"
        assert error.operation == "document_processing"
        assert error.context["document_mrid"] == "INVALID_DOC"

    async def test_forecast_margin_document_processing(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test processing of year-ahead forecast margin documents."""
        # Create forecast margin document with different DocumentType
        points = [LoadPoint(position=1, quantity=500.0)]

        time_interval = LoadTimeInterval(
            start=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            end=datetime(2023, 1, 1, 1, 0, tzinfo=UTC),
        )

        period = LoadPeriod(
            timeInterval=time_interval,
            resolution="PT60M",
            points=points,
        )

        time_series = LoadTimeSeries(
            mRID="TS_FORECAST_MARGIN",
            businessType=BusinessType.CONSUMPTION,
            objectAggregation=ObjectAggregation.AGGREGATED,
            outBiddingZoneDomainMRID=DomainMRID(area_code=AreaCode.GERMANY),
            quantityMeasureUnitName="MW",
            curveType=CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK,
            period=period,
        )

        document = GlMarketDocument(
            mRID="DOC_FORECAST_MARGIN_TEST",
            revisionNumber=1,
            type=DocumentType.LOAD_FORECAST_MARGIN,  # A70 - Forecast Margin DocumentType
            processType=ProcessType.YEAR_AHEAD,  # A33 - Year Ahead ProcessType
            senderMarketParticipantMRID=MarketParticipantMRID(
                value="10X1001A1001A450", coding_scheme=None
            ),
            senderMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
            receiverMarketParticipantMRID=MarketParticipantMRID(
                value="10X1001A1001A450", coding_scheme=None
            ),
            receiverMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
            createdDateTime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
            timePeriodTimeInterval=time_interval,
            timeSeries=time_series,
        )

        result = await processor.process([document])

        # Verify forecast margin data type mapping
        assert len(result) == 1
        point = result[0]
        assert point.data_type == EnergyDataType.FORECAST_MARGIN
        assert point.area_code == "DE"
        assert point.document_mrid == "DOC_FORECAST_MARGIN_TEST"
        assert point.quantity == Decimal("500.0")

    async def test_timestamp_calculation_leap_year_accuracy(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test that yearly calculations properly handle leap years."""
        # Start in a leap year
        period_start = datetime(2020, 2, 28, 0, 0, tzinfo=UTC)

        result = processor._calculate_point_timestamp(
            period_start=period_start,
            resolution="P1Y",
            position=2,  # Add 1 year
        )

        # Should be Feb 28, 2021 (not affected by leap day since we started on Feb 28)
        expected = datetime(2021, 2, 28, 0, 0, tzinfo=UTC)
        assert result == expected

    async def test_timestamp_calculation_month_boundary_accuracy(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test that monthly calculations handle variable month lengths correctly."""
        # Start at end of January
        period_start = datetime(2023, 1, 31, 0, 0, tzinfo=UTC)

        result = processor._calculate_point_timestamp(
            period_start=period_start,
            resolution="P1M",  # Add 1 month
            position=2,
        )

        # relativedelta properly handles this - should be Feb 28 (since Feb has no 31st)
        expected = datetime(2023, 2, 28, 0, 0, tzinfo=UTC)
        assert result == expected

    async def test_timestamp_calculation_combined_duration(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test timestamp calculation with combined duration (date + time)."""
        period_start = datetime(2023, 1, 1, 0, 0, tzinfo=UTC)

        result = processor._calculate_point_timestamp(
            period_start=period_start,
            resolution="P1DT2H30M",  # 1 day, 2 hours, 30 minutes
            position=3,  # Position 3 = offset 2
        )

        # Should add 2 * (1 day + 2 hours + 30 minutes) = 2 days, 5 hours
        expected = datetime(2023, 1, 3, 5, 0, tzinfo=UTC)
        assert result == expected
