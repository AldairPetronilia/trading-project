from entsoe_client.model.common.area_code import AreaCode
from entsoe_client.model.common.area_type import AreaType


class EntsoEApiRequestError(Exception):
    def __init__(
        self,
        message: str,
        area_code: AreaCode | None = None,
        required_type: AreaType | None = None,
        parameter_name: str | None = None,
    ):
        super().__init__(message)
        self.area_code = area_code
        self.required_type = required_type
        self.parameter_name = parameter_name

    @classmethod
    def invalid_area_type(
        cls,
        area_code: AreaCode,
        required_type: AreaType,
        parameter_name: str,
    ) -> "EntsoEApiRequestError":
        message = (
            f"Area {area_code.description} ({area_code.code}) "
            f"does not support {required_type.description}. "
            f"Supported types: {area_code.get_area_types_list}"
        )
        return cls(message, area_code, required_type, parameter_name)

    @classmethod
    def required_field_missing(cls, field_name: str) -> "EntsoEApiRequestError":
        return cls(f"{field_name} is required")

    @classmethod
    def invalid_xml_content(cls, reason: str) -> "EntsoEApiRequestError":
        return cls(f"Invalid XML content: {reason}")

    @classmethod
    def unsupported_document_type(cls, document_type: str) -> "EntsoEApiRequestError":
        return cls(f"Unsupported XML document type: {document_type}")

    @classmethod
    def document_type_detection_failed(cls, reason: str) -> "EntsoEApiRequestError":
        return cls(f"Failed to detect XML document type: {reason}")
