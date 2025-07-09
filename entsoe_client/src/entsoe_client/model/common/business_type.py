from enum import Enum
from typing import Self

from src.entsoe_client.exceptions.unknown_business_type_error import (
    UnknownBusinessTypeError,
)


class BusinessType(Enum):
    PRODUCTION = ("A01", "Production")
    CONSUMPTION = ("A04", "Consumption")
    AGGREGATED_ENERGY_DATA = ("A14", "Aggregated energy data")
    BALANCE_ENERGY_DEVIATION = ("A19", "Balance energy deviation")
    GENERAL_CAPACITY_INFORMATION = ("A25", "General Capacity Information")
    ALREADY_ALLOCATED_CAPACITY = ("A29", "Already allocated capacity (AAC)")
    INSTALLED_GENERATION = ("A37", "Installed generation")
    REQUESTED_CAPACITY = ("A43", "Requested capacity (without price)")
    SYSTEM_OPERATOR_REDISPATCHING = ("A46", "System Operator redispatching")
    PLANNED_MAINTENANCE = ("A53", "Planned maintenance")
    UNPLANNED_OUTAGE = ("A54", "Unplanned outage")
    MINIMUM_POSSIBLE = ("A60", "Minimum possible")
    MAXIMUM_POSSIBLE = ("A61", "Maximum possible")
    INTERNAL_REDISPATCH = ("A85", "Internal redispatch")
    POSITIVE_FORECAST_MARGIN = (
        "A91",
        "Positive forecast margin (if installed capacity > load forecast)",
    )
    NEGATIVE_FORECAST_MARGIN = (
        "A92",
        "Negative forecast margin (if load forecast > installed capacity)",
    )
    WIND_GENERATION = ("A93", "Wind generation")
    SOLAR_GENERATION = ("A94", "Solar generation")
    FREQUENCY_CONTAINMENT_RESERVE = ("A95", "Frequency containment reserve")
    AUTOMATIC_FREQUENCY_RESTORATION_RESERVE = (
        "A96",
        "Automatic frequency restoration reserve",
    )
    MANUAL_FREQUENCY_RESTORATION_RESERVE = (
        "A97",
        "Manual frequency restoration reserve",
    )
    REPLACEMENT_RESERVE = ("A98", "Replacement reserve")
    INTERCONNECTOR_NETWORK_EVOLUTION = ("B01", "Interconnector network evolution")
    INTERCONNECTOR_NETWORK_DISMANTLING = ("B02", "Interconnector network dismantling")
    COUNTER_TRADE = ("B03", "Counter trade")
    CONGESTION_COSTS = ("B04", "Congestion costs")
    CAPACITY_ALLOCATED = ("B05", "Capacity allocated (including price)")
    AUCTION_REVENUE = ("B07", "Auction revenue")
    TOTAL_NOMINATED_CAPACITY = ("B08", "Total nominated capacity")
    NET_POSITION = ("B09", "Net position")
    CONGESTION_INCOME = ("B10", "Congestion income")
    PRODUCTION_UNIT = ("B11", "Production unit")
    AREA_CONTROL_ERROR = ("B33", "Area Control Error")
    OFFER = ("B74", "Offer")
    NEED = ("B75", "Need")
    PROCURED_CAPACITY = ("B95", "Procured capacity")
    SHARED_BALANCING_RESERVE_CAPACITY = ("C22", "Shared Balancing Reserve Capacity")
    SHARE_OF_RESERVE_CAPACITY = ("C23", "Share of reserve capacity")
    ACTUAL_RESERVE_CAPACITY = ("C24", "Actual reserve capacity")

    def __init__(self, code: str, description: str) -> None:
        self.code = code
        self.description = description

    @classmethod
    def from_code(cls, code: str) -> Self:
        for member in cls:
            if member.code == code:
                return member
        raise UnknownBusinessTypeError(code)
