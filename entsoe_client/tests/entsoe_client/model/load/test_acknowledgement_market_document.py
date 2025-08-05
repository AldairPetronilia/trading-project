from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from entsoe_client.model.acknowledgement import (
    AcknowledgementMarketDocument,
    AcknowledgementMarketParticipant,
)


class TestAcknowledgementMarketDocument:
    """Test suite for AcknowledgementMarketDocument XML parsing and validation."""

    @pytest.fixture
    def valid_no_data_acknowledgement_xml(self) -> str:
        """Sample acknowledgement XML with reason code 999 (no data available)."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0">
    <mRID>73e41c75-ae22-4f67-9c4e-014eb0a0b4a3</mRID>
    <createdDateTime>2025-08-04T19:55:30Z</createdDateTime>
    <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
    <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
    <received_MarketDocument.createdDateTime>2025-08-04T19:55:30Z</received_MarketDocument.createdDateTime>
    <Reason>
        <code>999</code>
        <text>No matching data found for Data item Year-ahead Forecast Margin [8.1] for Period 2025-08-05T00:00Z/2025-08-06T00:00Z and Domain 10YDE-VE-------2.</text>
    </Reason>
</Acknowledgement_MarketDocument>"""

    @pytest.fixture
    def valid_error_acknowledgement_xml(self) -> str:
        """Sample acknowledgement XML with error reason code (not 999)."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0">
    <mRID>84f52d86-bf33-5g78-0d5f-125fc1b1c5b4</mRID>
    <createdDateTime>2025-08-04T20:10:15Z</createdDateTime>
    <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
    <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
    <received_MarketDocument.createdDateTime>2025-08-04T20:10:15Z</received_MarketDocument.createdDateTime>
    <Reason>
        <code>401</code>
        <text>Unauthorized access to requested data</text>
    </Reason>
</Acknowledgement_MarketDocument>"""

    @pytest.fixture
    def minimal_acknowledgement_xml(self) -> str:
        """Minimal valid acknowledgement XML."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0">
    <mRID>minimal-id</mRID>
    <createdDateTime>2025-08-04T12:00:00Z</createdDateTime>
    <sender_MarketParticipant.mRID codingScheme="A01">10XSENDER------1</sender_MarketParticipant.mRID>
    <receiver_MarketParticipant.mRID codingScheme="A01">10XRECEIVER----1</receiver_MarketParticipant.mRID>
    <received_MarketDocument.createdDateTime>2025-08-04T11:59:59Z</received_MarketDocument.createdDateTime>
    <Reason>
        <code>999</code>
        <text>No data</text>
    </Reason>
</Acknowledgement_MarketDocument>"""

    def test_parse_no_data_acknowledgement_success(
        self, valid_no_data_acknowledgement_xml: str
    ) -> None:
        """Test successful parsing of acknowledgement with reason code 999."""
        # Act
        ack_doc = AcknowledgementMarketDocument.from_xml(
            valid_no_data_acknowledgement_xml
        )

        # Assert
        assert ack_doc.mRID == "73e41c75-ae22-4f67-9c4e-014eb0a0b4a3"
        assert ack_doc.createdDateTime == datetime(2025, 8, 4, 19, 55, 30, tzinfo=UTC)
        assert ack_doc.senderMarketParticipantMRID.mRID == "10X1001A1001A450"
        assert ack_doc.senderMarketParticipantMRID.codingScheme == "A01"
        assert ack_doc.receiverMarketParticipantMRID.mRID == "10X1001A1001A450"
        assert ack_doc.receiverMarketParticipantMRID.codingScheme == "A01"
        assert ack_doc.receivedMarketDocumentCreatedDateTime == datetime(
            2025, 8, 4, 19, 55, 30, tzinfo=UTC
        )
        assert ack_doc.reason_code == "999"
        assert "No matching data found" in ack_doc.reason_text
        assert "Year-ahead Forecast Margin" in ack_doc.reason_text

    def test_parse_error_acknowledgement_success(
        self, valid_error_acknowledgement_xml: str
    ) -> None:
        """Test successful parsing of acknowledgement with error reason code."""
        # Act
        ack_doc = AcknowledgementMarketDocument.from_xml(
            valid_error_acknowledgement_xml
        )

        # Assert
        assert ack_doc.mRID == "84f52d86-bf33-5g78-0d5f-125fc1b1c5b4"
        assert ack_doc.reason_code == "401"
        assert ack_doc.reason_text == "Unauthorized access to requested data"

    def test_parse_minimal_acknowledgement_success(
        self, minimal_acknowledgement_xml: str
    ) -> None:
        """Test parsing of minimal valid acknowledgement."""
        # Act
        ack_doc = AcknowledgementMarketDocument.from_xml(minimal_acknowledgement_xml)

        # Assert
        assert ack_doc.mRID == "minimal-id"
        assert ack_doc.reason_code == "999"
        assert ack_doc.reason_text == "No data"

    def test_is_no_data_available_true_for_code_999(
        self, valid_no_data_acknowledgement_xml: str
    ) -> None:
        """Test that is_no_data_available returns True for reason code 999."""
        # Arrange
        ack_doc = AcknowledgementMarketDocument.from_xml(
            valid_no_data_acknowledgement_xml
        )

        # Act & Assert
        assert ack_doc.is_no_data_available() is True
        assert ack_doc.is_error_acknowledgement() is False

    def test_is_no_data_available_false_for_other_codes(
        self, valid_error_acknowledgement_xml: str
    ) -> None:
        """Test that is_no_data_available returns False for non-999 reason codes."""
        # Arrange
        ack_doc = AcknowledgementMarketDocument.from_xml(
            valid_error_acknowledgement_xml
        )

        # Act & Assert
        assert ack_doc.is_no_data_available() is False
        assert ack_doc.is_error_acknowledgement() is True

    @pytest.mark.parametrize(
        ("reason_code", "expected_no_data"),
        [
            ("999", True),
            ("000", False),
            ("401", False),
            ("500", False),
            ("404", False),
            ("123", False),
        ],
    )
    def test_is_no_data_available_various_codes(
        self, reason_code: str, *, expected_no_data: bool
    ) -> None:
        """Test is_no_data_available with various reason codes."""
        # Arrange
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0">
    <mRID>test-id</mRID>
    <createdDateTime>2025-08-04T12:00:00Z</createdDateTime>
    <sender_MarketParticipant.mRID codingScheme="A01">10XSENDER------1</sender_MarketParticipant.mRID>
    <receiver_MarketParticipant.mRID codingScheme="A01">10XRECEIVER----1</receiver_MarketParticipant.mRID>
    <received_MarketDocument.createdDateTime>2025-08-04T11:59:59Z</received_MarketDocument.createdDateTime>
    <Reason>
        <code>{reason_code}</code>
        <text>Test reason text</text>
    </Reason>
