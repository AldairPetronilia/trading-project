"""Tests for MarketDomainRequestBuilder."""

from datetime import UTC, datetime, timezone

import pytest

from entsoe_client.api.market_domain_request_builder import MarketDomainRequestBuilder
from entsoe_client.exceptions.market_domain_request_builder_error import (
    MarketDomainRequestBuilderError,
)
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.business_type import BusinessType
from entsoe_client.model.common.document_type import DocumentType


class TestMarketDomainRequestBuilderSuccess:
    """Success scenarios for MarketDomainRequestBuilder."""

    def test_build_day_ahead_prices_success(self) -> None:
        """Test successful day-ahead prices request building."""
        builder = MarketDomainRequestBuilder(
            in_domain=AreaCode.CZECH_REPUBLIC,
            out_domain=AreaCode.CZECH_REPUBLIC,
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 2, tzinfo=UTC),
        )

        request = builder.build_day_ahead_prices()

        assert request.document_type == DocumentType.PRICE_DOCUMENT
        assert request.business_type == BusinessType.DAY_AHEAD_PRICES
        assert request.in_domain == AreaCode.CZECH_REPUBLIC
        assert request.out_domain == AreaCode.CZECH_REPUBLIC
        assert request.period_start == datetime(2024, 1, 1, tzinfo=UTC)
        assert request.period_end == datetime(2024, 1, 2, tzinfo=UTC)
        assert request.offset is None

    def test_build_day_ahead_prices_with_offset(self) -> None:
        """Test day-ahead prices request with pagination offset."""
        builder = MarketDomainRequestBuilder(
            in_domain=AreaCode.CZECH_REPUBLIC,
            out_domain=AreaCode.CZECH_REPUBLIC,
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 2, tzinfo=UTC),
            offset=100,
        )

        request = builder.build_day_ahead_prices()
        assert request.offset == 100

    def test_fluent_interface_pattern(self) -> None:
        """Test fluent interface pattern for builder."""
        request = (
            MarketDomainRequestBuilder.builder()
            .for_domains(AreaCode.CZECH_REPUBLIC, AreaCode.CZECH_REPUBLIC)
            .from_period(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 1, 2, tzinfo=UTC)
            )
            .with_offset(50)
            .build_day_ahead_prices()
        )

        assert request.document_type == DocumentType.PRICE_DOCUMENT
        assert request.business_type == BusinessType.DAY_AHEAD_PRICES
        assert request.offset == 50


class TestMarketDomainRequestBuilderValidation:
    """Validation tests for MarketDomainRequestBuilder."""

    def test_domain_validation_failure(self) -> None:
        """Test that mismatched domains fail validation."""
        builder = MarketDomainRequestBuilder(
            in_domain=AreaCode.CZECH_REPUBLIC,
            out_domain=AreaCode.FINLAND,
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 2, tzinfo=UTC),
        )
        with pytest.raises(MarketDomainRequestBuilderError) as exc_info:
            builder.build_day_ahead_prices()

        error_msg = str(exc_info.value)
        assert (
            "in_domain (10YCZ-CEPS-----N) must equal out_domain (10YFI-1--------U)"
            in error_msg
        )

    def test_missing_in_domain_validation(self) -> None:
        """Test validation fails for missing in_domain."""
        with pytest.raises(MarketDomainRequestBuilderError) as exc_info:
            MarketDomainRequestBuilder(
                in_domain=None,  # type: ignore[arg-type]
                out_domain=AreaCode.CZECH_REPUBLIC,
                period_start=datetime(2024, 1, 1, tzinfo=UTC),
                period_end=datetime(2024, 1, 2, tzinfo=UTC),
            )

        assert "in_domain is required" in str(exc_info.value)

    def test_missing_out_domain_validation(self) -> None:
        """Test validation fails for missing out_domain."""
        with pytest.raises(MarketDomainRequestBuilderError) as exc_info:
            MarketDomainRequestBuilder(
                in_domain=AreaCode.CZECH_REPUBLIC,
                out_domain=None,  # type: ignore[arg-type]
                period_start=datetime(2024, 1, 1, tzinfo=UTC),
                period_end=datetime(2024, 1, 2, tzinfo=UTC),
            )

        assert "out_domain is required" in str(exc_info.value)

    def test_period_start_after_end_validation(self) -> None:
        """Test validation fails when period_start is after period_end."""
        with pytest.raises(MarketDomainRequestBuilderError) as exc_info:
            MarketDomainRequestBuilder(
                in_domain=AreaCode.CZECH_REPUBLIC,
                out_domain=AreaCode.CZECH_REPUBLIC,
                period_start=datetime(2024, 1, 2, tzinfo=UTC),
                period_end=datetime(2024, 1, 1, tzinfo=UTC),
            )

        assert "Period start must be before period end" in str(exc_info.value)

    def test_date_range_exceeds_one_year_validation(self) -> None:
        """Test validation fails for date ranges exceeding one year."""
        with pytest.raises(MarketDomainRequestBuilderError) as exc_info:
            MarketDomainRequestBuilder(
                in_domain=AreaCode.CZECH_REPUBLIC,
                out_domain=AreaCode.CZECH_REPUBLIC,
                period_start=datetime(2024, 1, 1, tzinfo=UTC),
                period_end=datetime(2025, 1, 2, tzinfo=UTC),  # More than one year
            )

        assert "Date range cannot exceed one year" in str(exc_info.value)


