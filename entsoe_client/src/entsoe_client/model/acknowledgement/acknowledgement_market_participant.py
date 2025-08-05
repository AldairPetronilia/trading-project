from pydantic_xml import BaseXmlModel, attr

from . import ENTSOE_ACKNOWLEDGEMENT_NSMAP


class AcknowledgementMarketParticipant(
    BaseXmlModel,
    nsmap=ENTSOE_ACKNOWLEDGEMENT_NSMAP,  # type: ignore[call-arg]
):
    """Market participant MRID element in acknowledgement documents."""

    mRID: str
    codingScheme: str | None = attr(name="codingScheme")
