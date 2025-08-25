"""Market participant MRID model for ENTSO-E market documents."""

from pydantic_xml import BaseXmlModel, attr


class MarketParticipantMRID(BaseXmlModel):  # Namespace-agnostic model
    """Market participant MRID for market documents."""

    value: str
    coding_scheme: str | None = attr(name="codingScheme")
