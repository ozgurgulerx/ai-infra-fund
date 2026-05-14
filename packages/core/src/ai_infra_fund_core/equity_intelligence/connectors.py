from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ai_infra_fund_core.contracts.common import normalize_tuple, require_aware_datetime, require_text

from .urls import canonicalize_url


@dataclass(frozen=True, slots=True)
class ConnectorFetchResult:
    canonical_url: str
    status_code: int
    fetched_at: datetime
    content: str
    content_hash: str
    discovered_urls: tuple[str, ...] = ()
    etag: str | None = None
    last_modified: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_url", canonicalize_url(self.canonical_url).canonical_url)
        if self.status_code < 100 or self.status_code > 599:
            raise ValueError("status_code must be an HTTP status code")
        require_aware_datetime(self.fetched_at, "fetched_at")
        object.__setattr__(self, "content", require_text(self.content, "content"))
        object.__setattr__(self, "content_hash", require_text(self.content_hash, "content_hash"))
        object.__setattr__(
            self,
            "discovered_urls",
            tuple(canonicalize_url(str(url)).canonical_url for url in normalize_tuple(self.discovered_urls, "discovered_urls")),
        )


class SourceConnector(Protocol):
    connector_id: str

    def fetch(self, url: str) -> ConnectorFetchResult:
        """Return a deterministic fetch result for a canonicalized public URL."""


@dataclass(frozen=True, slots=True)
class StubSourceConnector:
    connector_id: str
    results: dict[str, ConnectorFetchResult]

    def __post_init__(self) -> None:
        object.__setattr__(self, "connector_id", require_text(self.connector_id, "connector_id").strip())
        object.__setattr__(
            self,
            "results",
            {canonicalize_url(url).canonical_url: result for url, result in self.results.items()},
        )

    def fetch(self, url: str) -> ConnectorFetchResult:
        canonical = canonicalize_url(url).canonical_url
        try:
            return self.results[canonical]
        except KeyError as exc:
            raise KeyError(f"no stub result registered for {canonical}") from exc
