from enum import Enum
from typing import Any, Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema
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

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        from_code_validator = core_schema.no_info_plain_validator_function(
            cls.from_code,
        )

        return core_schema.json_or_python_schema(
            json_schema=from_code_validator,
            # For creating models from Python, we can be more flexible:
            # allow passing an existing AreaCode instance OR a string to be parsed.
            python_schema=core_schema.union_schema(
                [core_schema.is_instance_schema(cls), from_code_validator],
            ),
            # For serialization (e.g., model_dump), define the 'marshal' logic.
            # We take an AreaCode instance and return its .code attribute.
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: v.code,
            ),
        )
