from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.area_type import AreaType


class EntsoEApiRequestError(Exception):
    def __init__(
        self,
        area_code: AreaCode | None,
        required_type: AreaType,
        parameter_name: str,
    ):
        super().__init__(
            f"Area {area_code}' "
            f"does not support {required_type}. "
            f"Supported types: {area_code}",
        )
        self.area_code = AreaCode
        self.required_type = required_type
        self.parameter_name = parameter_name
