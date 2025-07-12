from enum import Enum
from typing import Self

from entsoe_client.exceptions.unknown_market_role_type_error import (
    UnknownMarketRoleTypeError,
)


class MarketRoleType(Enum):
    ISSUING_OFFICE = ("A32", "Issuing Office")
    MARKET_OPERATOR = ("A33", "Market Operator")

    def __init__(self, code: str, description: str) -> None:
        self.code = code
        self.description = description

    @classmethod
    def from_code(cls, code: str) -> Self:
        for member in cls:
            if member.code == code:
                return member
        raise UnknownMarketRoleTypeError(code)
