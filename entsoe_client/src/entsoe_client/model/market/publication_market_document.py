"""Publication Market Document model for ENTSO-E Market Domain responses."""

from datetime import datetime

from pydantic import field_serializer, field_validator
from pydantic_xml import BaseXmlModel, element

from entsoe_client.adapters import date_time_adapter
from entsoe_client.model.common.document_type import DocumentType
from entsoe_client.model.common.market_role_type import MarketRoleType

from .market_participant_mrid import MarketParticipantMRID
from .market_time_interval import MarketTimeInterval
from .market_time_series import MarketTimeSeries


class PublicationMarketDocument(BaseXmlModel, tag="Publication_MarketDocument"):  # type: ignore[call-arg]  # Namespace-agnostic model
    """
    Publication Market Document for ENTSO-E Market Domain responses.

    Used for price-related data like day-ahead prices [12.1.D] and
    physical flows data [12.1.G]. This namespace-agnostic version can
    parse both 7:3 and 7:0 namespace variants after namespace stripping.
    Follows the same pattern as GlMarketDocument but adapted for market domain.
    """

    mRID: str = element(tag="mRID")
    revisionNumber: int | None = element(tag="revisionNumber")
    type: DocumentType = element(tag="type")
    senderMarketParticipantMRID: MarketParticipantMRID = element(
        tag="sender_MarketParticipant.mRID",
    )
    senderMarketParticipantMarketRoleType: MarketRoleType = element(
        tag="sender_MarketParticipant.marketRole.type",
    )
    receiverMarketParticipantMRID: MarketParticipantMRID = element(
        tag="receiver_MarketParticipant.mRID",
    )
    receiverMarketParticipantMarketRoleType: MarketRoleType = element(
        tag="receiver_MarketParticipant.marketRole.type",
    )
    createdDateTime: datetime = element(tag="createdDateTime")
    periodTimeInterval: MarketTimeInterval = element(tag="period.timeInterval")
    # Fix: Use proper element mapping for list of TimeSeries
    timeSeries: list[MarketTimeSeries] = element(tag="TimeSeries", default=[])

    @field_serializer("type")  # type: ignore[misc]
    def encode_type(self, value: DocumentType) -> str:
        return value.code

    @field_validator("type", mode="before")  # type: ignore[misc]
    def decode_type(
        cls,
        value: str | DocumentType | None,
    ) -> DocumentType | None:
        if isinstance(value, str):
            return DocumentType.from_code(value)

        return value

    @field_serializer("senderMarketParticipantMarketRoleType")  # type: ignore[misc]
    def encode_sender_role_type(self, value: MarketRoleType) -> str:
        return value.code

    @field_validator("senderMarketParticipantMarketRoleType", mode="before")  # type: ignore[misc]
    def decode_sender_role_type(
        cls,
        value: str | MarketRoleType | None,
    ) -> MarketRoleType | None:
        if isinstance(value, str):
            return MarketRoleType.from_code(value)

        return value

    @field_serializer("receiverMarketParticipantMarketRoleType")  # type: ignore[misc]
    def encode_receiver_role_type(self, value: MarketRoleType) -> str:
        return value.code

    @field_validator("receiverMarketParticipantMarketRoleType", mode="before")  # type: ignore[misc]
    def decode_receiver_role_type(
        cls,
        value: str | MarketRoleType | None,
    ) -> MarketRoleType | None:
        if isinstance(value, str):
            return MarketRoleType.from_code(value)

        return value

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
