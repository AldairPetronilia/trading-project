from datetime import datetime

from pydantic import field_serializer, field_validator
from pydantic_xml import BaseXmlModel, attr, element

from entsoe_client.adapters import date_time_adapter

from . import ENTSOE_ACKNOWLEDGEMENT_NSMAP
from .acknowledgement_market_participant import AcknowledgementMarketParticipant
from .acknowledgement_reason import AcknowledgementReason


class AcknowledgementMarketDocument(
    BaseXmlModel,
    tag="Acknowledgement_MarketDocument",
    nsmap=ENTSOE_ACKNOWLEDGEMENT_NSMAP,  # type: ignore[call-arg]
):
    """ENTSO-E Acknowledgement_MarketDocument for handling no-data responses.

    This model represents the XML structure returned by ENTSO-E when no data
    is available for a request. The most common case is reason code 999,
    which indicates "no matching data found".

    Example XML structure:
    ```xml
    <Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0">
        <mRID>73e41c75-ae22-4</mRID>
        <createdDateTime>2025-08-04T19:55:30Z</createdDateTime>
        <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
        <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
        <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
        <receiver_MarketParticipant.marketRole.type>A39</receiver_MarketParticipant.marketRole.type>
        <received_MarketDocument.createdDateTime>2025-08-04T19:55:30Z</received_MarketDocument.createdDateTime>
        <Reason>
            <code>999</code>
            <text>No matching data found for Data item Year-ahead Forecast Margin [8.1]</text>
        </Reason>
    </Acknowledgement_MarketDocument>
    ```
    """

    mRID: str = element(tag="mRID")
    createdDateTime: datetime = element(tag="createdDateTime")

    # Create nested objects but with proper field mapping for the extra marketRole.type fields
    senderMarketParticipantMRID: AcknowledgementMarketParticipant = element(
        tag="sender_MarketParticipant.mRID",
    )
    senderMarketRoleType: str | None = element(
        tag="sender_MarketParticipant.marketRole.type", default=None
    )

    receiverMarketParticipantMRID: AcknowledgementMarketParticipant = element(
        tag="receiver_MarketParticipant.mRID",
    )
    receiverMarketRoleType: str | None = element(
        tag="receiver_MarketParticipant.marketRole.type", default=None
    )

    receivedMarketDocumentCreatedDateTime: datetime = element(
        tag="received_MarketDocument.createdDateTime",
    )
    reason: AcknowledgementReason

    @field_serializer("createdDateTime")  # type: ignore[misc]
    def encode_created_datetime(self, value: datetime) -> str:
        return date_time_adapter.encode_content(value)

    @field_validator("createdDateTime", mode="before")  # type: ignore[misc]
    def decode_created_datetime(
        cls,
        value: str | datetime | None,
    ) -> datetime | None:
        if isinstance(value, str):
            return date_time_adapter.decode_content(value)
        return value

    @field_serializer("receivedMarketDocumentCreatedDateTime")  # type: ignore[misc]
    def encode_received_datetime(self, value: datetime) -> str:
        return date_time_adapter.encode_content(value)

    @field_validator("receivedMarketDocumentCreatedDateTime", mode="before")  # type: ignore[misc]
    def decode_received_datetime(
        cls,
        value: str | datetime | None,
    ) -> datetime | None:
        if isinstance(value, str):
            return date_time_adapter.decode_content(value)
        return value

    # Backward compatibility properties
    @property
    def sender_market_participant_coding_scheme(self) -> str | None:
        """Get sender market participant coding scheme for backward compatibility."""
        return self.senderMarketParticipantMRID.codingScheme

    @property
    def receiver_market_participant_coding_scheme(self) -> str | None:
        """Get receiver market participant coding scheme for backward compatibility."""
        return self.receiverMarketParticipantMRID.codingScheme

    @property
    def reason_code(self) -> str:
        """Get the reason code from the nested reason element."""
        return self.reason.code

    @property
    def reason_text(self) -> str:
        """Get the reason text from the nested reason element."""
        return self.reason.text

    def is_no_data_available(self) -> bool:
        """Check if this acknowledgement indicates no data is available.

        Returns:
            True if the reason code is 999 (no matching data found)
        """
        return self.reason_code == "999"

    def is_error_acknowledgement(self) -> bool:
        """Check if this acknowledgement indicates an error condition.

        Returns:
            True if the reason code indicates an error (not 999)
        """
        return not self.is_no_data_available()
