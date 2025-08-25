"""Market time series model for ENTSO-E Publication Market Documents."""

from pydantic import field_serializer, field_validator
from pydantic_xml import BaseXmlModel, element

from entsoe_client.model.common.auction_type import AuctionType
from entsoe_client.model.common.business_type import BusinessType
from entsoe_client.model.common.contract_market_agreement_type import (
    ContractMarketAgreementType,
)
from entsoe_client.model.common.curve_type import CurveType

from .market_domain_mrid import MarketDomainMRID
from .market_period import MarketPeriod
from .market_time_interval import ENTSOE_MARKET_NSMAP


class MarketTimeSeries(BaseXmlModel, tag="TimeSeries", nsmap=ENTSOE_MARKET_NSMAP):  # type: ignore[call-arg]
    """Time series model for market documents with price and quantity data."""

    mRID: str = element(tag="mRID")
    auction_type: AuctionType | None = element(tag="auction.type", default=None)
    businessType: BusinessType = element(tag="businessType")
    in_domain_mRID: MarketDomainMRID | None = element(
        tag="in_Domain.mRID", default=None
    )
    out_domain_mRID: MarketDomainMRID | None = element(
        tag="out_Domain.mRID", default=None
    )
    contract_market_agreement_type: ContractMarketAgreementType | None = element(
        tag="contract_MarketAgreement.type", default=None
    )
    currency_unit_name: str | None = element(tag="currency_Unit.name", default=None)
    price_measure_unit_name: str | None = element(
        tag="price_Measure_Unit.name", default=None
    )
    quantity_measure_unit_name: str | None = element(
        tag="quantity_Measure_Unit.name", default=None
    )
    # Add missing field for classification sequence position
    classification_sequence_position: int | None = element(
        tag="classificationSequence_AttributeInstanceComponent.position", default=None
    )
    curveType: CurveType | None = element(tag="curveType", default=None)
    # Fix: Use proper element mapping for Period
    period: MarketPeriod = element(tag="Period")

    @field_serializer("auction_type")  # type: ignore[misc]
    def encode_auction_type(self, value: AuctionType | None) -> str | None:
        return value.code if value else None

    @field_validator("auction_type", mode="before")  # type: ignore[misc]
    def decode_auction_type(
        cls,
        value: str | AuctionType | None,
    ) -> AuctionType | None:
        if isinstance(value, str):
            return AuctionType.from_code(value)
        return value

    @field_serializer("contract_market_agreement_type")  # type: ignore[misc]
    def encode_contract_market_agreement_type(
        self, value: ContractMarketAgreementType | None
    ) -> str | None:
        return value.code if value else None

    @field_validator("contract_market_agreement_type", mode="before")  # type: ignore[misc]
    def decode_contract_market_agreement_type(
        cls,
        value: str | ContractMarketAgreementType | None,
    ) -> ContractMarketAgreementType | None:
        if isinstance(value, str):
            return ContractMarketAgreementType.from_code(value)
        return value

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
    def encode_curve_type(self, value: CurveType | None) -> str | None:
        return value.code if value else None

    @field_validator("curveType", mode="before")  # type: ignore[misc]
    def decode_curve_type(
        cls,
        value: str | CurveType | None,
    ) -> CurveType | None:
        if isinstance(value, str):
            return CurveType.from_code(value)

        return value
