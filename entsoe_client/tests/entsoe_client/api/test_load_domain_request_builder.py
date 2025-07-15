"""Unit tests for LoadDomainRequestBuilder."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from entsoe_client.api.load_domain_request_builder import LoadDomainRequestBuilder
from entsoe_client.exceptions.load_domain_request_builder_error import (
    LoadDomainRequestBuilderError,
)
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.area_type import AreaType
from entsoe_client.model.common.document_type import DocumentType
from entsoe_client.model.common.entsoe_api_request import EntsoEApiRequest
from entsoe_client.model.common.process_type import ProcessType


class TestLoadDomainRequestBuilder:
    """Test suite for LoadDomainRequestBuilder."""

    @pytest.fixture
    def valid_start_date(self) -> datetime:
        """Valid start date for testing."""
        return datetime(2024, 1, 1, tzinfo=UTC)

    @pytest.fixture
    def valid_end_date(self) -> datetime:
        """Valid end date for testing."""
        return datetime(2024, 1, 31, tzinfo=UTC)

    @pytest.fixture
    def valid_bidding_zone(self) -> AreaCode:
        """Valid bidding zone for testing."""
        return AreaCode.CZECH_REPUBLIC

    @pytest.fixture
    def invalid_bidding_zone(self) -> AreaCode:
        """Invalid bidding zone (not BZN type) for testing."""
        # Use NORDIC which doesn't have BZN type (only SNA, REG, LFB)
        return AreaCode.NORDIC

    @pytest.fixture
    def builder(
        self,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
    ) -> LoadDomainRequestBuilder:
        """Create a valid LoadDomainRequestBuilder instance."""
        return LoadDomainRequestBuilder(
            out_bidding_zone_domain=valid_bidding_zone,
            period_start=valid_start_date,
            period_end=valid_end_date,
        )

    def test_init_with_valid_params(
        self,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
    ) -> None:
        """Test initialization with valid parameters."""
        builder = LoadDomainRequestBuilder(
            out_bidding_zone_domain=valid_bidding_zone,
            period_start=valid_start_date,
            period_end=valid_end_date,
        )

        assert builder.out_bidding_zone_domain == valid_bidding_zone
        assert builder.period_start == valid_start_date
        assert builder.period_end == valid_end_date
        assert builder.time_interval is None
        assert builder.offset is None

    def test_init_with_optional_params(
        self,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
    ) -> None:
        """Test initialization with optional parameters."""
        builder = LoadDomainRequestBuilder(
            out_bidding_zone_domain=valid_bidding_zone,
            period_start=valid_start_date,
            period_end=valid_end_date,
            time_interval="PT1H",
            offset=100,
        )

        assert builder.time_interval == "PT1H"
        assert builder.offset == 100

    def test_init_missing_bidding_zone_domain(
        self,
        valid_start_date: datetime,
        valid_end_date: datetime,
    ) -> None:
        """Test initialization fails when bidding zone domain is missing."""
        with pytest.raises(LoadDomainRequestBuilderError) as exc_info:
            LoadDomainRequestBuilder(
                out_bidding_zone_domain=None,  # type: ignore[arg-type]
                period_start=valid_start_date,
                period_end=valid_end_date,
            )

        assert "out_bidding_zone_domain is required" in str(exc_info.value)

    def test_init_missing_period_start(
        self,
        valid_bidding_zone: AreaCode,
        valid_end_date: datetime,
    ) -> None:
        """Test initialization fails when period start is missing."""
        with pytest.raises(LoadDomainRequestBuilderError) as exc_info:
            LoadDomainRequestBuilder(
                out_bidding_zone_domain=valid_bidding_zone,
                period_start=None,  # type: ignore[arg-type]
                period_end=valid_end_date,
            )

        assert "period_start is required" in str(exc_info.value)

    def test_init_missing_period_end(
        self,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
    ) -> None:
        """Test initialization fails when period end is missing."""
        with pytest.raises(LoadDomainRequestBuilderError) as exc_info:
            LoadDomainRequestBuilder(
                out_bidding_zone_domain=valid_bidding_zone,
                period_start=valid_start_date,
                period_end=None,  # type: ignore[arg-type]
            )

        assert "period_end is required" in str(exc_info.value)

    def test_init_invalid_bidding_zone(
        self,
        invalid_bidding_zone: AreaCode,
        valid_start_date: datetime,
        valid_end_date: datetime,
    ) -> None:
        """Test initialization fails with invalid bidding zone."""
        with pytest.raises(LoadDomainRequestBuilderError) as exc_info:
            LoadDomainRequestBuilder(
                out_bidding_zone_domain=invalid_bidding_zone,
                period_start=valid_start_date,
                period_end=valid_end_date,
            )

        assert "is not a valid bidding zone" in str(exc_info.value)

    def test_init_period_start_after_end(
        self,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
    ) -> None:
        """Test initialization fails when period start is after end."""
        with pytest.raises(LoadDomainRequestBuilderError) as exc_info:
            LoadDomainRequestBuilder(
                out_bidding_zone_domain=valid_bidding_zone,
                period_start=valid_start_date,
                period_end=valid_start_date,  # Same date, so start >= end
            )

        assert "Period start must be before period end" in str(exc_info.value)

    def test_init_date_range_exceeds_one_year(
        self,
        valid_bidding_zone: AreaCode,
        valid_start_date: datetime,
    ) -> None:
        """Test initialization fails when date range exceeds one year."""
        end_date = valid_start_date.replace(year=valid_start_date.year + 1, day=2)

        with pytest.raises(LoadDomainRequestBuilderError) as exc_info:
            LoadDomainRequestBuilder(
                out_bidding_zone_domain=valid_bidding_zone,
                period_start=valid_start_date,
                period_end=end_date,
            )

        assert "Date range cannot exceed one year" in str(exc_info.value)

    def test_builder_factory_method(self) -> None:
        """Test the builder factory method."""
        builder = LoadDomainRequestBuilder.builder()
        assert isinstance(builder, LoadDomainRequestBuilder)

    def test_for_bidding_zone_fluent_interface(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test for_bidding_zone method returns self for fluent interface."""
        result = builder.for_bidding_zone(AreaCode.FINLAND)
        assert result is builder
        assert builder.out_bidding_zone_domain == AreaCode.FINLAND

    def test_for_bidding_zone_invalid_zone(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test for_bidding_zone with invalid zone raises error."""
        # Use NORDIC which doesn't have BZN type
        with pytest.raises(LoadDomainRequestBuilderError) as exc_info:
            builder.for_bidding_zone(AreaCode.NORDIC)

        assert "is not a valid bidding zone" in str(exc_info.value)

    def test_from_period_fluent_interface(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test from_period method returns self for fluent interface."""
        new_start = datetime(2024, 2, 1, tzinfo=UTC)
        new_end = datetime(2024, 2, 28, tzinfo=UTC)

        result = builder.from_period(new_start, new_end)
        assert result is builder
        assert builder.period_start == new_start
        assert builder.period_end == new_end

    def test_from_period_invalid_range(self, builder: LoadDomainRequestBuilder) -> None:
        """Test from_period with invalid range raises error."""
        start = datetime(2024, 2, 1, tzinfo=UTC)
        end = datetime(2024, 1, 31, tzinfo=UTC)  # End before start

        with pytest.raises(LoadDomainRequestBuilderError) as exc_info:
            builder.from_period(start, end)

        assert "Period start must be before period end" in str(exc_info.value)

    def test_with_time_interval_fluent_interface(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test with_time_interval method returns self for fluent interface."""
        result = builder.with_time_interval("PT15M")
        assert result is builder
        assert builder.time_interval == "PT15M"

    def test_with_offset_fluent_interface(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test with_offset method returns self for fluent interface."""
        result = builder.with_offset(500)
        assert result is builder
        assert builder.offset == 500

    def test_build_actual_total_load(self, builder: LoadDomainRequestBuilder) -> None:
        """Test build_actual_total_load creates correct request."""
        request = builder.build_actual_total_load()

        assert isinstance(request, EntsoEApiRequest)
        assert request.document_type == DocumentType.SYSTEM_TOTAL_LOAD
        assert request.process_type == ProcessType.REALISED
        assert request.out_bidding_zone_domain == builder.out_bidding_zone_domain
        assert request.period_start == builder.period_start
        assert request.period_end == builder.period_end
        assert request.offset == builder.offset

    def test_build_day_ahead_load_forecast(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test build_day_ahead_load_forecast creates correct request."""
        request = builder.build_day_ahead_load_forecast()

        assert isinstance(request, EntsoEApiRequest)
        assert request.document_type == DocumentType.SYSTEM_TOTAL_LOAD
        assert request.process_type == ProcessType.DAY_AHEAD
        assert request.out_bidding_zone_domain == builder.out_bidding_zone_domain
        assert request.period_start == builder.period_start
        assert request.period_end == builder.period_end
        assert request.offset == builder.offset

    def test_build_week_ahead_load_forecast(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test build_week_ahead_load_forecast creates correct request."""
        request = builder.build_week_ahead_load_forecast()

        assert isinstance(request, EntsoEApiRequest)
        assert request.document_type == DocumentType.SYSTEM_TOTAL_LOAD
        assert request.process_type == ProcessType.WEEK_AHEAD
        assert request.out_bidding_zone_domain == builder.out_bidding_zone_domain
        assert request.period_start == builder.period_start
        assert request.period_end == builder.period_end
        assert request.offset == builder.offset

    def test_build_month_ahead_load_forecast(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test build_month_ahead_load_forecast creates correct request."""
        request = builder.build_month_ahead_load_forecast()

        assert isinstance(request, EntsoEApiRequest)
        assert request.document_type == DocumentType.SYSTEM_TOTAL_LOAD
        assert request.process_type == ProcessType.MONTH_AHEAD
        assert request.out_bidding_zone_domain == builder.out_bidding_zone_domain
        assert request.period_start == builder.period_start
        assert request.period_end == builder.period_end
        assert request.offset == builder.offset

    def test_build_year_ahead_load_forecast(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test build_year_ahead_load_forecast creates correct request."""
        request = builder.build_year_ahead_load_forecast()

        assert isinstance(request, EntsoEApiRequest)
        assert request.document_type == DocumentType.SYSTEM_TOTAL_LOAD
        assert request.process_type == ProcessType.YEAR_AHEAD
        assert request.out_bidding_zone_domain == builder.out_bidding_zone_domain
        assert request.period_start == builder.period_start
        assert request.period_end == builder.period_end
        assert request.offset == builder.offset

    def test_build_year_ahead_forecast_margin(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test build_year_ahead_forecast_margin creates correct request."""
        request = builder.build_year_ahead_forecast_margin()

        assert isinstance(request, EntsoEApiRequest)
        assert request.document_type == DocumentType.LOAD_FORECAST_MARGIN
        assert request.process_type == ProcessType.YEAR_AHEAD
        assert request.out_bidding_zone_domain == builder.out_bidding_zone_domain
        assert request.period_start == builder.period_start
        assert request.period_end == builder.period_end
        assert request.offset == builder.offset

    def test_fluent_interface_chaining(self, valid_bidding_zone: AreaCode) -> None:
        """Test that methods can be chained together in fluent interface style."""
        start = datetime(2024, 3, 1, tzinfo=UTC)
        end = datetime(2024, 3, 31, tzinfo=UTC)

        builder = (
            LoadDomainRequestBuilder.builder()
            .for_bidding_zone(valid_bidding_zone)
            .from_period(start, end)
            .with_time_interval("PT1H")
            .with_offset(200)
        )

        assert builder.out_bidding_zone_domain == valid_bidding_zone
        assert builder.period_start == start
        assert builder.period_end == end
        assert builder.time_interval == "PT1H"
        assert builder.offset == 200

    def test_validate_bidding_zone_with_valid_zone(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test _validate_bidding_zone with valid bidding zone."""
        # Should not raise any exception
        builder._validate_bidding_zone(AreaCode.CZECH_REPUBLIC)

    def test_validate_bidding_zone_with_none(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test _validate_bidding_zone with None (should pass)."""
        # Should not raise any exception when area_code is None
        builder._validate_bidding_zone(None)  # type: ignore[arg-type]

    def test_validate_date_range_with_valid_range(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test _validate_date_range with valid date range."""
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 6, 1, tzinfo=UTC)

        # Should not raise any exception
        builder._validate_date_range(start, end)

    def test_validate_date_range_with_none_values(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test _validate_date_range with None values (should pass)."""
        # Should not raise any exception when dates are None
        builder._validate_date_range(None, None)  # type: ignore[arg-type]

    def test_validate_date_range_one_year_boundary(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test _validate_date_range at exactly one year boundary."""
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2025, 1, 1, tzinfo=UTC)  # Exactly one year

        # Should not raise any exception
        builder._validate_date_range(start, end)

    def test_build_with_offset_included(
        self,
        builder: LoadDomainRequestBuilder,
    ) -> None:
        """Test that offset is properly included in built requests."""
        builder.with_offset(123)

        request = builder.build_actual_total_load()
        assert request.offset == 123

        request = builder.build_day_ahead_load_forecast()
        assert request.offset == 123
