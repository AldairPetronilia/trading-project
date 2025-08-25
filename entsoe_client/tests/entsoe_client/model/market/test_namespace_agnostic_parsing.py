"""Tests for namespace-agnostic publication market document parsing."""

from entsoe_client.model.market.publication_market_document import (
    PublicationMarketDocument,
)
from entsoe_client.utils.xml_namespace_utils import remove_xml_namespaces


class TestNamespaceAgnosticParsing:
    """Test parsing of publication documents with different namespaces."""

    def test_parse_market_prices_7_3_namespace_stripped(self) -> None:
        """Test parsing market prices XML (7:3 namespace) after namespace stripping."""
        xml_with_namespace = """<?xml version="1.0" encoding="UTF-8"?>
        <Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
            <mRID>price-doc-123</mRID>
            <revisionNumber>1</revisionNumber>
            <type>A44</type>
            <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
            <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
            <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
            <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
            <createdDateTime>2016-05-10T10:54:18Z</createdDateTime>
            <period.timeInterval>
                <start>2015-12-31T23:00Z</start>
                <end>2016-12-31T23:00Z</end>
            </period.timeInterval>
            <TimeSeries>
                <mRID>1</mRID>
                <businessType>A62</businessType>
                <in_Domain.mRID codingScheme="A01">10YCZ-CEPS-----N</in_Domain.mRID>
                <out_Domain.mRID codingScheme="A01">10YCZ-CEPS-----N</out_Domain.mRID>
                <price_Measure_Unit.name>EUR</price_Measure_Unit.name>
                <curveType>A01</curveType>
                <Period>
                    <timeInterval>
                        <start>2015-12-31T23:00Z</start>
                        <end>2016-01-01T23:00Z</end>
                    </timeInterval>
                    <resolution>PT60M</resolution>
                    <Point>
                        <position>1</position>
                        <price.amount>45.67</price.amount>
                    </Point>
                </Period>
            </TimeSeries>
        </Publication_MarketDocument>"""

        # Strip namespace and parse
        cleaned_xml = remove_xml_namespaces(xml_with_namespace)
        doc = PublicationMarketDocument.from_xml(cleaned_xml.encode())

        # Verify document structure
        assert doc.mRID == "price-doc-123"
        assert doc.revisionNumber == 1
        assert doc.type.code == "A44"  # Price document

        # Verify time series
        assert len(doc.timeSeries) == 1
        ts = doc.timeSeries[0]
        assert ts.businessType.code == "A62"  # Day-ahead prices
        assert ts.price_measure_unit_name == "EUR"

        # Verify point data
        assert ts.period.points[0].position == 1
        assert ts.period.points[0].price_amount == 45.67
        assert ts.period.points[0].quantity is None  # Should be None for price data

    def test_parse_physical_flows_7_0_namespace_stripped(self) -> None:
        """Test parsing physical flows XML (7:0 namespace) after namespace stripping."""
        xml_with_namespace = """<?xml version="1.0" encoding="UTF-8"?>
        <Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:0">
            <mRID>flow-doc-456</mRID>
            <revisionNumber>1</revisionNumber>
            <type>A11</type>
            <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
            <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
            <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
            <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
            <createdDateTime>2016-05-10T10:54:18Z</createdDateTime>
            <period.timeInterval>
                <start>2015-12-31T23:00Z</start>
                <end>2016-12-31T23:00Z</end>
            </period.timeInterval>
            <TimeSeries>
                <mRID>1</mRID>
                <businessType>A66</businessType>
                <in_Domain.mRID codingScheme="A01">10YCZ-CEPS-----N</in_Domain.mRID>
                <out_Domain.mRID codingScheme="A01">10YSK-SEPS-----K</out_Domain.mRID>
                <quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>
                <curveType>A01</curveType>
                <Period>
                    <timeInterval>
                        <start>2015-12-31T23:00Z</start>
                        <end>2016-01-01T23:00Z</end>
                    </timeInterval>
                    <resolution>PT60M</resolution>
                    <Point>
                        <position>1</position>
                        <quantity>125.5</quantity>
                    </Point>
                    <Point>
                        <position>2</position>
                        <quantity>89.3</quantity>
                    </Point>
                </Period>
            </TimeSeries>
        </Publication_MarketDocument>"""

        # Strip namespace and parse
        cleaned_xml = remove_xml_namespaces(xml_with_namespace)
        doc = PublicationMarketDocument.from_xml(cleaned_xml.encode())

        # Verify document structure
        assert doc.mRID == "flow-doc-456"
        assert doc.revisionNumber == 1
        assert doc.type.code == "A11"  # Aggregated energy data report

        # Verify time series
        assert len(doc.timeSeries) == 1
        ts = doc.timeSeries[0]
        assert ts.businessType.code == "A66"  # Physical flows
        assert ts.quantity_measure_unit_name == "MAW"

        # Verify directional domains (different for flows)
        assert ts.in_domain_mRID.area_code.code == "10YCZ-CEPS-----N"  # Czech Republic
        assert ts.out_domain_mRID.area_code.code == "10YSK-SEPS-----K"  # Slovakia

        # Verify point data
        assert len(ts.period.points) == 2
        assert ts.period.points[0].position == 1
        assert ts.period.points[0].quantity == 125.5
        assert ts.period.points[0].price_amount is None  # Should be None for flow data

        assert ts.period.points[1].position == 2
        assert ts.period.points[1].quantity == 89.3

    def test_namespace_agnostic_models_handle_both_data_types(self) -> None:
        """Test that namespace-agnostic models can handle both price and quantity data."""
        xml_mixed_data = """<?xml version="1.0" encoding="UTF-8"?>
        <Publication_MarketDocument>
            <mRID>mixed-doc-789</mRID>
            <revisionNumber>1</revisionNumber>
            <type>A44</type>
            <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
            <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
            <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
            <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
            <createdDateTime>2016-05-10T10:54:18Z</createdDateTime>
            <period.timeInterval>
                <start>2015-12-31T23:00Z</start>
                <end>2016-12-31T23:00Z</end>
            </period.timeInterval>
            <TimeSeries>
                <mRID>1</mRID>
                <businessType>A62</businessType>
                <in_Domain.mRID codingScheme="A01">10YCZ-CEPS-----N</in_Domain.mRID>
                <out_Domain.mRID codingScheme="A01">10YCZ-CEPS-----N</out_Domain.mRID>
                <price_Measure_Unit.name>EUR</price_Measure_Unit.name>
                <quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>
                <curveType>A01</curveType>
                <Period>
                    <timeInterval>
                        <start>2015-12-31T23:00Z</start>
                        <end>2016-01-01T23:00Z</end>
                    </timeInterval>
                    <resolution>PT60M</resolution>
                    <Point>
                        <position>1</position>
                        <price.amount>45.67</price.amount>
                        <quantity>125.5</quantity>
                    </Point>
                </Period>
            </TimeSeries>
        </Publication_MarketDocument>"""

        # Parse directly (no namespace to strip)
        doc = PublicationMarketDocument.from_xml(xml_mixed_data.encode())

        # Verify both price and quantity fields are handled
        ts = doc.timeSeries[0]
        assert ts.price_measure_unit_name == "EUR"
        assert ts.quantity_measure_unit_name == "MAW"

        point = ts.period.points[0]
        assert point.price_amount == 45.67
        assert point.quantity == 125.5
