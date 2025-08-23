"""Market period model for ENTSO-E Publication Market Documents."""

from pydantic_xml import BaseXmlModel, element

from .market_point import MarketPoint
from .market_time_interval import ENTSOE_MARKET_NSMAP, MarketTimeInterval


class MarketPeriod(BaseXmlModel, tag="Period", nsmap=ENTSOE_MARKET_NSMAP):  # type: ignore[call-arg]
    """Period model for market documents."""

    timeInterval: MarketTimeInterval = element(tag="timeInterval")
    resolution: str = element(tag="resolution")
    points: list[MarketPoint]
