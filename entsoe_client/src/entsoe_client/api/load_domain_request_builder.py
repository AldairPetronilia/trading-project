from dataclasses import dataclass
from datetime import datetime
from typing import Self

from entsoe_client.exceptions.load_domain_request_builder_error import (
    LoadDomainRequestBuilderError,
)
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.area_type import AreaType
from entsoe_client.model.common.document_type import DocumentType
from entsoe_client.model.common.entsoe_api_request import EntsoEApiRequest
from entsoe_client.model.common.process_type import ProcessType


@dataclass
class LoadDomainRequestBuilder:
    """
    Specialized builder for ENTSO-E Load Domain API endpoints.
    Supports all load-related data types with predefined configurations.
    """

    out_bidding_zone_domain: AreaCode
    period_start: datetime
    period_end: datetime
    time_interval: str | None = None
    offset: int | None = None

    def __post_init__(self) -> None:
        if self.out_bidding_zone_domain is None:
            raise LoadDomainRequestBuilderError.out_bidding_zone_domain_required()
        if self.period_start is None:
            raise LoadDomainRequestBuilderError.period_start_required()
        if self.period_end is None:
            raise LoadDomainRequestBuilderError.period_end_required()

        self._validate_bidding_zone(self.out_bidding_zone_domain)
        self._validate_date_range(self.period_start, self.period_end)

    @classmethod
    def builder(cls) -> "LoadDomainRequestBuilder":
        """Create a new builder instance."""
        return cls.__new__(cls)

    def for_bidding_zone(self, bidding_zone: AreaCode) -> Self:
        """Set the bidding zone domain."""
        self._validate_bidding_zone(bidding_zone)
        self.out_bidding_zone_domain = bidding_zone
        return self

    def from_period(self, start: datetime, end: datetime) -> Self:
        """Set the time period."""
        self._validate_date_range(start, end)
        self.period_start = start
        self.period_end = end
        return self

    def with_time_interval(self, time_interval: str) -> Self:
        """Set the time interval."""
        self.time_interval = time_interval
        return self

    def with_offset(self, offset: int) -> Self:
        """Set the pagination offset."""
        self.offset = offset
        return self

    def build_actual_total_load(self) -> EntsoEApiRequest:
        """
        Build EntsoEApiRequest for Actual Total Load [6.1.A].
        DocumentType: A65 (System Total Load)
        ProcessType: A16 (Realised)
        One year range limit, minimum MTU period resolution.
        """
        return EntsoEApiRequest(
            document_type=DocumentType.SYSTEM_TOTAL_LOAD,  # A65
            process_type=ProcessType.REALISED,  # A16
            out_bidding_zone_domain=self.out_bidding_zone_domain,
            period_start=self.period_start,
            period_end=self.period_end,
            offset=self.offset,
        )

    def build_day_ahead_load_forecast(self) -> EntsoEApiRequest:
        """
        Build EntsoEApiRequest for Day-Ahead Total Load Forecast [6.1.B].
        DocumentType: A65 (System Total Load)
        ProcessType: A01 (Day Ahead)
        One year range limit, minimum one day resolution.
        """
        return EntsoEApiRequest(
            document_type=DocumentType.SYSTEM_TOTAL_LOAD,  # A65
            process_type=ProcessType.DAY_AHEAD,  # A01
            out_bidding_zone_domain=self.out_bidding_zone_domain,
            period_start=self.period_start,
            period_end=self.period_end,
            offset=self.offset,
        )

    def build_week_ahead_load_forecast(self) -> EntsoEApiRequest:
        """
        Build EntsoEApiRequest for Week-Ahead Total Load Forecast [6.1.C].
        DocumentType: A65 (System Total Load)
        ProcessType: A31 (Week Ahead)
        One year range limit, minimum one week resolution.
        """
        return EntsoEApiRequest(
            document_type=DocumentType.SYSTEM_TOTAL_LOAD,  # A65
            process_type=ProcessType.WEEK_AHEAD,  # A31
            out_bidding_zone_domain=self.out_bidding_zone_domain,
            period_start=self.period_start,
            period_end=self.period_end,
            offset=self.offset,
        )

    def build_month_ahead_load_forecast(self) -> EntsoEApiRequest:
        """
        Build EntsoEApiRequest for Month-Ahead Total Load Forecast [6.1.D].
        DocumentType: A65 (System Total Load)
        ProcessType: A32 (Month Ahead)
        One year range limit, minimum one month resolution.
        """
        return EntsoEApiRequest(
            document_type=DocumentType.SYSTEM_TOTAL_LOAD,  # A65
            process_type=ProcessType.MONTH_AHEAD,  # A32
            out_bidding_zone_domain=self.out_bidding_zone_domain,
            period_start=self.period_start,
            period_end=self.period_end,
            offset=self.offset,
        )

    def build_year_ahead_load_forecast(self) -> EntsoEApiRequest:
        """
        Build EntsoEApiRequest for Year-Ahead Total Load Forecast [6.1.E].
        DocumentType: A65 (System Total Load)
        ProcessType: A33 (Year Ahead)
        One year range limit, minimum one year resolution.
        """
        return EntsoEApiRequest(
            document_type=DocumentType.SYSTEM_TOTAL_LOAD,  # A65
            process_type=ProcessType.YEAR_AHEAD,  # A33
            out_bidding_zone_domain=self.out_bidding_zone_domain,
            period_start=self.period_start,
            period_end=self.period_end,
            offset=self.offset,
        )

    def build_year_ahead_forecast_margin(self) -> EntsoEApiRequest:
        """
        Build EntsoEApiRequest for Year-Ahead Forecast Margin [8.1].
        DocumentType: A70 (Load Forecast Margin)
        ProcessType: A33 (Year Ahead)
        One year range limit, minimum one year resolution.
        """
        return EntsoEApiRequest(
            document_type=DocumentType.LOAD_FORECAST_MARGIN,  # A70
            process_type=ProcessType.YEAR_AHEAD,  # A33
            out_bidding_zone_domain=self.out_bidding_zone_domain,
            period_start=self.period_start,
            period_end=self.period_end,
            offset=self.offset,
        )

    def _validate_bidding_zone(self, area_code: AreaCode) -> None:
        """Validate that the area code is a valid bidding zone."""
        if area_code and not area_code.has_area_type(AreaType.BZN):
            raise LoadDomainRequestBuilderError.invalid_bidding_zone(area_code)

    def _validate_date_range(self, start: datetime, end: datetime) -> None:
        """Validate the date range constraints."""
        if start and end:
            if start >= end:
                raise LoadDomainRequestBuilderError.period_start_after_end()

            # Check one year limit
            if start.replace(year=start.year + 1) < end:
                raise LoadDomainRequestBuilderError.date_range_exceeds_one_year()
