"""Market point model for ENTSO-E Publication Market Documents."""

from pydantic_xml import BaseXmlModel, element

from .market_time_interval import ENTSOE_MARKET_NSMAP


class MarketPoint(BaseXmlModel, tag="Point", nsmap=ENTSOE_MARKET_NSMAP):  # type: ignore[call-arg]
    """Point model for market documents with price and quantity information."""

    position: int | None = element(tag="position", default=None)
    price_amount: float | None = element(tag="price.amount", default=None)
    quantity: float | None = element(tag="quantity", default=None)
