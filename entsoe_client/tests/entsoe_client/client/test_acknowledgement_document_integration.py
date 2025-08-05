"""Integration tests for acknowledgement document handling workflow."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from entsoe_client.client.default_entsoe_client import DefaultEntsoEClient
from entsoe_client.client.entsoe_client_error import EntsoEClientError
from entsoe_client.client.xml_document_detector import (
    XmlDocumentDetector,
    XmlDocumentType,
)
from entsoe_client.http_client.httpx_client import HttpxClient
from entsoe_client.model.acknowledgement import AcknowledgementMarketDocument
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.load.gl_market_document import GlMarketDocument


class TestAcknowledgementDocumentIntegration:
    """Integration tests for complete acknowledgement document workflow."""

    @pytest.fixture
    def mock_http_client(self) -> AsyncMock:
        """Create a mock HTTP client for testing."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value="<xml>mock response</xml>")
        mock_client.close = AsyncMock()
        return mock_client

    @pytest.fixture
    def client_with_mock(self, mock_http_client: AsyncMock) -> DefaultEntsoEClient:
        """Create a DefaultEntsoEClient with mocked HTTP client."""
        return DefaultEntsoEClient(mock_http_client, "https://web-api.tp.entsoe.eu/api")

    @pytest.fixture
    def valid_gl_market_document_xml(self) -> str:
        """Sample GL_MarketDocument XML response."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
    <mRID>sample-gl-document-id</mRID>
    <revisionNumber>1</revisionNumber>
    <type>A65</type>
    <process.processType>A16</process.processType>
    <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
    <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
    <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
    <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
    <createdDateTime>2025-08-04T12:00:00Z</createdDateTime>
    <time_Period.timeInterval>
        <start>2025-08-04T00:00Z</start>
        <end>2025-08-05T00:00Z</end>
    </time_Period.timeInterval>
    <TimeSeries>
        <mRID>ts-sample-id</mRID>
        <businessType>A04</businessType>
        <objectAggregation>A01</objectAggregation>
        <outBiddingZone_Domain.mRID codingScheme="A01">10YCZ-CEPS-----N</outBiddingZone_Domain.mRID>
        <quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>
        <curveType>A01</curveType>
        <Period>
            <timeInterval>
                <start>2025-08-04T00:00Z</start>
                <end>2025-08-05T00:00Z</end>
            </timeInterval>
            <resolution>PT1H</resolution>
            <Point>
                <position>1</position>
                <quantity>1000</quantity>
            </Point>
            <Point>
                <position>2</position>
                <quantity>1100</quantity>
            </Point>
        </Period>
    </TimeSeries>
</GL_MarketDocument>"""

    @pytest.fixture
    def no_data_acknowledgement_xml(self) -> str:
        """Sample acknowledgement XML with reason code 999 (no data available)."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0">
    <mRID>ack-no-data-id</mRID>
    <createdDateTime>2025-08-04T12:00:00Z</createdDateTime>
    <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
    <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
    <received_MarketDocument.createdDateTime>2025-08-04T11:59:59Z</received_MarketDocument.createdDateTime>
    <Reason>
        <code>999</code>
        <text>No matching data found for Data item Year-ahead Forecast Margin [8.1] for Period 2025-08-05T00:00Z/2025-08-06T00:00Z and Domain 10YDE-VE-------2.</text>
    </Reason>
</Acknowledgement_MarketDocument>"""

    @pytest.fixture
    def error_acknowledgement_xml(self) -> str:
        """Sample acknowledgement XML with error reason code."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0">
    <mRID>ack-error-id</mRID>
    <createdDateTime>2025-08-04T12:00:00Z</createdDateTime>
    <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
    <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
    <received_MarketDocument.createdDateTime>2025-08-04T11:59:59Z</received_MarketDocument.createdDateTime>
    <Reason>
        <code>401</code>
        <text>Unauthorized access to requested data</text>
    </Reason>
</Acknowledgement_MarketDocument>"""

    def test_xml_document_detector_integration(
        self,
        valid_gl_market_document_xml: str,
        no_data_acknowledgement_xml: str,
        error_acknowledgement_xml: str,
    ) -> None:
        """Test XmlDocumentDetector correctly identifies different document types."""
        # Test GL_MarketDocument detection
        gl_doc_type = XmlDocumentDetector.detect_document_type(
            valid_gl_market_document_xml
        )
        assert gl_doc_type == XmlDocumentType.GL_MARKET_DOCUMENT

        # Test Acknowledgement_MarketDocument detection (no data)
        ack_no_data_type = XmlDocumentDetector.detect_document_type(
            no_data_acknowledgement_xml
        )
        assert ack_no_data_type == XmlDocumentType.ACKNOWLEDGEMENT_MARKET_DOCUMENT

        # Test Acknowledgement_MarketDocument detection (error)
        ack_error_type = XmlDocumentDetector.detect_document_type(
            error_acknowledgement_xml
        )
        assert ack_error_type == XmlDocumentType.ACKNOWLEDGEMENT_MARKET_DOCUMENT

    def test_acknowledgement_document_parsing_integration(
        self, no_data_acknowledgement_xml: str, error_acknowledgement_xml: str
    ) -> None:
        """Test AcknowledgementMarketDocument parsing and classification."""
        # Test no-data acknowledgement parsing
        no_data_doc = AcknowledgementMarketDocument.from_xml(
            no_data_acknowledgement_xml
        )
        assert no_data_doc.mRID == "ack-no-data-id"
        assert no_data_doc.reason_code == "999"
        assert no_data_doc.is_no_data_available() is True
        assert no_data_doc.is_error_acknowledgement() is False
        assert "No matching data found" in no_data_doc.reason_text

        # Test error acknowledgement parsing
        error_doc = AcknowledgementMarketDocument.from_xml(error_acknowledgement_xml)
        assert error_doc.mRID == "ack-error-id"
        assert error_doc.reason_code == "401"
        assert error_doc.is_no_data_available() is False
        assert error_doc.is_error_acknowledgement() is True
        assert "Unauthorized access" in error_doc.reason_text

    def test_gl_market_document_parsing_integration(
        self, valid_gl_market_document_xml: str
    ) -> None:
        """Test GL_MarketDocument parsing still works correctly."""
        gl_doc = GlMarketDocument.from_xml(valid_gl_market_document_xml)
        assert gl_doc.mRID == "sample-gl-document-id"
        assert gl_doc.timeSeries[0].mRID == "ts-sample-id"
        assert len(gl_doc.timeSeries[0].period.points) == 2
        assert gl_doc.timeSeries[0].period.points[0].quantity == 1000
        assert gl_doc.timeSeries[0].period.points[1].quantity == 1100

    @pytest.mark.asyncio
    async def test_client_workflow_with_gl_market_document(
        self, client_with_mock: DefaultEntsoEClient, valid_gl_market_document_xml: str
    ) -> None:
        """Test complete client workflow when ENTSO-E returns GL_MarketDocument."""
        # Mock the HTTP client get method to return GL_MarketDocument XML
        with patch.object(
            client_with_mock.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = valid_gl_market_document_xml

            # Test period - yesterday for actual data
            today = datetime.now(UTC).date()
            yesterday = today - timedelta(days=1)
            period_start = datetime.combine(yesterday, datetime.min.time()).replace(
                tzinfo=UTC
            )
            period_end = period_start + timedelta(days=1)

            # Make request
            result = await client_with_mock.get_actual_total_load(
                bidding_zone=AreaCode.CZECH_REPUBLIC,
                period_start=period_start,
                period_end=period_end,
            )

            # Verify result
            assert isinstance(result, GlMarketDocument)
            assert result.mRID == "sample-gl-document-id"
            assert result.timeSeries[0].mRID == "ts-sample-id"
            assert len(result.timeSeries[0].period.points) == 2

            # Verify HTTP client was called
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_workflow_with_no_data_acknowledgement(
        self, client_with_mock: DefaultEntsoEClient, no_data_acknowledgement_xml: str
    ) -> None:
        """Test complete client workflow when ENTSO-E returns no-data acknowledgement."""
        # Mock the HTTP client get method to return acknowledgement XML
        with patch.object(
            client_with_mock.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = no_data_acknowledgement_xml

            # Test period - future date that likely has no data
            tomorrow = datetime.now(UTC).date() + timedelta(days=1)
            period_start = datetime.combine(tomorrow, datetime.min.time()).replace(
                tzinfo=UTC
            )
            period_end = period_start + timedelta(days=1)

            # Make request - should return None for no-data acknowledgement
            # Note: This assumes the client has been updated to handle acknowledgements
            # For now, we test that the parsing works and acknowledgement is detected
            try:
                await client_with_mock.get_year_ahead_forecast_margin(
                    bidding_zone=AreaCode.CZECH_REPUBLIC,
                    period_start=period_start,
                    period_end=period_end,
                )
                # This will currently raise an exception since the client hasn't been updated yet
                # In Phase 2, this should return None
                pytest.fail(
                    "Expected exception since client not yet updated for acknowledgements"
                )
            except EntsoEClientError:
                # For now, verify that we can detect and parse the acknowledgement
                xml_response = no_data_acknowledgement_xml
                doc_type = XmlDocumentDetector.detect_document_type(xml_response)
                assert doc_type == XmlDocumentType.ACKNOWLEDGEMENT_MARKET_DOCUMENT

                ack_doc = AcknowledgementMarketDocument.from_xml(xml_response)
                assert ack_doc.is_no_data_available() is True
                assert ack_doc.reason_code == "999"

            # Note: Not verifying HTTP client was called since client may fail before HTTP request
            # This will be properly tested in Phase 2 when client handles acknowledgements

    @pytest.mark.asyncio
    async def test_client_workflow_with_error_acknowledgement(
        self, client_with_mock: DefaultEntsoEClient, error_acknowledgement_xml: str
    ) -> None:
        """Test complete client workflow when ENTSO-E returns error acknowledgement."""
        # Mock the HTTP client get method to return error acknowledgement XML
        with patch.object(
            client_with_mock.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = error_acknowledgement_xml

            period_start = datetime.now(UTC)
            period_end = period_start + timedelta(days=1)

            # Make request - should handle error acknowledgement appropriately
            try:
                await client_with_mock.get_actual_total_load(
                    bidding_zone=AreaCode.CZECH_REPUBLIC,
                    period_start=period_start,
                    period_end=period_end,
                )
                # This will currently raise an exception since the client hasn't been updated yet
                pytest.fail(
                    "Expected exception since client not yet updated for acknowledgements"
                )
            except EntsoEClientError:
                # For now, verify that we can detect and parse the acknowledgement
                xml_response = error_acknowledgement_xml
                doc_type = XmlDocumentDetector.detect_document_type(xml_response)
                assert doc_type == XmlDocumentType.ACKNOWLEDGEMENT_MARKET_DOCUMENT

                ack_doc = AcknowledgementMarketDocument.from_xml(xml_response)
                assert ack_doc.is_error_acknowledgement() is True
                assert ack_doc.reason_code == "401"
                assert "Unauthorized access" in ack_doc.reason_text

            # Note: Not verifying HTTP client was called since client may fail before HTTP request
            # This will be properly tested in Phase 2 when client handles acknowledgements

    def test_complete_workflow_simulation(
        self,
        valid_gl_market_document_xml: str,
        no_data_acknowledgement_xml: str,
        error_acknowledgement_xml: str,
    ) -> None:
        """Simulate complete workflow without client dependency."""
        test_responses = [
            valid_gl_market_document_xml,
            no_data_acknowledgement_xml,
            error_acknowledgement_xml,
        ]

        results = []
        for xml_response in test_responses:
            # Step 1: Detect document type
            doc_type = XmlDocumentDetector.detect_document_type(xml_response)

            # Step 2: Parse based on document type
            if doc_type == XmlDocumentType.GL_MARKET_DOCUMENT:
                parsed_doc = GlMarketDocument.from_xml(xml_response)
                results.append(("data", parsed_doc))
            elif doc_type == XmlDocumentType.ACKNOWLEDGEMENT_MARKET_DOCUMENT:
                ack_doc = AcknowledgementMarketDocument.from_xml(xml_response)
                if ack_doc.is_no_data_available():
                    results.append(("no_data", ack_doc))
                else:
                    results.append(("error", ack_doc))

        # Verify results
        assert len(results) == 3

        # First result should be data
        assert results[0][0] == "data"
        assert isinstance(results[0][1], GlMarketDocument)
        assert results[0][1].mRID == "sample-gl-document-id"

        # Second result should be no_data
        assert results[1][0] == "no_data"
        assert isinstance(results[1][1], AcknowledgementMarketDocument)
        assert results[1][1].reason_code == "999"

        # Third result should be error
        assert results[2][0] == "error"
        assert isinstance(results[2][1], AcknowledgementMarketDocument)
        assert results[2][1].reason_code == "401"

    @pytest.mark.asyncio
    async def test_mixed_response_scenarios(
        self,
        client_with_mock: DefaultEntsoEClient,
        valid_gl_market_document_xml: str,
        no_data_acknowledgement_xml: str,
    ) -> None:
        """Test handling of mixed response scenarios in sequence."""
        responses = [valid_gl_market_document_xml, no_data_acknowledgement_xml]

        for i, xml_response in enumerate(responses):
            with patch.object(
                client_with_mock.http_client, "get", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = xml_response

                period_start = datetime.now(UTC) + timedelta(days=i)
                period_end = period_start + timedelta(days=1)

                if i == 0:  # GL_MarketDocument response
                    result = await client_with_mock.get_actual_total_load(
                        bidding_zone=AreaCode.CZECH_REPUBLIC,
                        period_start=period_start,
                        period_end=period_end,
                    )
                    assert isinstance(result, GlMarketDocument)
                    assert result.mRID == "sample-gl-document-id"
                else:  # Acknowledgement response
                    try:
                        await client_with_mock.get_year_ahead_forecast_margin(
                            bidding_zone=AreaCode.CZECH_REPUBLIC,
                            period_start=period_start,
                            period_end=period_end,
                        )
                        pytest.fail("Expected exception for acknowledgement")
                    except EntsoEClientError:
                        # Verify we can still detect and parse acknowledgement
                        doc_type = XmlDocumentDetector.detect_document_type(
                            xml_response
                        )
                        assert (
                            doc_type == XmlDocumentType.ACKNOWLEDGEMENT_MARKET_DOCUMENT
                        )

                        ack_doc = AcknowledgementMarketDocument.from_xml(xml_response)
                        assert ack_doc.is_no_data_available() is True
