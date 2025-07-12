from enum import Enum
from typing import Self

from entsoe_client.exceptions.unknown_curve_type_error import (
    UnknownCurveTypeError,
)


class CurveType(Enum):
    SEQUENTIAL_FIXED_SIZE_BLOCK = ("A01", "Sequential fixed size block")
    POINT_TO_POINT = ("A02", "Point to point")
    VARIABLE_SIZED_BLOCK = ("A03", "Variable sized block")

    def __init__(self, code: str, description: str) -> None:
        self.code = code
        self.description = description

    @classmethod
    def from_code(cls, code: str) -> Self:
        for member in cls:
            if member.code == code:
                return member
        raise UnknownCurveTypeError(code)
