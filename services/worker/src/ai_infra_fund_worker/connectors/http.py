from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status_code: int
    content: str
    headers: dict[str, str] = field(default_factory=dict)


class HttpFetcher(Protocol):
    """Minimal HTTP GET interface used by all worker connectors.

    Production code injects an httpx-backed adapter; tests inject a
    recorded-response stub. Keeps the connectors I/O-pure for unit
    testing.
    """

    def get(self, url: str, *, headers: dict[str, str]) -> HttpResponse: ...


__all__ = ["HttpFetcher", "HttpResponse"]
