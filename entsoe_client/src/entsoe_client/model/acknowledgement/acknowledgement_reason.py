from pydantic_xml import BaseXmlModel, element

from . import ENTSOE_ACKNOWLEDGEMENT_NSMAP


class AcknowledgementReason(
    BaseXmlModel,
    tag="Reason",
    nsmap=ENTSOE_ACKNOWLEDGEMENT_NSMAP,  # type: ignore[call-arg]
):
    """Reason element in acknowledgement documents."""

    code: str = element(tag="code")
    text: str = element(tag="text")
