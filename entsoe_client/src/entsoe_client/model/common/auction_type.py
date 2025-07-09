from enum import Enum
from typing import Self

from src.entsoe_client.exceptions.unknown_auction_type_error import (
    UnknownAuctionTypeError,
)


class AuctionType(Enum):
    IMPLICIT = ("A01", "Implicit")
    EXPLICIT = ("A02", "Explicit")

    def __init__(self, code: str, description: str):
        self.code = code
        self.description = description

    @classmethod
    def from_code(cls, code: str) -> Self:
        for member in cls:
            if member.code == code:
                return member
        raise UnknownAuctionTypeError
