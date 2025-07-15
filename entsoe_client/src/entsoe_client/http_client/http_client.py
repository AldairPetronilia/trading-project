from abc import ABC, abstractmethod
from typing import Any

from pydantic import HttpUrl


class HttpClient(ABC):
    """HTTP client interface for EntsoE API requests."""

    @abstractmethod
    async def get(self, url: HttpUrl, params: dict[str, Any] | None = None) -> str:
        """Perform a GET request to the specified URL with optional parameters."""

    @abstractmethod
    async def close(self) -> None:
        """Close the HTTP client connection."""
