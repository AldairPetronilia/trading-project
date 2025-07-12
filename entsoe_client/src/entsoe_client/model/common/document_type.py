from enum import Enum
from typing import Self

from entsoe_client.exceptions.unknown_document_type_error import (
    UnknownDocumentTypeError,
)


class DocumentType(Enum):
    FINALISED_SCHEDULE = ("A09", "Finalised schedule")
    AGGREGATED_ENERGY_DATA_REPORT = ("A11", "Aggregated energy data report")
    ACQUIRING_SYSTEM_OPERATOR_RESERVE_SCHEDULE = (
        "A15",
        "Acquiring system operator reserve schedule",
    )
    BID_DOCUMENT = ("A24", "Bid document")
    ALLOCATION_RESULT_DOCUMENT = ("A25", "Allocation result document")
    CAPACITY_DOCUMENT = ("A26", "Capacity document")
    AGREED_CAPACITY = ("A31", "Agreed capacity")
    RESERVE_BID_DOCUMENT = ("A37", "Reserve bid document")
    RESERVE_ALLOCATION_RESULT_DOCUMENT = ("A38", "Reserve allocation result document")
    PRICE_DOCUMENT = ("A44", "Price Document")
    ESTIMATED_NET_TRANSFER_CAPACITY = ("A61", "Estimated Net Transfer Capacity")
    REDISPATCH_NOTICE = ("A63", "Redispatch notice")
    SYSTEM_TOTAL_LOAD = ("A65", "System total load")
    INSTALLED_GENERATION_PER_TYPE = ("A68", "Installed generation per type")
    WIND_AND_SOLAR_FORECAST = ("A69", "Wind and solar forecast")
    LOAD_FORECAST_MARGIN = ("A70", "Load forecast margin")
    GENERATION_FORECAST = ("A71", "Generation forecast")
    RESERVOIR_FILLING_INFORMATION = ("A72", "Reservoir filling information")
    ACTUAL_GENERATION = ("A73", "Actual generation")
    WIND_AND_SOLAR_GENERATION = ("A74", "Wind and solar generation")
    ACTUAL_GENERATION_PER_TYPE = ("A75", "Actual generation per type")
    LOAD_UNAVAILABILITY = ("A76", "Load unavailability")
    PRODUCTION_UNAVAILABILITY = ("A77", "Production unavailability")
    TRANSMISSION_UNAVAILABILITY = ("A78", "Transmission unavailability")
    OFFSHORE_GRID_INFRASTRUCTURE_UNAVAILABILITY = (
        "A79",
        "Offshore grid infrastructure unavailability",
    )
    GENERATION_UNAVAILABILITY = ("A80", "Generation unavailability")
    CONTRACTED_RESERVES = ("A81", "Contracted reserves")
    ACCEPTED_OFFERS = ("A82", "Accepted offers")
    ACTIVATED_BALANCING_QUANTITIES = ("A83", "Activated balancing quantities")
    ACTIVATED_BALANCING_PRICES = ("A84", "Activated balancing prices")
    IMBALANCE_PRICES = ("A85", "Imbalance prices")
    IMBALANCE_VOLUME = ("A86", "Imbalance volume")
    FINANCIAL_SITUATION = ("A87", "Financial situation")
    CROSS_BORDER_BALANCING = ("A88", "Cross border balancing")
    CONTRACTED_RESERVE_PRICES = ("A89", "Contracted reserve prices")
    INTERCONNECTION_NETWORK_EXPANSION = ("A90", "Interconnection network expansion")
    COUNTER_TRADE_NOTICE = ("A91", "Counter trade notice")
    CONGESTION_COSTS = ("A92", "Congestion costs")
    DC_LINK_CAPACITY = ("A93", "DC link capacity")
    NON_EU_ALLOCATIONS = ("A94", "Non EU allocations")
    CONFIGURATION_DOCUMENT = ("A95", "Configuration document")
    FLOW_BASED_ALLOCATIONS = ("B11", "Flow-based allocations")
    AGGREGATED_NETTED_EXTERNAL_TSO_SCHEDULE_DOCUMENT = (
        "B17",
        "Aggregated netted external TSO schedule document",
    )
    BID_AVAILABILITY_DOCUMENT = ("B45", "Bid Availability Document")

    def __init__(self, code: str, description: str) -> None:
        self.code = code
        self.description = description

    @classmethod
    def from_code(cls, code: str) -> Self:
        for member in cls:
            if member.code == code:
                return member
        raise UnknownDocumentTypeError(code)
