from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.area_type import AreaType


class LoadDomainRequestBuilderError(ValueError):
    """Exception raised by LoadDomainRequestBuilder validation."""

    def __init__(self, message: str) -> None:
        super().__init__(message)

    @classmethod
    def out_bidding_zone_domain_required(cls) -> "LoadDomainRequestBuilderError":
        """Create error for missing out_bidding_zone_domain."""
        msg = "out_bidding_zone_domain is required"
        return cls(msg)

    @classmethod
    def period_start_required(cls) -> "LoadDomainRequestBuilderError":
        """Create error for missing period_start."""
        msg = "period_start is required"
        return cls(msg)

    @classmethod
    def period_end_required(cls) -> "LoadDomainRequestBuilderError":
        """Create error for missing period_end."""
        msg = "period_end is required"
        return cls(msg)

    @classmethod
    def invalid_bidding_zone(
        cls,
        area_code: AreaCode,
    ) -> "LoadDomainRequestBuilderError":
        """Create error for invalid bidding zone."""
        msg = f"Area {area_code.description} ({area_code.code}) is not a valid bidding zone. Required type: {AreaType.BZN.value}"
        return cls(msg)

    @classmethod
    def period_start_after_end(cls) -> "LoadDomainRequestBuilderError":
        """Create error for period start after end."""
        msg = "Period start must be before period end"
        return cls(msg)

    @classmethod
    def date_range_exceeds_one_year(cls) -> "LoadDomainRequestBuilderError":
        """Create error for date range exceeding one year."""
        msg = "Date range cannot exceed one year"
        return cls(msg)
