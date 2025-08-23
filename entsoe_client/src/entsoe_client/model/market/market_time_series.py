"""Market time series model for ENTSO-E Publication Market Documents."""

from pydantic import field_serializer, field_validator
from pydantic_xml import BaseXmlModel, element

from entsoe_client.model.common.business_type import BusinessType
from entsoe_client.model.common.curve_type import CurveType
from entsoe_client.model.common.domain_mrid import DomainMRID

from .market_period import MarketPeriod
from .market_time_interval import ENTSOE_MARKET_NSMAP


class MarketTimeSeries(BaseXmlModel, tag="TimeSeries", nsmap=ENTSOE_MARKET_NSMAP):  # type: ignore[call-arg]
    """Time series model for market documents with price data."""

    mRID: str = element(tag="mRID")
    businessType: BusinessType = element(tag="businessType")
    in_domain_mRID: DomainMRID = element(tag="in_Domain.mRID")
    out_domain_mRID: DomainMRID = element(tag="out_Domain.mRID")
    currency_unit_name: str = element(tag="currency_Unit.name")
    price_measure_unit_name: str = element(tag="price_Measure_Unit.name")
    curveType: CurveType = element(tag="curveType")
    period: MarketPeriod

    @field_serializer("businessType")  # type: ignore[misc]
    def encode_business_type(self, value: BusinessType) -> str:
        return value.code

    @field_validator("businessType", mode="before")  # type: ignore[misc]
    def decode_business_type(
        cls,
        value: str | BusinessType | None,
    ) -> BusinessType | None:
        if isinstance(value, str):
            return BusinessType.from_code(value)

        return value

    @field_serializer("curveType")  # type: ignore[misc]
    def encode_curve_type(self, value: CurveType) -> str:
        return value.code

    @field_validator("curveType", mode="before")  # type: ignore[misc]
    def decode_curve_type(
        cls,
        value: str | CurveType | None,
    ) -> CurveType | None:
        if isinstance(value, str):
            return CurveType.from_code(value)

        return value
