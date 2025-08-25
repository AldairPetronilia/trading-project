"""Market Domain Request Builder for ENTSO-E Market Domain API endpoints."""

from dataclasses import dataclass
from datetime import datetime
from typing import Self

from entsoe_client.exceptions.market_domain_request_builder_error import (
    MarketDomainRequestBuilderError,
)
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.business_type import BusinessType
from entsoe_client.model.common.document_type import DocumentType
from entsoe_client.model.common.entsoe_api_request import EntsoEApiRequest


@dataclass
class MarketDomainRequestBuilder:
    """
    Specialized builder for ENTSO-E Market Domain API endpoints.
    Supports market-related data types like day-ahead prices with domain validation.
    """

    in_domain: AreaCode
    out_domain: AreaCode
    period_start: datetime
    period_end: datetime
    offset: int | None = None

    def __post_init__(self) -> None:
        if self.in_domain is None:
            raise MarketDomainRequestBuilderError.in_domain_required()
        if self.out_domain is None:
            raise MarketDomainRequestBuilderError.out_domain_required()
        if self.period_start is None:
            raise MarketDomainRequestBuilderError.period_start_required()
        if self.period_end is None:
            raise MarketDomainRequestBuilderError.period_end_required()

        self._validate_date_range(self.period_start, self.period_end)

    @classmethod
    def builder(cls) -> "MarketDomainRequestBuilder":
        """Create a new builder instance."""
        return cls.__new__(cls)

    def for_domains(self, in_domain: AreaCode, out_domain: AreaCode) -> Self:
        """Set both domain areas."""
        self.in_domain = in_domain
        self.out_domain = out_domain
        return self

    def from_period(self, start: datetime, end: datetime) -> Self:
        """Set the time period."""
        self._validate_date_range(start, end)
        self.period_start = start
        self.period_end = end
        return self

    def with_offset(self, offset: int) -> Self:
        """Set the pagination offset."""
        self.offset = offset
        return self

    def build_day_ahead_prices(self) -> EntsoEApiRequest:
        """
        Build EntsoEApiRequest for Day-Ahead Prices [12.1.D].
        DocumentType: A44 (Price Document)
        BusinessType: A62 (Day-ahead prices)
        Domain validation: in_Domain must equal out_Domain for price requests.
        One year range limit, minimum one hour resolution.
        """
        self._validate_domains_for_prices(self.in_domain, self.out_domain)

        return EntsoEApiRequest(
            document_type=DocumentType.PRICE_DOCUMENT,  # A44
            business_type=BusinessType.DAY_AHEAD_PRICES,  # A62
            in_domain=self.in_domain,
            out_domain=self.out_domain,
            period_start=self.period_start,
            period_end=self.period_end,
            offset=self.offset,
        )

    def build_physical_flows(self) -> EntsoEApiRequest:
        """
        Build EntsoEApiRequest for Physical Flows [12.1.G].
        DocumentType: A11 (Aggregated energy data report)
        BusinessType: A66 (Physical flows)
        Domain validation: in_Domain must NOT equal out_Domain for directional flows.
        One year range limit, minimum MTU period resolution.
        """
        self._validate_domains_for_flows(self.in_domain, self.out_domain)

        return EntsoEApiRequest(
            document_type=DocumentType.AGGREGATED_ENERGY_DATA_REPORT,  # A11
            business_type=BusinessType.PHYSICAL_FLOWS,  # A66
            in_domain=self.in_domain,
            out_domain=self.out_domain,
            period_start=self.period_start,
            period_end=self.period_end,
            offset=self.offset,
        )

    def _validate_domains_for_prices(
        self, in_domain: AreaCode, out_domain: AreaCode
    ) -> None:
        """Validate that domains are equal for price requests."""
        if in_domain and out_domain and in_domain != out_domain:
            raise MarketDomainRequestBuilderError.domains_must_be_equal(
                in_domain, out_domain
            )

    def _validate_domains_for_flows(
        self, in_domain: AreaCode, out_domain: AreaCode
    ) -> None:
        """Validate that domains are different for flow requests (directional)."""
        if in_domain and out_domain and in_domain == out_domain:
            raise MarketDomainRequestBuilderError.domains_must_be_different(
                in_domain, out_domain
            )

    def _validate_date_range(self, start: datetime, end: datetime) -> None:
        """Validate the date range constraints."""
        if start and end:
            if start >= end:
                raise MarketDomainRequestBuilderError.period_start_after_end()

            # Check one year limit
            if start.replace(year=start.year + 1) < end:
                raise MarketDomainRequestBuilderError.date_range_exceeds_one_year()
