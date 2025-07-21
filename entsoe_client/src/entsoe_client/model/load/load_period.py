from pydantic_xml import BaseXmlModel, element

from entsoe_client.model import ENTSOE_LOAD_NSMAP
from entsoe_client.model.load.load_point import LoadPoint
from entsoe_client.model.load.load_time_interval import LoadTimeInterval


class LoadPeriod(BaseXmlModel, tag="Period", nsmap=ENTSOE_LOAD_NSMAP):  # type: ignore[call-arg]
    timeInterval: LoadTimeInterval = element(tag="timeInterval")
    resolution: str = element(tag="resolution")
    points: list[LoadPoint]
