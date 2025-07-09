from enum import Enum
from typing import Self

from src.entsoe_client.exceptions.unknown_contract_market_agreement_type_error import (
    UnknownContractMarketAgreementTypeError,
)


class ContractMarketAgreementType(Enum):
    DAILY = ("A01", "Daily")
    WEEKLY = ("A02", "Weekly")
    MONTHLY = ("A03", "Monthly")
    YEARLY = ("A04", "Yearly")
    TOTAL = ("A05", "Total")
    LONG_TERM = ("A06", "Long term")
    INTRADAY = ("A07", "Intraday")
    HOURLY = ("A13", "Hourly")

    def __init__(self, code: str, description: str) -> None:
        self.code = code
        self.description = description

    @classmethod
    def from_code(cls, code: str) -> Self:
        for member in cls:
            if member.code == code:
                return member
        raise UnknownContractMarketAgreementTypeError(code)
