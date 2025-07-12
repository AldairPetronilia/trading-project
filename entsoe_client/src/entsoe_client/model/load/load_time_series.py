from typing import Optional, Union

from pydantic import field_serializer, field_validator
from pydantic_xml import BaseXmlModel, element

from entsoe_client.model import ENTSOE_NSMAP
from entsoe_client.model.common.business_type import BusinessType
from entsoe_client.model.common.curve_type import CurveType
from entsoe_client.model.common.domain_mrid import DomainMRID
from entsoe_client.model.load.load_period import LoadPeriod
from entsoe_client.model.load.object_aggregation import ObjectAggregation


class LoadTimeSeries(BaseXmlModel, tag="TimeSeries", nsmap=ENTSOE_NSMAP):  # type: ignore[call-arg]
    mRID: str = element(tag="mRID")
    businessType: BusinessType = element(tag="businessType")
    objectAggregation: ObjectAggregation = element(tag="objectAggregation")
    outBiddingZoneDomainMRID: DomainMRID = element(tag="outBiddingZone_Domain.mRID")
    quantityMeasureUnitName: str = element(tag="quantity_Measure_Unit.name")
    curveType: CurveType = element(tag="curveType")
    period: LoadPeriod

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

    @field_serializer("objectAggregation")  # type: ignore[misc]
    def encode_object_aggregation(self, value: ObjectAggregation) -> str:
        return value.code

    @field_validator("objectAggregation", mode="before")  # type: ignore[misc]
    def decode_object_aggregation(
        cls,
        value: str | ObjectAggregation | None,
    ) -> ObjectAggregation | None:
        if isinstance(value, str):
            return ObjectAggregation.from_code(value)

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
