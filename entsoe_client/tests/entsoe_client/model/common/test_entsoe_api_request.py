"""Unit tests for EntsoEApiRequest quarter-hour alignment functionality."""

from datetime import UTC, datetime

import pytest

from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.document_type import DocumentType
from entsoe_client.model.common.entsoe_api_request import EntsoEApiRequest
from entsoe_client.model.common.process_type import ProcessType


class TestEntsoEApiRequestQuarterHourAlignment:
    """Test suite for quarter-hour alignment in EntsoEApiRequest."""

    @pytest.fixture
    def base_request_data(self) -> dict:
        """Base request data for testing."""
        return {
            "document_type": DocumentType.SYSTEM_TOTAL_LOAD,
            "process_type": ProcessType.REALISED,
            "out_bidding_zone_domain": AreaCode.CZECH_REPUBLIC,
        }

    def test_align_to_quarter_hour_round_down(self, base_request_data: dict) -> None:
        """Test quarter-hour alignment rounds down for period_start (offset=0)."""
        # Test cases: input minute -> expected aligned minute
        test_cases = [
            (7, 0),  # 7 minutes -> 0 (round down)
            (14, 0),  # 14 minutes -> 0 (round down)
            (15, 15),  # 15 minutes -> 15 (exact)
            (22, 15),  # 22 minutes -> 15 (round down)
            (29, 15),  # 29 minutes -> 15 (round down)
            (30, 30),  # 30 minutes -> 30 (exact)
            (37, 30),  # 37 minutes -> 30 (round down)
            (44, 30),  # 44 minutes -> 30 (round down)
            (45, 45),  # 45 minutes -> 45 (exact)
            (52, 45),  # 52 minutes -> 45 (round down)
            (59, 45),  # 59 minutes -> 45 (round down)
        ]

        for input_minute, expected_minute in test_cases:
            period_start = datetime(
                2024, 1, 1, 10, input_minute, 30, 123456, tzinfo=UTC
            )
            period_end = datetime(2024, 1, 1, 11, 0, tzinfo=UTC)

            request = EntsoEApiRequest(
                period_start=period_start, period_end=period_end, **base_request_data
            )

            aligned = request._align_to_quarter_hour(period_start, 0)
            assert aligned.minute == expected_minute
            assert aligned.second == 0
            assert aligned.microsecond == 0
            assert aligned.hour == 10  # Hour should not change

    def test_align_to_quarter_hour_round_up(self, base_request_data: dict) -> None:
        """Test quarter-hour alignment rounds up for period_end (offset=1)."""
        # Test cases: input minute -> expected aligned minute
        test_cases = [
            (0, 15),  # 0 minutes -> 15 (round up)
            (7, 15),  # 7 minutes -> 15 (round up)
            (14, 15),  # 14 minutes -> 15 (round up)
            (15, 30),  # 15 minutes -> 30 (round up)
            (22, 30),  # 22 minutes -> 30 (round up)
            (29, 30),  # 29 minutes -> 30 (round up)
            (30, 45),  # 30 minutes -> 45 (round up)
            (37, 45),  # 37 minutes -> 45 (round up)
            (44, 45),  # 44 minutes -> 45 (round up)
            (45, 0),  # 45 minutes -> 0 next hour (round up with overflow)
            (52, 0),  # 52 minutes -> 0 next hour (round up with overflow)
            (59, 0),  # 59 minutes -> 0 next hour (round up with overflow)
        ]

        for input_minute, expected_minute in test_cases:
            period_start = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
            period_end = datetime(2024, 1, 1, 10, input_minute, 30, 123456, tzinfo=UTC)

            request = EntsoEApiRequest(
                period_start=period_start, period_end=period_end, **base_request_data
            )

            aligned = request._align_to_quarter_hour(period_end, 1)
            assert aligned.minute == expected_minute
            assert aligned.second == 0
            assert aligned.microsecond == 0

            # Check hour overflow for cases where minute becomes 0
            if expected_minute == 0:
                assert aligned.hour == 11  # Hour should increment
            else:
                assert aligned.hour == 10  # Hour should not change

    def test_hour_overflow_at_day_boundary(self, base_request_data: dict) -> None:
        """Test hour overflow at day boundary (23:xx -> 00:xx next day)."""
        period_start = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
        period_end = datetime(2024, 1, 1, 23, 50, tzinfo=UTC)  # 23:50

        request = EntsoEApiRequest(
            period_start=period_start, period_end=period_end, **base_request_data
        )

        aligned = request._align_to_quarter_hour(period_end, 1)  # Round up

        # 23:50 with offset=1 should become 00:00 next day
        assert aligned.hour == 0
        assert aligned.minute == 0
        assert aligned.day == 2  # Next day
        assert aligned.month == 1
        assert aligned.year == 2024

    def test_to_parameter_map_applies_alignment(self, base_request_data: dict) -> None:
        """Test that to_parameter_map applies quarter-hour alignment."""
        # Use non-aligned times
        period_start = datetime(2024, 1, 1, 10, 7, 30, tzinfo=UTC)  # 10:07:30
        period_end = datetime(2024, 1, 1, 11, 52, 45, tzinfo=UTC)  # 11:52:45

        request = EntsoEApiRequest(
            period_start=period_start, period_end=period_end, **base_request_data
        )

        params = request.to_parameter_map()

        # period_start with offset=0 should round down: 10:07 -> 10:00
        assert params["periodStart"] == "202401011000"

        # period_end with offset=1 should round up: 11:52 -> 12:00
        assert params["periodEnd"] == "202401011200"

    def test_format_datetime_preserves_date_components(
        self, base_request_data: dict
    ) -> None:
        """Test that _format_datetime preserves year, month, day correctly."""
        test_datetime = datetime(2024, 12, 31, 14, 37, 22, 555666, tzinfo=UTC)

        request = EntsoEApiRequest(
            period_start=test_datetime, period_end=test_datetime, **base_request_data
        )

        # Test both offsets
        formatted_down = request._format_datetime(test_datetime, 0)  # Round down
        formatted_up = request._format_datetime(test_datetime, 1)  # Round up

        # Should preserve year, month, day
        assert formatted_down.startswith("20241231")  # 14:37 -> 14:30
        assert formatted_up.startswith("20241231")  # 14:37 -> 14:45

        assert formatted_down == "202412311430"
        assert formatted_up == "202412311445"
