class EntsoEClientError(Exception):
    """Exception raised by EntsoE client operations."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause

    def __str__(self) -> str:
        if self.cause:
            return f"{super().__str__()} (caused by {self.cause})"
        return super().__str__()

    @classmethod
    def http_request_failed(cls, cause: Exception) -> "EntsoEClientError":
        """Create error for HTTP request failure."""
        msg = "Failed to fetch load data"
        return cls(msg, cause)

    @classmethod
    def xml_parsing_failed(cls, cause: Exception) -> "EntsoEClientError":
        """Create error for XML parsing failure."""
        msg = "Failed to parse XML response"
        return cls(msg, cause)
