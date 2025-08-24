"""Market domain MRID model for ENTSO-E Publication Market Documents."""

from pydantic import field_serializer, field_validator
from pydantic_xml import BaseXmlModel, attr

from entsoe_client.model.common.area_code import AreaCode

from .market_time_interval import ENTSOE_MARKET_NSMAP


class MarketDomainMRID(BaseXmlModel, tag="domain.mRID", nsmap=ENTSOE_MARKET_NSMAP):  # type: ignore[call-arg]
    """Domain MRID model for market documents with correct namespace."""

    area_code: AreaCode  # Text content of the element
    coding_scheme: str | None = attr(name="codingScheme", default=None)

    @field_serializer("area_code")  # type: ignore[misc]
    def encode_area_code(self, value: AreaCode) -> str:
        return value.code

    @field_validator("area_code", mode="before")  # type: ignore[misc]
    def decode_area_code(
        cls,
        value: str | AreaCode | None,
    ) -> AreaCode | None:
        if isinstance(value, str):
            return AreaCode.from_code(value)
        return value
