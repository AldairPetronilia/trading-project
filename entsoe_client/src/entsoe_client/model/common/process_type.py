from enum import Enum
from typing import Any, Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema
from src.entsoe_client.exceptions.unknown_process_type_error import (
    UnknownProcessTypeError,
)


class ProcessType(Enum):
    DAY_AHEAD = ("A01", "Day ahead")
    INTRA_DAY_INCREMENTAL = ("A02", "Intra day incremental")
    REALISED = ("A16", "Realised")
    INTRADAY_TOTAL = ("A18", "Intraday total")
    WEEK_AHEAD = ("A31", "Week ahead")
    MONTH_AHEAD = ("A32", "Month ahead")
    YEAR_AHEAD = ("A33", "Year ahead")
    SYNCHRONISATION_PROCESS = ("A39", "Synchronisation process")
    INTRADAY_PROCESS = ("A40", "Intraday process")
    REPLACEMENT_RESERVE = ("A46", "Replacement reserve")
    MANUAL_FREQUENCY_RESTORATION_RESERVE = (
        "A47",
        "Manual frequency restoration reserve",
    )
    AUTOMATIC_FREQUENCY_RESTORATION_RESERVE = (
        "A51",
        "Automatic frequency restoration reserve",
    )
    FREQUENCY_CONTAINMENT_RESERVE = ("A52", "Frequency containment reserve")
    FREQUENCY_RESTORATION_RESERVE = ("A56", "Frequency restoration reserve")
    SCHEDULED_ACTIVATION_MFRR = ("A60", "Scheduled activation mFRR")
    DIRECT_ACTIVATION_MFRR = ("A61", "Direct activation mFRR")
    CENTRAL_SELECTION_AFRR = ("A67", "Central Selection aFRR")
    LOCAL_SELECTION_AFRR = ("A68", "Local Selection aFRR")

    def __init__(self, code: str, description: str) -> None:
        self.code = code
        self.description = description

    @classmethod
    def from_code(cls, code: str) -> Self:
        for member in cls:
            if member.code == code:
                return member
        raise UnknownProcessTypeError(code)

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
