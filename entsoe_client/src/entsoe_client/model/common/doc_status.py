from enum import Enum
from typing import Self

from entsoe_client.exceptions.unknown_doc_status_error import (
    UnknownDocStatusError,
)


class DocStatus(Enum):
    INTERMEDIATE = ("A01", "Intermediate")
    FINAL = ("A02", "Final")
    ACTIVE = ("A05", "Active")
    CANCELLED = ("A09", "Cancelled")
    WITHDRAWN = ("A13", "Withdrawn")
    ESTIMATED = ("X01", "Estimated")

    def __init__(self, code: str, description: str) -> None:
        self.code = code
        self.description = description

    @classmethod
    def from_code(cls, code: str) -> Self:
        for member in cls:
            if member.code == code:
                return member
        raise UnknownDocStatusError(code)
