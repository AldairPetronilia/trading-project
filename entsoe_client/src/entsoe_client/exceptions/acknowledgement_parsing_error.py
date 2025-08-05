class AcknowledgementParsingError(Exception):
    """Exception raised when parsing ENTSO-E Acknowledgement_MarketDocument fails."""

    def __init__(self, message: str, xml_content: str | None = None):
        super().__init__(message)
        self.xml_content = xml_content

    @classmethod
    def invalid_xml_structure(
        cls, reason: str, xml_content: str | None = None
    ) -> "AcknowledgementParsingError":
        return cls(f"Invalid acknowledgement XML structure: {reason}", xml_content)

    @classmethod
    def missing_required_field(
        cls, field_name: str, xml_content: str | None = None
    ) -> "AcknowledgementParsingError":
        return cls(
            f"Required field '{field_name}' not found in acknowledgement document",
            xml_content,
        )

    @classmethod
    def invalid_datetime_format(
        cls, field_name: str, datetime_value: str, xml_content: str | None = None
    ) -> "AcknowledgementParsingError":
        return cls(
            f"Invalid datetime format in field '{field_name}': {datetime_value}",
            xml_content,
        )

    @classmethod
    def invalid_reason_structure(
        cls, xml_content: str | None = None
    ) -> "AcknowledgementParsingError":
        return cls(
            "Acknowledgement document missing or invalid Reason element", xml_content
        )
