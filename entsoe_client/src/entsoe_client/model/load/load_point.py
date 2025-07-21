from pydantic_xml import BaseXmlModel, element

from entsoe_client.model import ENTSOE_LOAD_NSMAP


class LoadPoint(BaseXmlModel, tag="Point", nsmap=ENTSOE_LOAD_NSMAP):  # type: ignore[call-arg]
    position: int | None = element(tag="position")
    quantity: float | None = element(tag="quantity")
