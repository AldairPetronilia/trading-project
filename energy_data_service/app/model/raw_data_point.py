from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.model.data_quality import DataQuality
from app.model.data_type import DataType
from app.model.market_code import MarketCode


@dataclass(frozen=True)
class RawDataPoint:
    """Standardized container for raw data from any source"""

    timestamp: datetime
    value: Decimal
    unit: str
    source: str
    market: MarketCode
    data_type: DataType
    quality: DataQuality = DataQuality.HIGH
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_price_data(self) -> bool:
        """Check if this data point represents price information"""
        price_types = {
            DataType.SPOT_PRICE,
            DataType.DAY_AHEAD_PRICE,
            DataType.INTRADAY_PRICE,
            DataType.FUTURES_PRICE,
        }
        return self.data_type in price_types
