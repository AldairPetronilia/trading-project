"""XML namespace utilities for ENTSO-E document parsing.

This module provides utilities to strip XML namespaces from ENTSO-E documents,
enabling namespace-agnostic parsing of Publication Market Documents.
"""

import xml.etree.ElementTree as ET


def remove_xml_namespaces(xml_content: str) -> str:
    """
    Remove all XML namespace declarations and prefixes from XML content.

    This enables namespace-agnostic parsing by stripping namespace information
    while preserving the XML structure and data.

    Args:
        xml_content: Raw XML string with namespace declarations

    Returns:
        XML string with all namespace information removed

    Raises:
        ValueError: If XML content cannot be parsed

    Note:
        This function uses xml.etree.ElementTree to parse trusted XML content
        from ENTSO-E API responses. For untrusted XML, consider using defusedxml.
    """
    try:
        # Parse the XML string - safe for trusted ENTSO-E API responses
        root = ET.fromstring(xml_content)  # noqa: S314

        # Remove namespaces from all elements recursively
        for element in root.iter():
            # Remove namespace from tag name (format: {namespace}tag -> tag)
            if "}" in element.tag:
                element.tag = element.tag.split("}")[-1]

        # Convert back to string without XML declaration
        return ET.tostring(root, encoding="unicode")

    except ET.ParseError as e:
        error_msg = f"Failed to parse XML content: {e}"
        raise ValueError(error_msg) from e
