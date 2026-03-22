from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class AuthStrategy(ABC):
    """Base class for authentication strategies.

    Each strategy modifies the *request_kwargs* dict that will be forwarded
    to :pymod:`httpx` (e.g. adding headers or query parameters).
    """

    @abstractmethod
    def apply(self, request_kwargs: dict) -> dict:
        """Return a **new or mutated** copy of *request_kwargs* with auth applied."""
        ...


@dataclass(frozen=True)
class NoAuth(AuthStrategy):
    """Pass-through – no authentication added."""

    def apply(self, request_kwargs: dict) -> dict:
        return request_kwargs


@dataclass(frozen=True)
class ApiKeyAuth(AuthStrategy):
    """Inject an API key as a header *or* query parameter.

    Parameters
    ----------
    key:
        The API-key value.
    param_name:
        Name of the header or query parameter (e.g. ``"X-Api-Key"``).
    location:
        ``"header"`` (default) or ``"query"``.
    """

    key: str
    param_name: str = "X-Api-Key"
    location: str = "header"  # "header" | "query"

    def apply(self, request_kwargs: dict) -> dict:
        if self.location == "query":
            params: dict = dict(request_kwargs.get("params") or {})
            params[self.param_name] = self.key
            request_kwargs["params"] = params
        else:
            headers: dict = dict(request_kwargs.get("headers") or {})
            headers[self.param_name] = self.key
            request_kwargs["headers"] = headers
        return request_kwargs


@dataclass(frozen=True)
class BearerTokenAuth(AuthStrategy):
    """Add an ``Authorization: Bearer <token>`` header."""

    token: str

    def apply(self, request_kwargs: dict) -> dict:
        headers: dict = dict(request_kwargs.get("headers") or {})
        headers["Authorization"] = f"Bearer {self.token}"
        request_kwargs["headers"] = headers
        return request_kwargs
