from pydantic_xml import BaseXmlModel, attr

from entsoe_client.model import ENTSOE_NSMAP


class MarketParticipantMRID(BaseXmlModel, nsmap=ENTSOE_NSMAP):  # type: ignore[call-arg]
    value: str
    coding_scheme: str | None = attr(name="codingScheme")
