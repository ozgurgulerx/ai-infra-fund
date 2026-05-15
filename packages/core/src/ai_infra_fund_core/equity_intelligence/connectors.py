from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from ai_infra_fund_core.contracts.common import (
    normalize_tuple,
    require_aware_datetime,
    require_text,
)

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
        object.__setattr__(
            self, "canonical_url", canonicalize_url(self.canonical_url).canonical_url
        )
        if self.status_code < 100 or self.status_code > 599:
            raise ValueError("status_code must be an HTTP status code")
        require_aware_datetime(self.fetched_at, "fetched_at")
        object.__setattr__(self, "content", require_text(self.content, "content"))
        object.__setattr__(
            self, "content_hash", require_text(self.content_hash, "content_hash")
        )
        object.__setattr__(
            self,
            "discovered_urls",
            tuple(
                canonicalize_url(str(url)).canonical_url
                for url in normalize_tuple(self.discovered_urls, "discovered_urls")
            ),
        )


class SourceConnector(Protocol):
    connector_id: str

    def fetch(self, url: str) -> ConnectorFetchResult:
        """Return a deterministic fetch result for a canonicalized public URL."""


class NewsRssPublicWebConnector(SourceConnector, Protocol):
    """Connector contract for public news, RSS, and web evidence."""


class SecFilingConnector(SourceConnector, Protocol):
    """Connector contract for SEC or filing-import evidence."""


class CompanyIrPressConnector(SourceConnector, Protocol):
    """Connector contract for company IR and press-release evidence."""


@dataclass(frozen=True, slots=True)
class MarketPriceSnapshot:
    ticker: str
    as_of: datetime
    close_price: Decimal
    volume: int
    source: str
    content_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        require_aware_datetime(self.as_of, "as_of")
        if self.close_price <= 0:
            raise ValueError("close_price must be positive")
        if self.volume < 0:
            raise ValueError("volume must be non-negative")
        object.__setattr__(self, "source", require_text(self.source, "source").strip())
        object.__setattr__(
            self,
            "content_hash",
            require_text(self.content_hash, "content_hash").strip(),
        )


class MarketPriceSnapshotConnector(Protocol):
    connector_id: str

    def fetch_snapshot(self, ticker: str) -> MarketPriceSnapshot:
        """Return a deterministic point-in-time market snapshot for a ticker."""


class ManualLocalFileConnector(Protocol):
    connector_id: str

    def fetch_file(self, path: str | Path) -> ConnectorFetchResult:
        """Return a deterministic local/manual evidence file capture."""


@dataclass(frozen=True, slots=True)
class MacroSeriesObservation:
    series_id: str
    as_of: datetime
    value: Decimal | None
    unit: str
    vintage_id: str
    source: str
    content_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "series_id", require_text(self.series_id, "series_id").strip()
        )
        require_aware_datetime(self.as_of, "as_of")
        object.__setattr__(self, "unit", require_text(self.unit, "unit").strip())
        object.__setattr__(
            self, "vintage_id", require_text(self.vintage_id, "vintage_id").strip()
        )
        object.__setattr__(self, "source", require_text(self.source, "source").strip())
        object.__setattr__(
            self,
            "content_hash",
            require_text(self.content_hash, "content_hash").strip(),
        )


class MacroSeriesConnector(Protocol):
    connector_id: str

    def fetch_series(
        self, series_id: str, *, since: datetime | None
    ) -> tuple[MacroSeriesObservation, ...]:
        """Return a deterministic series of observations for a macro series id."""


@dataclass(frozen=True, slots=True)
class StubSourceConnector:
    connector_id: str
    results: dict[str, ConnectorFetchResult]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "connector_id",
            require_text(self.connector_id, "connector_id").strip(),
        )
        object.__setattr__(
            self,
            "results",
            {
                canonicalize_url(url).canonical_url: result
                for url, result in self.results.items()
            },
        )

    def fetch(self, url: str) -> ConnectorFetchResult:
        canonical = canonicalize_url(url).canonical_url
        try:
            return self.results[canonical]
        except KeyError as exc:
            raise KeyError(f"no stub result registered for {canonical}") from exc


class StubNewsRssPublicWebConnector(StubSourceConnector):
    """Deterministic fixture connector for public news/RSS/web sources."""


class StubSecFilingConnector(StubSourceConnector):
    """Deterministic fixture connector for SEC/filing-import sources."""


class StubCompanyIrPressConnector(StubSourceConnector):
    """Deterministic fixture connector for company IR and press releases."""


@dataclass(frozen=True, slots=True)
class StubMarketPriceSnapshotConnector:
    connector_id: str
    snapshots: dict[str, MarketPriceSnapshot]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "connector_id",
            require_text(self.connector_id, "connector_id").strip(),
        )
        object.__setattr__(
            self,
            "snapshots",
            {ticker.upper(): snapshot for ticker, snapshot in self.snapshots.items()},
        )

    def fetch_snapshot(self, ticker: str) -> MarketPriceSnapshot:
        normalized = require_text(ticker, "ticker").upper()
        try:
            return self.snapshots[normalized]
        except KeyError as exc:
            raise KeyError(
                f"no stub market snapshot registered for {normalized}"
            ) from exc


@dataclass(frozen=True, slots=True)
class StubManualLocalFileConnector:
    connector_id: str
    results: dict[str, ConnectorFetchResult]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "connector_id",
            require_text(self.connector_id, "connector_id").strip(),
        )
        object.__setattr__(
            self,
            "results",
            {str(Path(path)): result for path, result in self.results.items()},
        )

    def fetch_file(self, path: str | Path) -> ConnectorFetchResult:
        normalized = str(Path(path))
        try:
            return self.results[normalized]
        except KeyError as exc:
            raise KeyError(
                f"no stub local file result registered for {normalized}"
            ) from exc


@dataclass(frozen=True, slots=True)
class StubMacroSeriesConnector:
    connector_id: str
    observations: dict[str, tuple[MacroSeriesObservation, ...]]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "connector_id",
            require_text(self.connector_id, "connector_id").strip(),
        )
        object.__setattr__(
            self,
            "observations",
            {
                require_text(series_id, "series_id").strip(): tuple(values)
                for series_id, values in self.observations.items()
            },
        )

    def fetch_series(
        self, series_id: str, *, since: datetime | None
    ) -> tuple[MacroSeriesObservation, ...]:
        normalized = require_text(series_id, "series_id").strip()
        try:
            values = self.observations[normalized]
        except KeyError as exc:
            raise KeyError(f"no stub macro series registered for {normalized}") from exc
        if since is None:
            return values
        require_aware_datetime(since, "since")
        return tuple(obs for obs in values if obs.as_of >= since)


@dataclass(frozen=True, slots=True)
class FutureProviderHook:
    provider_id: str
    connector_kind: str
    capabilities: tuple[str, ...]
    requires_secret: bool = True
    enabled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "provider_id", require_text(self.provider_id, "provider_id").strip()
        )
        object.__setattr__(
            self,
            "connector_kind",
            require_text(self.connector_kind, "connector_kind").strip(),
        )
        capabilities = tuple(
            require_text(str(capability), "capability").strip()
            for capability in normalize_tuple(self.capabilities, "capabilities")
        )
        if not capabilities:
            raise ValueError("capabilities must not be empty")
        object.__setattr__(self, "capabilities", capabilities)
