from dataclasses import dataclass
from typing import Optional

from src.entsoe_client.model.common.area_code import AreaCode


@dataclass
class DomainMRID:
    area_code: AreaCode
    coding_scheme: str | None = None