</Acknowledgement_MarketDocument>"""

        # Act
        ack_doc = AcknowledgementMarketDocument.from_xml(xml)

        # Assert
        assert ack_doc.is_no_data_available() is expected_no_data
        assert ack_doc.is_error_acknowledgement() is not expected_no_data

    def test_parse_invalid_xml_raises_exception(self) -> None:
        """Test that parsing invalid XML raises appropriate exception."""
        # Arrange
        invalid_xml = "<invalid>xml</structure>"

        # Act & Assert
        with pytest.raises((ValidationError, ValueError, Exception)):
            AcknowledgementMarketDocument.from_xml(invalid_xml)

    def test_parse_missing_required_fields_raises_exception(self) -> None:
        """Test that parsing XML with missing required fields raises exception."""
        # Arrange
        incomplete_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0">
    <mRID>test-id</mRID>
    <!-- Missing other required fields -->
</Acknowledgement_MarketDocument>"""

        # Act & Assert
        with pytest.raises(ValidationError):
            AcknowledgementMarketDocument.from_xml(incomplete_xml)

    def test_parse_invalid_datetime_raises_exception(self) -> None:
        """Test that parsing XML with invalid datetime format raises exception."""
        # Arrange
        invalid_datetime_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0">
    <mRID>test-id</mRID>
    <createdDateTime>invalid-datetime</createdDateTime>
    <sender_MarketParticipant.mRID codingScheme="A01">10XSENDER------1</sender_MarketParticipant.mRID>
    <receiver_MarketParticipant.mRID codingScheme="A01">10XRECEIVER----1</receiver_MarketParticipant.mRID>
    <received_MarketDocument.createdDateTime>2025-08-04T11:59:59Z</received_MarketDocument.createdDateTime>
    <Reason>
        <code>999</code>
        <text>Test</text>
    </Reason>
