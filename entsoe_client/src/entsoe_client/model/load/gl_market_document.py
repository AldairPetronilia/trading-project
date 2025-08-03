from datetime import datetime

from pydantic import field_serializer, field_validator
from pydantic_xml import BaseXmlModel, element

from entsoe_client.adapters import date_time_adapter
from entsoe_client.model import ENTSOE_LOAD_NSMAP
from entsoe_client.model.common.document_type import DocumentType
from entsoe_client.model.common.market_role_type import MarketRoleType
from entsoe_client.model.common.process_type import ProcessType
from entsoe_client.model.load.load_time_interval import LoadTimeInterval
from entsoe_client.model.load.load_time_series import LoadTimeSeries
from entsoe_client.model.load.market_participant_mrid import MarketParticipantMRID


class GlMarketDocument(BaseXmlModel, tag="GL_MarketDocument", nsmap=ENTSOE_LOAD_NSMAP):  # type: ignore[call-arg]
    mRID: str = element(tag="mRID")
    revisionNumber: int | None = element(tag="revisionNumber")
    type: DocumentType = element(tag="type")
    processType: ProcessType = element(tag="process.processType")
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
    timePeriodTimeInterval: LoadTimeInterval = element(tag="time_Period.timeInterval")
    timeSeries: list[LoadTimeSeries]

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

    @field_serializer("processType")  # type: ignore[misc]
    def encode_process_type(self, value: ProcessType) -> str:
        return value.code

    @field_validator("processType", mode="before")  # type: ignore[misc]
    def decode_process_type(
        cls,
        value: str | ProcessType | None,
    ) -> ProcessType | None:
        if isinstance(value, str):
            return ProcessType.from_code(value)

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
