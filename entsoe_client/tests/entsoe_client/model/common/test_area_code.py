"""Tests for AreaCode enum and its methods."""

import pytest

from entsoe_client.exceptions.unknown_area_code_error import UnknownAreaCodeError
from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.area_type import AreaType


class TestAreaCodeFromCode:
    """Test the from_code class method."""

    def test_from_code_success(self) -> None:
        """Test from_code returns correct enum member for valid codes."""
        assert AreaCode.from_code("10YFR-RTE------C") == AreaCode.FRANCE
        assert AreaCode.from_code("10YIT-GRTN-----B") == AreaCode.ITALY
        assert AreaCode.from_code("10YES-REE------0") == AreaCode.SPAIN
        assert AreaCode.from_code("10YDE-VE-------2") == AreaCode.DE_50HERTZ

    def test_from_code_failure(self) -> None:
        """Test from_code raises UnknownAreaCodeError for invalid codes."""
        invalid_codes = ["INVALID-CODE", "10YINVALID-----X", "", "NOT-A-REAL-CODE"]

        for invalid_code in invalid_codes:
            with pytest.raises(UnknownAreaCodeError) as exc_info:
                AreaCode.from_code(invalid_code)
            assert invalid_code in str(exc_info.value)


class TestAreaCodeSafeFromCode:
    """Test the _safe_from_code method."""

    def test_safe_from_code_success(self) -> None:
        """Test _safe_from_code returns enum member for valid codes."""
        france = AreaCode.FRANCE
        result = france._safe_from_code("10YIT-GRTN-----B")
        assert result == AreaCode.ITALY

    def test_safe_from_code_failure(self) -> None:
        """Test _safe_from_code returns None for invalid codes."""
        france = AreaCode.FRANCE
        result = france._safe_from_code("INVALID-CODE")
        assert result is None


class TestAreaCodeCountryCode:
    """Test the get_country_code method."""

    @pytest.mark.parametrize(
        ("area_code", "expected_country"),
        [
            (AreaCode.FRANCE, "FR"),
            (AreaCode.GERMANY, "DE"),
            (AreaCode.SPAIN, "ES"),
            (AreaCode.ITALY, "IT"),
            (AreaCode.BELGIUM, "BE"),
            (AreaCode.NETHERLANDS, "NL"),
            (AreaCode.POLAND, "PL"),
            (AreaCode.UNITED_KINGDOM, "UK"),
            (AreaCode.SWEDEN_SE1, "SE"),
            (AreaCode.DENMARK_DK1, "DK"),
            (AreaCode.IT_SACOAC, "IT"),  # Tests extraction from BZN|IT-SACOAC
            (AreaCode.UKRAINE_BEI, "UA"),  # Tests extraction from multiple patterns
            (AreaCode.CWE_REGION, "CW"),  # Regional code that extracts CW from REG|CWE
        ],
    )
    def test_get_country_code_success(
        self,
        area_code: AreaCode,
        expected_country: str,
    ) -> None:
        """Test country code extraction for various area codes."""
        assert area_code.get_country_code() == expected_country

    @pytest.mark.parametrize(
        "area_code",
        [
            AreaCode.NORDIC,  # No country code in regional area
            AreaCode.CONTINENTAL_EUROPE,  # Continental region
        ],
    )
    def test_get_country_code_no_match(self, area_code: AreaCode) -> None:
        """Test that regional codes return None."""
        assert area_code.get_country_code() is None


class TestAreaCodeAreaTypes:
    """Test area type related methods."""

    def test_get_area_types_list(self) -> None:
        """Test that get_area_types_list returns list of AreaType enums."""
        # Test with a code that has multiple area types
        france = AreaCode.FRANCE
        area_types = france.get_area_types_list()

        # Should return a list of AreaType enums
        assert isinstance(area_types, list)
        # All items should be AreaType enums (or None filtered out)
        for area_type in area_types:
            assert isinstance(area_type, AreaType)

    def test_get_area_types_list_empty(self) -> None:
        """Test area codes with no parseable area types."""
        # Test with codes that might not have parseable area types
        area_types = AreaCode.ICELAND.get_area_types_list()
        assert isinstance(area_types, list)

    def test_has_area_type(self) -> None:
        """Test has_area_type method with known area types."""
        # This test depends on the AreaType enum having specific values
        # We'll test the method functionality rather than specific values
        france = AreaCode.FRANCE
        area_types = france.get_area_types_list()

        if area_types:  # If there are any area types
            # Test that has_area_type returns True for existing types
            for area_type in area_types:
                assert france.has_area_type(area_type) is True


class TestAreaCodeBasicProperties:
    """Test basic enum properties."""

    def test_area_code_properties(self) -> None:
        """Test that AreaCode instances have required properties."""
        france = AreaCode.FRANCE

        assert hasattr(france, "code")
        assert hasattr(france, "area_types")
        assert hasattr(france, "description")

        assert isinstance(france.code, str)
        assert isinstance(france.area_types, str)
        assert isinstance(france.description, str)

    def test_area_code_values(self) -> None:
        """Test specific known values."""
        assert AreaCode.FRANCE.code == "10YFR-RTE------C"
        assert AreaCode.FRANCE.description == "France "
        assert "France (FR)" in AreaCode.FRANCE.area_types

    def test_enum_membership(self) -> None:
        """Test that all area codes are accessible as enum members."""
        # Test a few key area codes exist
        assert AreaCode.FRANCE in AreaCode
        assert AreaCode.GERMANY in AreaCode
        assert AreaCode.ITALY in AreaCode
        assert AreaCode.SPAIN in AreaCode


class TestAreaCodeEdgeCases:
    """Test edge cases and error conditions."""

    def test_from_code_case_sensitivity(self) -> None:
        """Test that from_code is case sensitive."""
        with pytest.raises(UnknownAreaCodeError):
            AreaCode.from_code("10yfr-rte------c")  # lowercase

    def test_from_code_whitespace(self) -> None:
        """Test that from_code doesn't handle whitespace."""
        with pytest.raises(UnknownAreaCodeError):
            AreaCode.from_code(" 10YFR-RTE------C ")  # with spaces

    def test_area_code_uniqueness(self) -> None:
        """Test that all area codes have unique codes."""
        codes = [member.code for member in AreaCode]
        assert len(codes) == len(set(codes)), "Duplicate area codes found"