class TestPhysicalFlowsBuilder:
    """Test physical flows request building."""

    def test_build_physical_flows_success(self) -> None:
        """Test successful physical flows request with different domains."""
        builder = MarketDomainRequestBuilder(
            in_domain=AreaCode.CZECH_REPUBLIC,  # 10YCZ-CEPS-----N
            out_domain=AreaCode.SLOVAKIA,  # 10YSK-SEPS-----K
            period_start=datetime(2016, 1, 1, tzinfo=UTC),
            period_end=datetime(2016, 1, 2, tzinfo=UTC),
        )

        request = builder.build_physical_flows()

        assert (
            request.document_type == DocumentType.AGGREGATED_ENERGY_DATA_REPORT
        )  # A11
        assert request.business_type == BusinessType.PHYSICAL_FLOWS  # A66
        assert request.in_domain == AreaCode.CZECH_REPUBLIC
        assert request.out_domain == AreaCode.SLOVAKIA

    def test_build_physical_flows_same_domains_fails(self) -> None:
        """Test that same domains raise validation error for flows."""
        builder = MarketDomainRequestBuilder(
            in_domain=AreaCode.CZECH_REPUBLIC,  # Same domain
            out_domain=AreaCode.CZECH_REPUBLIC,  # Same domain - INVALID
            period_start=datetime(2016, 1, 1, tzinfo=UTC),
            period_end=datetime(2016, 1, 2, tzinfo=UTC),
        )

        with pytest.raises(MarketDomainRequestBuilderError) as exc_info:
            builder.build_physical_flows()

        assert "Physical flows require different domains" in str(exc_info.value)

    def test_validation_difference_with_price_requests(self) -> None:
        """Test that physical flows and price requests have opposite domain validation."""
        # Same domains - valid for prices, invalid for flows
        same_domain_builder = MarketDomainRequestBuilder(
            in_domain=AreaCode.CZECH_REPUBLIC,
            out_domain=AreaCode.CZECH_REPUBLIC,  # Same as in_domain
            period_start=datetime(2016, 1, 1, tzinfo=UTC),
            period_end=datetime(2016, 1, 2, tzinfo=UTC),
        )

        # Price request should succeed with same domains
        price_request = same_domain_builder.build_day_ahead_prices()
        assert price_request.business_type == BusinessType.DAY_AHEAD_PRICES

        # Physical flows request should fail with same domains
        with pytest.raises(MarketDomainRequestBuilderError) as exc_info:
            same_domain_builder.build_physical_flows()
        assert "Physical flows require different domains" in str(exc_info.value)

        # Different domains - invalid for prices, valid for flows
        different_domain_builder = MarketDomainRequestBuilder(
            in_domain=AreaCode.CZECH_REPUBLIC,
            out_domain=AreaCode.FINLAND,  # Different from in_domain
            period_start=datetime(2016, 1, 1, tzinfo=UTC),
            period_end=datetime(2016, 1, 2, tzinfo=UTC),
        )

        # Price request should fail with different domains
        with pytest.raises(MarketDomainRequestBuilderError) as exc_info:
            different_domain_builder.build_day_ahead_prices()
        error_msg = str(exc_info.value)
        assert "in_domain" in error_msg
        assert "must equal out_domain" in error_msg

        # Physical flows request should succeed with different domains
        flows_request = different_domain_builder.build_physical_flows()
        assert flows_request.business_type == BusinessType.PHYSICAL_FLOWS
