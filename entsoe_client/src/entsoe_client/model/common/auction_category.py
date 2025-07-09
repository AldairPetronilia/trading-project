from enum import Enum
from typing import Self

from src.entsoe_client.exceptions.unknown_auction_category_error import (
    UnknownAuctionCategoryError,
)


class AuctionCategory(Enum):
    BASE = ("A01", "Base")
    PEAK = ("A02", "Peak")
    OFF_PEAK = ("A03", "Off Peak")
    HOURLY = ("A04", "Hourly")

    def __init__(self, code: str, description: str) -> None:
        self.code = code
        self.description = description

    @classmethod
    def from_code(cls, code: str) -> Self:
        for member in cls:
            if member.code == code:
                return member
        raise UnknownAuctionCategoryError(code)
