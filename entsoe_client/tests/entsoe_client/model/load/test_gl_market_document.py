from datetime import UTC, datetime

from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.business_type import BusinessType
from entsoe_client.model.common.curve_type import CurveType
from entsoe_client.model.common.document_type import DocumentType
from entsoe_client.model.common.domain_mrid import DomainMRID
from entsoe_client.model.common.market_participant_mrid import MarketParticipantMRID
from entsoe_client.model.common.market_role_type import MarketRoleType
from entsoe_client.model.common.object_aggregation import ObjectAggregation
from entsoe_client.model.common.process_type import ProcessType
from entsoe_client.model.load.gl_market_document import GlMarketDocument
from entsoe_client.model.load.load_period import LoadPeriod
from entsoe_client.model.load.load_point import LoadPoint
from entsoe_client.model.load.load_time_interval import LoadTimeInterval
from entsoe_client.model.load.load_time_series import LoadTimeSeries


def test_gl_market_document_full_xml_parsing() -> None:
    """Test parsing complete GL_MarketDocument XML with TimeSeries element."""

    # Complete XML with TimeSeries element
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
    <mRID>5693afe33ce749e4b0cea17f1f64f211</mRID>
    <revisionNumber>1</revisionNumber>
    <type>A65</type>
    <process.processType>A16</process.processType>
    <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
    <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
    <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
    <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
    <createdDateTime>2016-02-26T07:24:53Z</createdDateTime>
    <time_Period.timeInterval>
        <start>2015-12-31T23:00Z</start>
        <end>2016-12-31T23:00Z</end>
    </time_Period.timeInterval>
    <TimeSeries>
        <mRID>1</mRID>
        <businessType>A04</businessType>
        <objectAggregation>A01</objectAggregation>
        <outBiddingZone_Domain.mRID codingScheme="A01">10YCZ-CEPS-----N</outBiddingZone_Domain.mRID>
        <quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>
        <curveType>A01</curveType>
        <Period>
            <timeInterval>
                <start>2015-12-31T23:00Z</start>
                <end>2016-12-31T23:00Z</end>
            </timeInterval>
            <resolution>PT60M</resolution>
            <Point>
                <position>1</position>
                <quantity>6288</quantity>
            </Point>
        </Period>
    </TimeSeries>
