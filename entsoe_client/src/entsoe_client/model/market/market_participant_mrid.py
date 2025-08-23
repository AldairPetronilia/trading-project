"""Market participant MRID model for ENTSO-E market documents."""

from pydantic_xml import BaseXmlModel, attr

from .market_time_interval import ENTSOE_MARKET_NSMAP


class MarketParticipantMRID(BaseXmlModel, nsmap=ENTSOE_MARKET_NSMAP):  # type: ignore[call-arg]
    """Market participant MRID for market documents."""

    value: str
    coding_scheme: str | None = attr(name="codingScheme")