</Acknowledgement_MarketDocument>"""

        # Act & Assert
        with pytest.raises(ValidationError):
            AcknowledgementMarketDocument.from_xml(invalid_datetime_xml)

    def test_datetime_serialization_roundtrip(
        self, valid_no_data_acknowledgement_xml: str
    ) -> None:
        """Test that datetime fields can be serialized and deserialized correctly."""
        # Arrange
        ack_doc = AcknowledgementMarketDocument.from_xml(
            valid_no_data_acknowledgement_xml
        )

        # Act - Convert to XML and back
        xml_output = ack_doc.to_xml()
        ack_doc_roundtrip = AcknowledgementMarketDocument.from_xml(xml_output)

        # Assert
        assert ack_doc_roundtrip.createdDateTime == ack_doc.createdDateTime
        assert (
            ack_doc_roundtrip.receivedMarketDocumentCreatedDateTime
            == ack_doc.receivedMarketDocumentCreatedDateTime
        )

    def test_market_participant_mrid_parsing(
        self, valid_no_data_acknowledgement_xml: str
    ) -> None:
        """Test that AcknowledgementMarketParticipant objects are parsed correctly."""
        # Act
        ack_doc = AcknowledgementMarketDocument.from_xml(
            valid_no_data_acknowledgement_xml
        )

        # Assert
        assert isinstance(
            ack_doc.senderMarketParticipantMRID, AcknowledgementMarketParticipant
        )
        assert isinstance(
            ack_doc.receiverMarketParticipantMRID, AcknowledgementMarketParticipant
        )
        assert ack_doc.senderMarketParticipantMRID.mRID == "10X1001A1001A450"
        assert ack_doc.senderMarketParticipantMRID.codingScheme == "A01"

    def test_empty_xml_content_raises_exception(self) -> None:
        """Test that empty XML content raises appropriate exception."""
        # Act & Assert
        with pytest.raises((ValidationError, ValueError, Exception)):
            AcknowledgementMarketDocument.from_xml("")

    def test_xml_with_different_namespace(self) -> None:
        """Test parsing XML with wrong namespace fails appropriately."""
        # Arrange
        wrong_namespace_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Acknowledgement_MarketDocument xmlns="urn:wrong:namespace">
    <mRID>test-id</mRID>
    <createdDateTime>2025-08-04T12:00:00Z</createdDateTime>
    <sender_MarketParticipant.mRID codingScheme="A01">10XSENDER------1</sender_MarketParticipant.mRID>
    <receiver_MarketParticipant.mRID codingScheme="A01">10XRECEIVER----1</receiver_MarketParticipant.mRID>
    <received_MarketDocument.createdDateTime>2025-08-04T11:59:59Z</received_MarketDocument.createdDateTime>
    <Reason>
        <code>999</code>
        <text>Test</text>
    </Reason>
</Acknowledgement_MarketDocument>"""

        # Act & Assert
        with pytest.raises((ValidationError, ValueError, Exception)):
            AcknowledgementMarketDocument.from_xml(wrong_namespace_xml)
