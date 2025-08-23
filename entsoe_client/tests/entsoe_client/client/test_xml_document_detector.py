import pytest

from entsoe_client.client.xml_document_detector import (
    XmlDocumentDetector,
    XmlDocumentType,
)
from entsoe_client.exceptions.entsoe_api_request_error import EntsoEApiRequestError


class TestXmlDocumentDetector:
    """Test suite for XmlDocumentDetector XML document type detection."""

    @pytest.fixture
    def gl_market_document_xml(self) -> str:
        """Sample GL_MarketDocument XML."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
    <mRID>sample-id</mRID>
    <type>A65</type>
    <!-- Additional content -->
</GL_MarketDocument>"""

    @pytest.fixture
    def acknowledgement_document_xml(self) -> str:
        """Sample Acknowledgement_MarketDocument XML."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0">
    <mRID>ack-id</mRID>
    <Reason>
        <code>999</code>
        <text>No data</text>
    </Reason>
</Acknowledgement_MarketDocument>"""

    @pytest.fixture
    def minimal_gl_document_xml(self) -> str:
        """Minimal GL_MarketDocument XML."""
        return "<GL_MarketDocument></GL_MarketDocument>"

    @pytest.fixture
    def minimal_acknowledgement_xml(self) -> str:
        """Minimal Acknowledgement_MarketDocument XML."""
        return "<Acknowledgement_MarketDocument></Acknowledgement_MarketDocument>"

    def test_detect_gl_market_document(self, gl_market_document_xml: str) -> None:
        """Test detection of GL_MarketDocument type."""
        # Act
        document_type = XmlDocumentDetector.detect_document_type(gl_market_document_xml)

        # Assert
        assert document_type == XmlDocumentType.GL_MARKET_DOCUMENT

    def test_detect_acknowledgement_document(
        self, acknowledgement_document_xml: str
    ) -> None:
        """Test detection of Acknowledgement_MarketDocument type."""
        # Act
        document_type = XmlDocumentDetector.detect_document_type(
            acknowledgement_document_xml
        )

        # Assert
        assert document_type == XmlDocumentType.ACKNOWLEDGEMENT_MARKET_DOCUMENT

    def test_detect_minimal_gl_document(self, minimal_gl_document_xml: str) -> None:
        """Test detection with minimal GL_MarketDocument."""
        # Act
        document_type = XmlDocumentDetector.detect_document_type(
            minimal_gl_document_xml
        )

        # Assert
        assert document_type == XmlDocumentType.GL_MARKET_DOCUMENT

    def test_detect_minimal_acknowledgement_document(
        self, minimal_acknowledgement_xml: str
    ) -> None:
        """Test detection with minimal Acknowledgement_MarketDocument."""
        # Act
        document_type = XmlDocumentDetector.detect_document_type(
            minimal_acknowledgement_xml
        )

        # Assert
        assert document_type == XmlDocumentType.ACKNOWLEDGEMENT_MARKET_DOCUMENT

    def test_detect_with_xml_declaration_and_whitespace(self) -> None:
        """Test detection with XML declaration and various whitespace."""
        # Arrange
        xml_with_whitespace = """  <?xml version="1.0" encoding="UTF-8"?>

        <GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
            <content/>
        </GL_MarketDocument>  """

        # Act
        document_type = XmlDocumentDetector.detect_document_type(xml_with_whitespace)

        # Assert
        assert document_type == XmlDocumentType.GL_MARKET_DOCUMENT

    def test_detect_with_attributes_in_root_element(self) -> None:
        """Test detection when root element has attributes."""
        # Arrange
        xml_with_attributes = """<GL_MarketDocument xmlns="urn:namespace" version="1.0" id="test">
            <content/>
        </GL_MarketDocument>"""

        # Act
        document_type = XmlDocumentDetector.detect_document_type(xml_with_attributes)

        # Assert
        assert document_type == XmlDocumentType.GL_MARKET_DOCUMENT

    def test_detect_with_self_closing_root_element(self) -> None:
        """Test detection with self-closing root element."""
        # Arrange
        self_closing_xml = '<Acknowledgement_MarketDocument xmlns="urn:namespace" />'

        # Act
        document_type = XmlDocumentDetector.detect_document_type(self_closing_xml)

        # Assert
        assert document_type == XmlDocumentType.ACKNOWLEDGEMENT_MARKET_DOCUMENT

    def test_detect_empty_string_raises_exception(self) -> None:
        """Test that empty string raises EntsoEApiRequestError."""
        # Act & Assert
        with pytest.raises(EntsoEApiRequestError) as exc_info:
            XmlDocumentDetector.detect_document_type("")

        assert "XML content is empty or invalid" in str(exc_info.value)

    def test_detect_none_input_raises_exception(self) -> None:
        """Test that None input raises EntsoEApiRequestError."""
        # Act & Assert
        with pytest.raises(EntsoEApiRequestError) as exc_info:
            XmlDocumentDetector.detect_document_type(None)  # type: ignore[arg-type]

        assert "XML content is empty or invalid" in str(exc_info.value)

    def test_detect_non_string_input_raises_exception(self) -> None:
        """Test that non-string input raises EntsoEApiRequestError."""
        # Act & Assert
        with pytest.raises(EntsoEApiRequestError) as exc_info:
            XmlDocumentDetector.detect_document_type(123)  # type: ignore[arg-type]

        assert "XML content is empty or invalid" in str(exc_info.value)

    def test_detect_whitespace_only_raises_exception(self) -> None:
        """Test that whitespace-only string raises EntsoEApiRequestError."""
        # Act & Assert
        with pytest.raises(EntsoEApiRequestError) as exc_info:
            XmlDocumentDetector.detect_document_type("   \n\t   ")

        assert "No XML root element found" in str(exc_info.value)

    def test_detect_no_xml_elements_raises_exception(self) -> None:
        """Test that string without XML elements raises EntsoEApiRequestError."""
        # Act & Assert
        with pytest.raises(EntsoEApiRequestError) as exc_info:
            XmlDocumentDetector.detect_document_type("This is not XML content")

        assert "No XML root element found" in str(exc_info.value)

    def test_detect_unknown_document_type_raises_exception(self) -> None:
        """Test that unknown document type raises EntsoEApiRequestError."""
        # Arrange
        unknown_xml = "<UnknownDocument><content/></UnknownDocument>"

        # Act & Assert
        with pytest.raises(EntsoEApiRequestError) as exc_info:
            XmlDocumentDetector.detect_document_type(unknown_xml)

        assert "Unsupported XML document type: UnknownDocument" in str(exc_info.value)

    def test_detect_malformed_xml_raises_exception(self) -> None:
        """Test that malformed XML raises EntsoEApiRequestError."""
        # Arrange
        malformed_xml = "<GL_MarketDocument<invalid"

        # Act & Assert
        with pytest.raises(EntsoEApiRequestError) as exc_info:
            XmlDocumentDetector.detect_document_type(malformed_xml)

        assert "No XML root element found" in str(exc_info.value)

    def test_detect_xml_with_comments_before_root(self) -> None:
        """Test detection with XML comments before root element."""
        # Arrange
        xml_with_comments = """<?xml version="1.0" encoding="UTF-8"?>
        <!-- This is a comment -->
        <!-- Another comment -->
        <GL_MarketDocument>
            <content/>
        </GL_MarketDocument>"""

        # Act
        document_type = XmlDocumentDetector.detect_document_type(xml_with_comments)

        # Assert
        assert document_type == XmlDocumentType.GL_MARKET_DOCUMENT

    def test_detect_xml_with_processing_instructions(self) -> None:
        """Test detection with XML processing instructions."""
        # Arrange
        xml_with_pi = """<?xml version="1.0" encoding="UTF-8"?>
        <?xml-stylesheet type="text/xsl" href="style.xsl"?>
        <Acknowledgement_MarketDocument>
            <content/>
        </Acknowledgement_MarketDocument>"""

        # Act
        document_type = XmlDocumentDetector.detect_document_type(xml_with_pi)

        # Assert
        assert document_type == XmlDocumentType.ACKNOWLEDGEMENT_MARKET_DOCUMENT

    @pytest.mark.parametrize(
        ("root_element", "expected_type"),
        [
            ("GL_MarketDocument", XmlDocumentType.GL_MARKET_DOCUMENT),
            (
                "Acknowledgement_MarketDocument",
                XmlDocumentType.ACKNOWLEDGEMENT_MARKET_DOCUMENT,
            ),
        ],
    )
    def test_detect_document_type_parametrized(
        self, root_element: str, expected_type: XmlDocumentType
    ) -> None:
        """Test document type detection with parametrized root elements."""
        # Arrange
        xml = f"<{root_element}></{root_element}>"

        # Act
        document_type = XmlDocumentDetector.detect_document_type(xml)

        # Assert
        assert document_type == expected_type

    def test_detect_large_xml_performance(self) -> None:
        """Test detection performance with large XML content."""
        # Arrange - Create large XML with GL_MarketDocument root
        large_content = "<large_content>" + "x" * 10000 + "</large_content>"
        large_xml = f"<GL_MarketDocument>{large_content}</GL_MarketDocument>"

        # Act - This should be fast since we only parse the root element
        document_type = XmlDocumentDetector.detect_document_type(large_xml)

        # Assert
        assert document_type == XmlDocumentType.GL_MARKET_DOCUMENT

    def test_detect_xml_with_cdata_sections(self) -> None:
        """Test detection with CDATA sections in XML."""
        # Arrange
        xml_with_cdata = """<GL_MarketDocument>
            <![CDATA[This is CDATA content]]>
            <content/>
        </GL_MarketDocument>"""

        # Act
        document_type = XmlDocumentDetector.detect_document_type(xml_with_cdata)

        # Assert
        assert document_type == XmlDocumentType.GL_MARKET_DOCUMENT

    def test_detect_xml_with_namespaced_root_element(self) -> None:
        """Test detection with namespaced root element."""
        # Arrange
        namespaced_xml = """<ns:GL_MarketDocument xmlns:ns="urn:namespace">
            <content/>
        </ns:GL_MarketDocument>"""

        # Act & Assert - This should raise exception as we don't expect namespaced roots
        with pytest.raises(EntsoEApiRequestError) as exc_info:
            XmlDocumentDetector.detect_document_type(namespaced_xml)

        assert "Unsupported XML document type: ns:GL_MarketDocument" in str(
            exc_info.value
        )

    def test_regex_pattern_compilation(self) -> None:
        """Test that the regex pattern is properly compiled."""
        # Assert
        assert XmlDocumentDetector.ROOT_ELEMENT_PATTERN is not None
        assert hasattr(XmlDocumentDetector.ROOT_ELEMENT_PATTERN, "search")

    def test_enum_values(self) -> None:
        """Test that XmlDocumentType enum has expected values."""
        # Assert
        assert XmlDocumentType.GL_MARKET_DOCUMENT.value == "GL_MarketDocument"
        assert (
            XmlDocumentType.PUBLICATION_MARKET_DOCUMENT.value
            == "Publication_MarketDocument"
        )
        assert (
            XmlDocumentType.ACKNOWLEDGEMENT_MARKET_DOCUMENT.value
            == "Acknowledgement_MarketDocument"
        )
        assert len(XmlDocumentType) == 3
