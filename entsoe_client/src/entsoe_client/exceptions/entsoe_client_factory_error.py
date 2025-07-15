class EntsoEClientFactoryError(ValueError):
    """Exception raised by EntsoEClientFactory operations."""

    def __init__(self, message: str) -> None:
        super().__init__(message)

    @classmethod
    def api_token_empty(cls) -> "EntsoEClientFactoryError":
        """Create error for empty API token."""
        msg = "API token cannot be null or empty"
        return cls(msg)
