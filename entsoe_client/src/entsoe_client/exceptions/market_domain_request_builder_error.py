"""Exception for market domain request builder validation."""

from entsoe_client.model.common.area_code import AreaCode


class MarketDomainRequestBuilderError(ValueError):
    """Exception raised by MarketDomainRequestBuilder validation."""

    def __init__(self, message: str) -> None:
        super().__init__(message)

    @classmethod
    def in_domain_required(cls) -> "MarketDomainRequestBuilderError":
        """Create error for missing in_domain."""
        msg = "in_domain is required"
        return cls(msg)

    @classmethod
    def out_domain_required(cls) -> "MarketDomainRequestBuilderError":
        """Create error for missing out_domain."""
        msg = "out_domain is required"
        return cls(msg)

    @classmethod
    def period_start_required(cls) -> "MarketDomainRequestBuilderError":
        """Create error for missing period_start."""
        msg = "period_start is required"
        return cls(msg)

    @classmethod
    def period_end_required(cls) -> "MarketDomainRequestBuilderError":
        """Create error for missing period_end."""
        msg = "period_end is required"
        return cls(msg)

    @classmethod
    def domains_must_be_equal(
        cls,
        in_domain: AreaCode,
        out_domain: AreaCode,
    ) -> "MarketDomainRequestBuilderError":
        """Create error for mismatched domains in price requests."""
        msg = f"For price requests, in_domain ({in_domain.code}) must equal out_domain ({out_domain.code})"
        return cls(msg)

    @classmethod
    def period_start_after_end(cls) -> "MarketDomainRequestBuilderError":
        """Create error for period start after end."""
        msg = "Period start must be before period end"
        return cls(msg)

    @classmethod
    def date_range_exceeds_one_year(cls) -> "MarketDomainRequestBuilderError":
        """Create error for date range exceeding one year."""
        msg = "Date range cannot exceed one year"
        return cls(msg)
