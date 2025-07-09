from enum import Enum


class AreaType(Enum):
    BZN = "Bidding Zone"
    BZA = "Bidding Zone Aggregation"
    CTA = "Control Area"
    MBA = "Market Balance Area"
    IBA = "Imbalance Area"
    IPA = "Imbalance Price Area"
    LFA = "Load Frequency Control Area"
    LFB = "Load Frequency Control Block"
    REG = "Region"
    SCA = "Scheduling Area"
    SNA = "Synchronous Area"

    def __init__(self, description: str) -> None:
        self.description = description
