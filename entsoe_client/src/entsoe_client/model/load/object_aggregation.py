from enum import Enum
from typing import Self

from entsoe_client.exceptions.unknown_object_aggregation_error import (
    UnknownObjectAggregationError,
)


class ObjectAggregation(Enum):
    AGGREGATED = ("A01", "Aggregated")
    INDIVIDUAL = ("A02", "Individual")

    def __init__(self, code: str, description: str) -> None:
        self.code = code
        self.description = description

    @classmethod
    def from_code(cls, code: str) -> Self:
        for member in cls:
            if member.code == code:
                return member
        raise UnknownObjectAggregationError(code)
