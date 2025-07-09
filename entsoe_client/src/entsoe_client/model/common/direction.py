from enum import Enum
from typing import Self

from src.entsoe_client.exceptions.unknown_direction_error import (
    UnknownDirectionError,
)


class Direction(Enum):
    UP = ("A01", "Up")
    DOWN = ("A02", "Down")
    SYMMETRIC = ("A03", "Symmetric")

    def __init__(self, code: str, description: str) -> None:
        self.code = code
        self.description = description

    @classmethod
    def from_code(cls, code: str) -> Self:
        for member in cls:
            if member.code == code:
                return member
        raise UnknownDirectionError(code)
