from enum import Enum
from typing import Self

from entsoe_client.exceptions.unknown_process_type_error import (
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