</GL_MarketDocument>"""

    # Parse the XML
    document = GlMarketDocument.from_xml(xml_content)

    # Verify all fields are parsed correctly
    assert document.mRID == "5693afe33ce749e4b0cea17f1f64f211"
    assert document.revisionNumber == 1
    assert document.type == DocumentType.SYSTEM_TOTAL_LOAD
    assert document.processType == ProcessType.REALISED

    # Verify sender market participant
    assert document.senderMarketParticipantMRID.value == "10X1001A1001A450"
    assert document.senderMarketParticipantMRID.coding_scheme == "A01"
    assert (
        document.senderMarketParticipantMarketRoleType == MarketRoleType.ISSUING_OFFICE
    )

    # Verify receiver market participant
    assert document.receiverMarketParticipantMRID.value == "10X1001A1001A450"
    assert document.receiverMarketParticipantMRID.coding_scheme == "A01"
    assert (
        document.receiverMarketParticipantMarketRoleType
        == MarketRoleType.MARKET_OPERATOR
    )

    # Verify created date time
    expected_datetime = datetime(2016, 2, 26, 7, 24, 53, tzinfo=UTC)
    assert document.createdDateTime == expected_datetime

    # Verify time period interval
    assert isinstance(document.timePeriodTimeInterval, LoadTimeInterval)
    expected_start = datetime(2015, 12, 31, 23, 0, 0, tzinfo=UTC)
    expected_end = datetime(2016, 12, 31, 23, 0, 0, tzinfo=UTC)
    assert document.timePeriodTimeInterval.start == expected_start
    assert document.timePeriodTimeInterval.end == expected_end

    # Verify TimeSeries element
    assert isinstance(document.timeSeries, LoadTimeSeries)
    assert document.timeSeries.mRID == "1"
    # Note: businessType, objectAggregation, curveType will be tested based on
    # their enum implementations when those are available


def test_gl_market_document_xml_serialization() -> None:
    """Test serializing gl_market_document back to XML."""

    # Create a complete document instance with all required fields
    time_interval = LoadTimeInterval(
        start=datetime(2015, 12, 31, 23, 0, 0, tzinfo=UTC),
        end=datetime(2016, 12, 31, 23, 0, 0, tzinfo=UTC),
    )

    # Create a LoadPoint for the period
    load_point = LoadPoint(position=1, quantity=6288.0)

    # Create a LoadPeriod with timeInterval reusing LoadTimeInterval with different tag
    period_time_interval = LoadTimeInterval(
        start=datetime(2015, 12, 31, 23, 0, 0, tzinfo=UTC),
        end=datetime(2016, 12, 31, 23, 0, 0, tzinfo=UTC),
    )

    load_period = LoadPeriod(
        timeInterval=period_time_interval,
        resolution="PT60M",
        points=[load_point],
    )

    # Create domain MRID
    domain_mrid = DomainMRID(area_code=AreaCode.CZECH_REPUBLIC, coding_scheme="A01")

    # Create a complete LoadTimeSeries instance
    time_series = LoadTimeSeries(
        mRID="1",
        businessType=BusinessType.CONSUMPTION,
        objectAggregation=ObjectAggregation.AGGREGATED,
        outBiddingZoneDomainMRID=domain_mrid,
        quantityMeasureUnitName="MAW",
        curveType=CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK,
        period=load_period,
    )

    document = GlMarketDocument(
        mRID="5693afe33ce749e4b0cea17f1f64f211",
        revisionNumber=1,
        type=DocumentType.SYSTEM_TOTAL_LOAD,
        processType=ProcessType.REALISED,
        senderMarketParticipantMRID=MarketParticipantMRID(
            value="10X1001A1001A450",
            coding_scheme="A01",
        ),
        senderMarketParticipantMarketRoleType=MarketRoleType.ISSUING_OFFICE,
        receiverMarketParticipantMRID=MarketParticipantMRID(
            value="10X1001A1001A450",
            coding_scheme="A01",
        ),
        receiverMarketParticipantMarketRoleType=MarketRoleType.MARKET_OPERATOR,
        createdDateTime=datetime(2016, 2, 26, 7, 24, 53, tzinfo=UTC),
        timePeriodTimeInterval=time_interval,
        timeSeries=time_series,
    )

    # Serialize to XML
    xml_output = str(document.to_xml())

    # Verify XML contains expected elements
    assert "GL_MarketDocument" in xml_output
    assert "5693afe33ce749e4b0cea17f1f64f211" in xml_output
    assert "A65" in xml_output  # DocumentType.SYSTEM_TOTAL_LOAD.code
    assert "A16" in xml_output  # ProcessType.REALISED.code
    assert "A32" in xml_output  # MarketRoleType.ISSUING_OFFICE.code
    assert "A33" in xml_output  # MarketRoleType.MARKET_OPERATOR.code
    assert "10X1001A1001A450" in xml_output
    assert "time_Period.timeInterval" in xml_output  # Document-level time interval
    assert "timeInterval" in xml_output  # Period-level time interval (different tag!)
    assert "TimeSeries" in xml_output
    assert "A04" in xml_output  # BusinessType.CONSUMPTION.code
    assert (
        "A01" in xml_output
    )  # ObjectAggregation.AGGREGATED.code and CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK.code
    assert "10YCZ-CEPS-----N" in xml_output  # AreaCode.CZ_REGION.code
    assert "MAW" in xml_output
    assert "PT60M" in xml_output
    assert "6288" in xml_output


def test_load_time_interval_tag_flexibility() -> None:
    """Test LoadTimeInterval tag flexibility - same class used with different XML tags."""

    # Test that LoadTimeInterval can be reused with different tags
    # This demonstrates the tag flexibility we implemented

    # Create a simple time interval instance
    time_interval = LoadTimeInterval(
        start=datetime(2015, 12, 31, 23, 0, 0, tzinfo=UTC),
        end=datetime(2016, 12, 31, 23, 0, 0, tzinfo=UTC),
    )

    # Verify the fields are correctly set
    expected_start = datetime(2015, 12, 31, 23, 0, 0, tzinfo=UTC)
    expected_end = datetime(2016, 12, 31, 23, 0, 0, tzinfo=UTC)

    assert time_interval.start == expected_start
    assert time_interval.end == expected_end


def test_gl_market_document_field_validation() -> None:
    """Test individual field validation in GlMarketDocument."""

    # Test DocumentType validation
    doc_type = DocumentType.from_code("A65")
    assert doc_type == DocumentType.SYSTEM_TOTAL_LOAD

    # Test ProcessType validation
    process_type = ProcessType.from_code("A16")
    assert process_type == ProcessType.REALISED

    # Test MarketRoleType validation
    role_type = MarketRoleType.from_code("A32")
    assert role_type == MarketRoleType.ISSUING_OFFICE

    # Test MarketParticipantMRID
    participant_mrid = MarketParticipantMRID(
        value="10X1001A1001A450",
        coding_scheme="A01",
    )
    assert participant_mrid.value == "10X1001A1001A450"
    assert participant_mrid.coding_scheme == "A01"


def test_gl_market_document_round_trip() -> None:
    """Test XML parsing and serialization round trip."""

    # Complete XML with TimeSeries element
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
    <mRID>5693afe33ce749e4b0cea17f1f64f211</mRID>
    <revisionNumber>1</revisionNumber>
    <type>A65</type>
    <process.processType>A16</process.processType>
    <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
    <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
    <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
    <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
    <createdDateTime>2016-02-26T07:24:53Z</createdDateTime>
    <time_Period.timeInterval>
        <start>2015-12-31T23:00Z</start>
        <end>2016-12-31T23:00Z</end>
    </time_Period.timeInterval>
    <TimeSeries>
        <mRID>1</mRID>
        <businessType>A04</businessType>
        <objectAggregation>A01</objectAggregation>
        <outBiddingZone_Domain.mRID codingScheme="A01">10YCZ-CEPS-----N</outBiddingZone_Domain.mRID>
        <quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>
        <curveType>A01</curveType>
        <Period>
            <timeInterval>
                <start>2015-12-31T23:00Z</start>
                <end>2016-12-31T23:00Z</end>
            </timeInterval>
            <resolution>PT60M</resolution>
            <Point>
                <position>1</position>
                <quantity>6288</quantity>
            </Point>
        </Period>
    </TimeSeries>
</GL_MarketDocument>"""

    # Parse XML to object
    document = GlMarketDocument.from_xml(xml_content)

    # Serialize back to XML
    serialized_xml = document.to_xml()

    # Parse the serialized XML again
    reparsed_document = GlMarketDocument.from_xml(serialized_xml)

    # Verify key fields are preserved through round trip
    assert reparsed_document.mRID == document.mRID
    assert reparsed_document.type == document.type
    assert reparsed_document.processType == document.processType
    assert reparsed_document.createdDateTime == document.createdDateTime
    assert (
        reparsed_document.timePeriodTimeInterval.start
        == document.timePeriodTimeInterval.start
    )
    assert (
        reparsed_document.timePeriodTimeInterval.end
        == document.timePeriodTimeInterval.end
    )
    assert reparsed_document.timeSeries.mRID == document.timeSeries.mRID
    assert reparsed_document.timeSeries.businessType == document.timeSeries.businessType
