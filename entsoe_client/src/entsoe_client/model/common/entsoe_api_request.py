from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from src.entsoe_client.exceptions.entsoe_api_request_error import EntsoEApiRequestError
from src.entsoe_client.model.common.area_code import AreaCode
from src.entsoe_client.model.common.area_type import AreaType
from src.entsoe_client.model.common.auction_category import AuctionCategory
from src.entsoe_client.model.common.auction_type import AuctionType
from src.entsoe_client.model.common.business_type import BusinessType
from src.entsoe_client.model.common.contract_market_agreement_type import (
    ContractMarketAgreementType,
)
from src.entsoe_client.model.common.direction import Direction
from src.entsoe_client.model.common.doc_status import DocStatus
from src.entsoe_client.model.common.document_type import DocumentType
from src.entsoe_client.model.common.process_type import ProcessType
from src.entsoe_client.model.common.psr_type import PsrType


@dataclass
class EntsoEApiRequest:
    document_type: DocumentType
    period_start: datetime
    period_end: datetime
    process_type: ProcessType | None = None
    business_type: BusinessType | None = None
    psr_type: PsrType | None = None
    doc_status: DocStatus | None = None
    out_bidding_zone_domain: AreaCode | None = None
    bidding_zone_domain: AreaCode | None = None
    control_area_domain: AreaCode | None = None
    in_domain: AreaCode | None = None
    out_domain: AreaCode | None = None
    acquiring_domain: AreaCode | None = None
    connecting_domain: AreaCode | None = None
    area_domain: AreaCode | None = None
    period_start_update: datetime | None = None
    period_end_update: datetime | None = None
    registered_resource: str | None = None
    contract_market_agreement_type: ContractMarketAgreementType | None = None
    type_market_agreement_type: ContractMarketAgreementType | None = None
    auction_type: AuctionType | None = None
    auction_category: AuctionCategory | None = None
    classification_sequence_position: str | None = None
    standard_market_product: str | None = None
    original_market_product: str | None = None
    direction: Direction | None = None
    mrid: str | None = None
    offset: int | None = None
    implementation_date_and_or_time: str | None = None
    update_date_and_or_time: str | None = None

    def to_parameter_map(self) -> dict[str, str]:
        params = {
            "documentType": self.document_type.code,
            "periodStart": self.period_start.strftime("%Y%m%d%H%M"),
            "periodEnd": self.period_end.strftime("%Y%m%d%H%M"),
        }

        def _add_if_not_none(key: str, value: Any) -> None:
            if value is not None:
                if hasattr(value, "code"):
                    params[key] = value.code
                elif isinstance(value, datetime):
                    params[key] = value.strftime("%Y%m%d%H%M")
                else:
                    params[key] = str(value)

        _add_if_not_none("processType", self.process_type)
        _add_if_not_none("businessType", self.business_type)
        _add_if_not_none("psrType", self.psr_type)
        _add_if_not_none("docStatus", self.doc_status)
        _add_if_not_none("outBiddingZone_Domain", self.out_bidding_zone_domain)
        _add_if_not_none("biddingZone_Domain", self.bidding_zone_domain)
        _add_if_not_none("controlArea_Domain", self.control_area_domain)
        _add_if_not_none("in_Domain", self.in_domain)
        _add_if_not_none("out_Domain", self.out_domain)
        _add_if_not_none("acquiring_Domain", self.acquiring_domain)
        _add_if_not_none("connecting_Domain", self.connecting_domain)
        _add_if_not_none("area_Domain", self.area_domain)
        _add_if_not_none("periodStartUpdate", self.period_start_update)
        _add_if_not_none("periodEndUpdate", self.period_end_update)
        _add_if_not_none("registeredResource", self.registered_resource)
        _add_if_not_none(
            "contract_MarketAgreement.Type",
            self.contract_market_agreement_type,
        )
        _add_if_not_none("type_MarketAgreement.Type", self.type_market_agreement_type)
        _add_if_not_none("auction.Type", self.auction_type)
        _add_if_not_none("auction.Category", self.auction_category)
        _add_if_not_none(
            "classificationSequence_AttributeInstanceComponent.Position",
            self.classification_sequence_position,
        )
        _add_if_not_none("standard_MarketProduct", self.standard_market_product)
        _add_if_not_none("original_MarketProduct", self.original_market_product)
        _add_if_not_none("direction", self.direction)
        _add_if_not_none("mRID", self.mrid)
        _add_if_not_none("offset", self.offset)
        _add_if_not_none(
            "implementation_DateAndOrTime",
            self.implementation_date_and_or_time,
        )
        _add_if_not_none("update_DateAndOrTime", self.update_date_and_or_time)

        return params

    def validate_domain_parameters(self) -> None:
        self._validate_area_type(
            self.bidding_zone_domain,
            AreaType.BZN,
            "bidding_zone_domain",
        )
        self._validate_area_type(
            self.control_area_domain,
            AreaType.CTA,
            "control_area_domain",
        )
        self._validate_area_type(
            self.out_bidding_zone_domain,
            AreaType.BZN,
            "out_bidding_zone_domain",
        )

    def _validate_area_type(
        self,
        area_code: AreaCode | None,
        required_type: AreaType,
        parameter_name: str,
    ) -> None:
        if area_code and not area_code.has_area_type(required_type):
            raise EntsoEApiRequestError(
                area_code=area_code,
                required_type=required_type,
                parameter_name=parameter_name,
            )
