import re
from enum import Enum
from typing import Final, NoReturn

from entsoe_client.exceptions.entsoe_api_request_error import EntsoEApiRequestError


class XmlDocumentType(Enum):
    """Supported ENTSO-E XML document types."""

    GL_MARKET_DOCUMENT = "GL_MarketDocument"
    PUBLICATION_MARKET_DOCUMENT = "Publication_MarketDocument"
    ACKNOWLEDGEMENT_MARKET_DOCUMENT = "Acknowledgement_MarketDocument"


class XmlDocumentDetector:
    """Detects the type of XML document from ENTSO-E API responses.

    This detector performs fast root element detection without parsing the
    entire XML document, providing efficient document type classification
    for routing to appropriate parsers.
    """

    # Regex pattern to extract root element name from XML
    # Captures full element name including namespace prefix (e.g., ns:ElementName)
    ROOT_ELEMENT_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"<\s*([a-zA-Z_][a-zA-Z0-9_.-]*(?::[a-zA-Z_][a-zA-Z0-9_.-]*)?)[\s>]",
        re.MULTILINE | re.DOTALL,
    )

    @classmethod
    def detect_document_type(cls, xml_content: str) -> XmlDocumentType:
        """Detect XML document type from root element.

        Args:
            xml_content: Raw XML content from ENTSO-E API response

        Returns:
            XmlDocumentType enum value for the detected document type

        Raises:
            EntsoEApiRequestError: If document type cannot be detected or is unsupported
        """

        def _raise_invalid_xml_content() -> NoReturn:
            msg = "No XML root element found"
            raise EntsoEApiRequestError.invalid_xml_content(msg)

        def _raise_unsupported_document_type(root_element: str) -> NoReturn:
            raise EntsoEApiRequestError.unsupported_document_type(root_element)

        if not xml_content or not isinstance(xml_content, str):
            msg = "XML content is empty or invalid"
            raise EntsoEApiRequestError.invalid_xml_content(msg)

        try:
            # Find the first XML element (root element)
            match = cls.ROOT_ELEMENT_PATTERN.search(xml_content.strip())

            if not match:
                _raise_invalid_xml_content()

            root_element = match.group(1)

            # Map root element to document type (only exact matches, no namespace prefixes)
            if root_element == "GL_MarketDocument":
                return XmlDocumentType.GL_MARKET_DOCUMENT
            if root_element == "Publication_MarketDocument":
                return XmlDocumentType.PUBLICATION_MARKET_DOCUMENT
            if root_element == "Acknowledgement_MarketDocument":
                return XmlDocumentType.ACKNOWLEDGEMENT_MARKET_DOCUMENT

            # Handle namespaced elements or unknown elements
            _raise_unsupported_document_type(root_element)

        except EntsoEApiRequestError:
            # Re-raise our specific exceptions
            raise
        except Exception as e:
            raise EntsoEApiRequestError.document_type_detection_failed(str(e)) from e
