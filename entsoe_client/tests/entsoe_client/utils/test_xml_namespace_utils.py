"""Tests for XML namespace utilities."""

import pytest

from entsoe_client.utils.xml_namespace_utils import remove_xml_namespaces


class TestXmlNamespaceUtils:
    """Test XML namespace utility functions."""

    def test_remove_xml_namespaces_simple(self) -> None:
        """Test namespace removal from simple XML."""
        xml_with_namespace = """<?xml version="1.0" encoding="UTF-8"?>
        <Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
            <mRID>test-123</mRID>
            <type>A44</type>
        </Publication_MarketDocument>"""

        result = remove_xml_namespaces(xml_with_namespace)

        # Should not contain xmlns declaration
        assert "xmlns=" not in result
        # Should contain the elements
        assert "<Publication_MarketDocument>" in result
        assert "<mRID>test-123</mRID>" in result
        assert "<type>A44</type>" in result

    def test_remove_xml_namespaces_complex(self) -> None:
        """Test namespace removal from complex XML with nested elements."""
        xml_with_namespace = """<?xml version="1.0" encoding="UTF-8"?>
        <Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:0">
            <mRID>flow-123</mRID>
            <TimeSeries>
                <businessType>A66</businessType>
                <quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>
                <Period>
                    <Point>
                        <position>1</position>
                        <quantity>125.5</quantity>
                    </Point>
                </Period>
            </TimeSeries>
        </Publication_MarketDocument>"""

        result = remove_xml_namespaces(xml_with_namespace)

        # Should not contain xmlns declaration
        assert "xmlns=" not in result
        # Should contain all nested elements without namespaces
        assert "<Publication_MarketDocument>" in result
        assert "<TimeSeries>" in result
        assert "<businessType>A66</businessType>" in result
        assert "<quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>" in result
        assert "<Point>" in result
        assert "<quantity>125.5</quantity>" in result

    def test_remove_xml_namespaces_invalid_xml(self) -> None:
        """Test namespace removal with invalid XML."""
        invalid_xml = "<unclosed_tag>content"

        with pytest.raises(ValueError, match="Failed to parse XML content"):
            remove_xml_namespaces(invalid_xml)
