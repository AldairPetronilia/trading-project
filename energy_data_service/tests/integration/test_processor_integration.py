"""Integration tests for processor with real data scenarios."""

from datetime import UTC, datetime, timezone
from decimal import Decimal

import pytest
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


class TestProcessorIntegration:
    """Integration tests for GL_MarketDocument processor with realistic data."""

    @pytest.fixture
    def processor(self) -> GlMarketDocumentProcessor:
        """Create processor instance for testing."""
        return GlMarketDocumentProcessor()

    @pytest.fixture
    def realistic_german_load_document(self) -> GlMarketDocument:
        """
        Create a realistic German load document similar to actual ENTSO-E data.

        This represents a typical German actual total load document with
        hourly data points for a full day.
        """
        # Create hourly data points for a full day (24 hours)
        points = [
            LoadPoint(position=i, quantity=40000 + (i * 100) + (i % 3 * 500))
            for i in range(1, 25)  # 1-24 for hourly positions
        ]

        time_interval = LoadTimeInterval(
            start=datetime(2023, 6, 15, 0, 0, tzinfo=UTC),
            end=datetime(2023, 6, 16, 0, 0, tzinfo=UTC),
        )

        period = LoadPeriod(
            timeInterval=time_interval,
            resolution="PT60M",  # Hourly resolution
            points=points,
        )

        time_series = LoadTimeSeries(
            mRID="TS_DE_LOAD_20230615",
            businessType=BusinessType.CONSUMPTION,
            objectAggregation=ObjectAggregation.AGGREGATED,
            outBiddingZoneDomainMRID=DomainMRID(area_code=AreaCode.GERMANY),
            quantityMeasureUnitName="MW",
            curveType=CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK,
            period=period,
        )

        return GlMarketDocument(
            mRID="DOC_DE_LOAD_ACT_20230615_001",
            revisionNumber=1,
            type=DocumentType.SYSTEM_TOTAL_LOAD,  # Correct DocumentType for load data
            processType=ProcessType.REALISED,
            senderMarketParticipantMRID=MarketParticipantMRID(
                value="10X1001A1001A450", coding_scheme=None
            ),
            senderMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
            receiverMarketParticipantMRID=MarketParticipantMRID(
                value="10X1001A1001A450", coding_scheme=None
            ),
            receiverMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
            createdDateTime=datetime(2023, 6, 15, 6, 30, tzinfo=UTC),
            timePeriodTimeInterval=time_interval,
            timeSeries=[time_series],
        )

    @pytest.fixture
    def realistic_french_forecast_document(self) -> GlMarketDocument:
        """
        Create a realistic French day-ahead forecast document.

        This represents typical French day-ahead load forecast with
        15-minute resolution for peak hours.
        """
        # Create 15-minute data points for 4 hours (16 points)
        points = [
            LoadPoint(position=i, quantity=50000 + (i * 50) - (i % 4 * 200))
            for i in range(1, 17)  # 1-16 for 15-minute positions
        ]

        time_interval = LoadTimeInterval(
            start=datetime(2023, 6, 15, 18, 0, tzinfo=UTC),  # Peak hours
            end=datetime(2023, 6, 15, 22, 0, tzinfo=UTC),
        )

        period = LoadPeriod(
            timeInterval=time_interval,
            resolution="PT15M",  # 15-minute resolution
            points=points,
        )

        time_series = LoadTimeSeries(
            mRID="TS_FR_FORECAST_20230615",
            businessType=BusinessType.CONSUMPTION,
            objectAggregation=ObjectAggregation.AGGREGATED,
            outBiddingZoneDomainMRID=DomainMRID(area_code=AreaCode.FRANCE),
            quantityMeasureUnitName="MW",
            curveType=CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK,
            period=period,
        )

        return GlMarketDocument(
            mRID="DOC_FR_LOAD_DA_20230615_001",
            revisionNumber=2,
            type=DocumentType.SYSTEM_TOTAL_LOAD,  # Correct DocumentType for load data
            processType=ProcessType.DAY_AHEAD,
            senderMarketParticipantMRID=MarketParticipantMRID(
                value="10X1001A1001A450", coding_scheme=None
            ),
            senderMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
            receiverMarketParticipantMRID=MarketParticipantMRID(
                value="10X1001A1001A450", coding_scheme=None
            ),
            receiverMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
            createdDateTime=datetime(2023, 6, 14, 12, 0, tzinfo=UTC),
            timePeriodTimeInterval=time_interval,
            timeSeries=[time_series],
        )

    async def test_realistic_german_load_processing(
        self,
        processor: GlMarketDocumentProcessor,
        realistic_german_load_document: GlMarketDocument,
    ) -> None:
        """Test processing realistic German actual load data."""
        result = await processor.process([realistic_german_load_document])

        # Verify we got 24 hourly data points
        assert len(result) == 24

        # Verify data structure and values
        first_point = result[0]
        assert first_point.area_code == "DE"
        assert first_point.data_type == EnergyDataType.ACTUAL
        assert first_point.business_type == "A04"  # Consumption
        assert first_point.unit == "MW"
        assert first_point.resolution == "PT60M"
        assert first_point.position == 1

        # Verify timestamp progression (hourly)
        expected_timestamps = [
            datetime(2023, 6, 15, hour, 0, tzinfo=UTC) for hour in range(24)
        ]

        actual_timestamps = [point.timestamp for point in result]
        assert actual_timestamps == expected_timestamps

        # Verify quantity values are reasonable for German load
        quantities = [point.quantity for point in result]
        assert all(30000 <= q <= 50000 for q in quantities)  # Typical German load range

        # Verify all points have same document metadata
        assert all(p.document_mrid == "DOC_DE_LOAD_ACT_20230615_001" for p in result)
        assert all(p.revision_number == 1 for p in result)
        assert all(p.data_source == "entsoe" for p in result)

    async def test_realistic_french_forecast_processing(
        self,
        processor: GlMarketDocumentProcessor,
        realistic_french_forecast_document: GlMarketDocument,
    ) -> None:
        """Test processing realistic French day-ahead forecast data."""
        result = await processor.process([realistic_french_forecast_document])

        # Verify we got 16 quarter-hourly data points
        assert len(result) == 16

        # Verify data structure and values
        first_point = result[0]
        assert first_point.area_code == "FR"
        assert first_point.data_type == EnergyDataType.DAY_AHEAD
        assert first_point.business_type == "A04"  # Consumption
        assert first_point.unit == "MW"
        assert first_point.resolution == "PT15M"
        assert first_point.revision_number == 2

        # Verify timestamp progression (15-minute intervals)
        expected_timestamps = [
            datetime(2023, 6, 15, 18 + hour_offset, minute, tzinfo=UTC)
            for hour_offset in range(4)  # 4 hours
            for minute in [0, 15, 30, 45]  # 15-minute intervals
        ]

        actual_timestamps = [point.timestamp for point in result]
        assert actual_timestamps == expected_timestamps

        # Verify quantities are in reasonable range for French load
        quantities = [point.quantity for point in result]
        assert all(45000 <= q <= 55000 for q in quantities)

    async def test_multi_country_processing(
        self,
        processor: GlMarketDocumentProcessor,
        realistic_german_load_document: GlMarketDocument,
        realistic_french_forecast_document: GlMarketDocument,
    ) -> None:
        """Test processing multiple documents from different countries."""
        result = await processor.process(
            [
                realistic_german_load_document,
                realistic_french_forecast_document,
            ]
        )

        # Verify total count (24 German + 16 French = 40 points)
        assert len(result) == 40

        # Verify we have data from both countries
        area_codes = {point.area_code for point in result}
        assert area_codes == {"DE", "FR"}

        # Verify we have both data types
        data_types = {point.data_type for point in result}
        assert data_types == {EnergyDataType.ACTUAL, EnergyDataType.DAY_AHEAD}

        # Verify document separation
        german_points = [p for p in result if p.area_code == "DE"]
        french_points = [p for p in result if p.area_code == "FR"]

        assert len(german_points) == 24
        assert len(french_points) == 16

        # Verify different resolutions
        german_resolutions = {p.resolution for p in german_points}
        french_resolutions = {p.resolution for p in french_points}

        assert german_resolutions == {"PT60M"}
        assert french_resolutions == {"PT15M"}

    async def test_large_dataset_performance(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test performance with a large dataset (1000+ points)."""
        # Create documents with many points to test performance
        documents = []

        for doc_idx in range(5):  # 5 documents
            points = [
                LoadPoint(position=i, quantity=1000.0 + i)
                for i in range(1, 201)  # 200 points each = 1000 total
            ]

            time_interval = LoadTimeInterval(
                start=datetime(2023, 6, 15 + doc_idx, 0, 0, tzinfo=UTC),
                end=datetime(2023, 6, 15 + doc_idx, 12, 0, tzinfo=UTC),
            )

            period = LoadPeriod(
                timeInterval=time_interval,
                resolution="PT1H",
                points=points,
            )

            time_series = LoadTimeSeries(
                mRID=f"TS_PERF_TEST_{doc_idx}",
                businessType=BusinessType.CONSUMPTION,
                objectAggregation=ObjectAggregation.AGGREGATED,
                outBiddingZoneDomainMRID=DomainMRID(
                    area_code=AreaCode.GERMANY
                ),  # Use consistent area for test
                quantityMeasureUnitName="MW",
                curveType=CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK,
                period=period,
            )

            document = GlMarketDocument(
                mRID=f"DOC_PERF_TEST_{doc_idx}",
                revisionNumber=1,
                type=DocumentType.SYSTEM_TOTAL_LOAD,
                processType=ProcessType.REALISED,
                senderMarketParticipantMRID=MarketParticipantMRID(
                    value="10X1001A1001A450", coding_scheme=None
                ),
                senderMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
                receiverMarketParticipantMRID=MarketParticipantMRID(
                    value="10X1001A1001A450", coding_scheme=None
                ),
                receiverMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
                createdDateTime=datetime(2023, 6, 15, 12, 0, tzinfo=UTC),
                timePeriodTimeInterval=time_interval,
                timeSeries=[time_series],
            )
            documents.append(document)

        # Process large dataset
        result = await processor.process(documents)

        # Verify we processed all points correctly
        assert len(result) == 1000  # 5 docs * 200 points each

        # Verify data integrity
        document_mrids = {point.document_mrid for point in result}
        expected_mrids = {f"DOC_PERF_TEST_{i}" for i in range(5)}
        assert document_mrids == expected_mrids

        # Verify all points have valid data
        assert all(isinstance(point.quantity, Decimal) for point in result)
        assert all(
            point.area_code == "DE" for point in result
        )  # All use Germany for consistency
        assert all(point.data_type == EnergyDataType.ACTUAL for point in result)

    async def test_edge_case_data_scenarios(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test edge cases and boundary conditions."""
        # Create document with extreme values and edge cases
        points = [
            LoadPoint(position=1, quantity=0.0),  # Zero quantity
            LoadPoint(position=2, quantity=999999.999),  # Very large quantity
            LoadPoint(position=3, quantity=0.001),  # Very small quantity
        ]

        time_interval = LoadTimeInterval(
            start=datetime(2023, 12, 31, 23, 0, tzinfo=UTC),  # Year boundary
            end=datetime(2024, 1, 1, 0, 30, tzinfo=UTC),
        )

        period = LoadPeriod(
            timeInterval=time_interval,
            resolution="PT15M",
            points=points,
        )

        time_series = LoadTimeSeries(
            mRID="TS_EDGE_CASE_TEST",
            businessType=BusinessType.CONSUMPTION,
            objectAggregation=ObjectAggregation.AGGREGATED,
            outBiddingZoneDomainMRID=DomainMRID(
                area_code=AreaCode.AUSTRIA
            ),  # Use real area code for edge case test
            quantityMeasureUnitName="MWh",
            curveType=CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK,
            period=period,
        )

        document = GlMarketDocument(
            mRID="DOC_EDGE_CASE_TEST_2023",
            revisionNumber=999,  # High revision number
            type=DocumentType.SYSTEM_TOTAL_LOAD,
            processType=ProcessType.YEAR_AHEAD,
            senderMarketParticipantMRID=MarketParticipantMRID(
                value="10X1001A1001A450", coding_scheme=None
            ),
            senderMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
            receiverMarketParticipantMRID=MarketParticipantMRID(
                value="10X1001A1001A450", coding_scheme=None
            ),
            receiverMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
            createdDateTime=datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC),
            timePeriodTimeInterval=time_interval,
            timeSeries=[time_series],
        )

        result = await processor.process([document])

        # Verify edge case handling
        assert len(result) == 3

        # Verify extreme values are preserved
        quantities = [point.quantity for point in result]
        assert quantities[0] == Decimal("0.0")
        assert quantities[1] == Decimal("999999.999")
        assert quantities[2] == Decimal("0.001")

        # Verify year boundary timestamp calculation
        expected_timestamps = [
            datetime(2023, 12, 31, 23, 0, tzinfo=UTC),
            datetime(2023, 12, 31, 23, 15, tzinfo=UTC),
            datetime(2023, 12, 31, 23, 30, tzinfo=UTC),
        ]

        actual_timestamps = [point.timestamp for point in result]
        assert actual_timestamps == expected_timestamps

        # Verify edge case metadata
        assert all(point.area_code == "AT" for point in result)  # Austria area code
        assert all(point.data_type == EnergyDataType.YEAR_AHEAD for point in result)
        assert all(point.revision_number == 999 for point in result)
        assert all(point.unit == "MWh" for point in result)

    async def test_end_to_end_multiple_time_series(
        self,
        processor: GlMarketDocumentProcessor,
    ) -> None:
        """Test complete pipeline with multiple TimeSeries response (Phase 3 requirement)."""
        # Create first TimeSeries (short period - 1 hour)
        points_ts1 = [
            LoadPoint(position=1, quantity=42000.0),
        ]

        time_interval_ts1 = LoadTimeInterval(
            start=datetime(2025, 8, 2, 14, 0, tzinfo=UTC),
            end=datetime(2025, 8, 2, 15, 0, tzinfo=UTC),
        )

        period_ts1 = LoadPeriod(
            timeInterval=time_interval_ts1,
            resolution="PT60M",
            points=points_ts1,
        )

        time_series_1 = LoadTimeSeries(
            mRID="1",
            businessType=BusinessType.CONSUMPTION,
            objectAggregation=ObjectAggregation.AGGREGATED,
            outBiddingZoneDomainMRID=DomainMRID(area_code=AreaCode.GERMANY),
            quantityMeasureUnitName="MW",
            curveType=CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK,
            period=period_ts1,
        )

        points_ts2 = [
            LoadPoint(position=i, quantity=41000.0 + (i * 100)) for i in range(1, 84)
        ]

        time_interval_ts2 = LoadTimeInterval(
            start=datetime(2025, 8, 2, 14, 30, tzinfo=UTC),
            end=datetime(2025, 8, 3, 11, 15, tzinfo=UTC),
        )

        period_ts2 = LoadPeriod(
            timeInterval=time_interval_ts2,
            resolution="PT15M",
            points=points_ts2,
        )

        time_series_2 = LoadTimeSeries(
            mRID="2",
            businessType=BusinessType.CONSUMPTION,
            objectAggregation=ObjectAggregation.AGGREGATED,
            outBiddingZoneDomainMRID=DomainMRID(area_code=AreaCode.GERMANY),
            quantityMeasureUnitName="MW",
            curveType=CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK,
            period=period_ts2,
        )

        document = GlMarketDocument(
            mRID="68e1b9a516a44fcc9a4f36981209696b",
            revisionNumber=1,
            type=DocumentType.SYSTEM_TOTAL_LOAD,
            processType=ProcessType.REALISED,
            senderMarketParticipantMRID=MarketParticipantMRID(
                value="10X1001A1001A450", coding_scheme=None
            ),
            senderMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
            receiverMarketParticipantMRID=MarketParticipantMRID(
                value="10X1001A1001A450", coding_scheme=None
            ),
            receiverMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
            createdDateTime=datetime(2025, 8, 2, 15, 0, tzinfo=UTC),
            timePeriodTimeInterval=LoadTimeInterval(
                start=datetime(2025, 8, 2, 14, 0, tzinfo=UTC),
                end=datetime(2025, 8, 3, 11, 15, tzinfo=UTC),
            ),
            timeSeries=[time_series_1, time_series_2],
        )

        result = await processor.process([document])

        expected_total_points = 1 + 83
        assert len(result) == expected_total_points, (
            f"Expected {expected_total_points} points, got {len(result)}. "
            "Multiple TimeSeries processing failed!"
        )

        time_series_mrids = {point.time_series_mrid for point in result}
        assert time_series_mrids == {"1", "2"}, (
            f"Expected TimeSeries mRIDs ['1', '2'], got {time_series_mrids}"
        )

        ts1_points = [p for p in result if p.time_series_mrid == "1"]
        ts2_points = [p for p in result if p.time_series_mrid == "2"]

        assert len(ts1_points) == 1, (
            f"TimeSeries 1 should have 1 point, got {len(ts1_points)}"
        )
        assert len(ts2_points) == 83, (
            f"TimeSeries 2 should have 83 points, got {len(ts2_points)}"
        )

        assert all(
            p.document_mrid == "68e1b9a516a44fcc9a4f36981209696b" for p in result
        )
        assert all(p.area_code == "DE" for p in result)
        assert all(p.data_type == EnergyDataType.ACTUAL for p in result)
        assert all(p.data_source == "entsoe" for p in result)

        ts1_resolution = {p.resolution for p in ts1_points}
        ts2_resolution = {p.resolution for p in ts2_points}
        assert ts1_resolution == {"PT60M"}
        assert ts2_resolution == {"PT15M"}

        ts1_timestamps = [p.timestamp for p in ts1_points]
        ts2_timestamps = [p.timestamp for p in ts2_points]

        assert ts1_timestamps == [datetime(2025, 8, 2, 14, 0, tzinfo=UTC)]
        assert ts2_timestamps[0] == datetime(2025, 8, 2, 14, 30, tzinfo=UTC)
        assert ts2_timestamps[-1] == datetime(2025, 8, 3, 11, 0, tzinfo=UTC)
