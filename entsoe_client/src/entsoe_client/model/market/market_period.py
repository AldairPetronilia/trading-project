"""Market period model for ENTSO-E Publication Market Documents."""

from pydantic_xml import BaseXmlModel, element

from .market_point import MarketPoint
from .market_time_interval import MarketTimeInterval


class MarketPeriod(BaseXmlModel):  # Namespace-agnostic model
    """Period model for market documents."""

    class Config:
        tag = "Period"

    timeInterval: MarketTimeInterval = element(tag="timeInterval")
    resolution: str = element(tag="resolution")
    # Fix: Use proper element mapping for list of Point elements
    points: list[MarketPoint] = element(tag="Point", default=[])
