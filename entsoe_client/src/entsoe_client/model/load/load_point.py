from typing import Union

from pydantic_xml import BaseXmlModel, element

from entsoe_client.model import ENTSOE_NSMAP


class LoadPoint(BaseXmlModel, tag="Point", nsmap=ENTSOE_NSMAP):  # type: ignore[call-arg]
    position: int | None = element(tag="position")
    quantity: float | None = element(tag="quantity")
