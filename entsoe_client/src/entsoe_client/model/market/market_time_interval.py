"""Market time interval model for ENTSO-E Publication Market Documents."""

from datetime import datetime

from pydantic import field_serializer, field_validator
from pydantic_xml import BaseXmlModel, element

from entsoe_client.adapters import date_time_adapter

ENTSOE_MARKET_NSMAP = {
    "": "urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3",
}


class MarketTimeInterval(BaseXmlModel, nsmap=ENTSOE_MARKET_NSMAP):  # type: ignore[call-arg]
    """Time interval model for market documents."""

    start: datetime = element(tag="start")
    end: datetime = element(tag="end")

    @field_serializer("start")  # type: ignore[misc]
    def encode_start(self, value: datetime) -> str:
        return date_time_adapter.encode_content(value)

    @field_validator("start", mode="before")  # type: ignore[misc]
    def decode_start(cls, value: str | datetime | None) -> datetime | None:
        if isinstance(value, str):
            return date_time_adapter.decode_content(value)

        return value

    @field_serializer("end")  # type: ignore[misc]
    def encode_end(self, value: datetime) -> str:
        return date_time_adapter.encode_content(value)

    @field_validator("end", mode="before")  # type: ignore[misc]
    def decode_end(cls, value: str | datetime | None) -> datetime | None:
        if isinstance(value, str):
            return date_time_adapter.decode_content(value)

        return value
