from dataclasses import dataclass
from typing import Optional


@dataclass
class MarketParticipantMRID:
    value: str
    coding_scheme: str | None = None
