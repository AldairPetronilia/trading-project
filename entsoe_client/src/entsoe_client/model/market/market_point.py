"""Market point model for ENTSO-E Publication Market Documents."""

from pydantic_xml import BaseXmlModel, element


class MarketPoint(BaseXmlModel):  # Namespace-agnostic model
    """Point model for market documents with price and quantity information."""

    class Config:
        tag = "Point"

    position: int | None = element(tag="position", default=None)
    price_amount: float | None = element(tag="price.amount", default=None)
    quantity: float | None = element(tag="quantity", default=None)
