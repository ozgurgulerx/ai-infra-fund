from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ai_infra_fund_core.contracts.common import require_aware_datetime
from ai_infra_fund_core.local_inputs.watchlist import AIEquityWatchlist

from .source_registry import SourceRegistry, RegistrySource
from .urls import canonicalize_url


PRIORITY_SCORES: dict[str, int] = {"critical": 100, "high": 75, "medium": 50, "low": 25}


@dataclass(frozen=True, slots=True)
class WatchedEquityRecord:
    ticker: str
    company_name: str
    exchange: str | None
    asset_type: str
    active: bool
    priority: int
    tags: tuple[str, ...]
    thesis: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SourceRecord:
    source_id: str
    source_name: str
    source_type: str
    base_url: str
    license_label: str
    data_class: str
    reliability_score: float
    metadata: dict[str, object] = field(default_factory=dict)
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.min)
    updated_at: datetime = field(default_factory=lambda: datetime.min)


@dataclass(frozen=True, slots=True)
class FrontierUrlRecord:
    frontier_url_id: str
    source_id: str
    url: str
    url_hash: str
    ticker: str
    priority: int
    discovered_at: datetime
    next_attempt_at: datetime
    status: str
    attempt_count: int
    max_attempts: int
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CrawlQueueItemRecord:
    queue_id: str
    frontier_url_id: str
    ticker: str
    priority: int
    status: str
    next_attempt_at: datetime
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SkippedSourceRecord:
    source_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class SourceRegistrySeedPlan:
    source_records: tuple[SourceRecord, ...]
    frontier_url_records: tuple[FrontierUrlRecord, ...]
    skipped_sources: tuple[SkippedSourceRecord, ...]

    @property
    def skipped_sources_by_id(self) -> dict[str, str]:
        return {record.source_id: record.reason for record in self.skipped_sources}


def build_watched_equity_records(
    watchlist: AIEquityWatchlist,
    *,
    now: datetime,
) -> tuple[WatchedEquityRecord, ...]:
    require_aware_datetime(now, "now")
    return tuple(
        WatchedEquityRecord(
            ticker=entry.ticker,
            company_name=entry.company_name,
            exchange=None,
            asset_type="equity",
            active=True,
            priority=_priority_score(entry.priority),
            tags=tuple(entry.themes) + tuple(entry.sector_tags),
            thesis=None,
            created_at=now,
            updated_at=now,
        )
        for entry in watchlist.entries
    )


def build_source_records(
    watchlist: AIEquityWatchlist,
    *,
    now: datetime,
) -> tuple[SourceRecord, ...]:
    require_aware_datetime(now, "now")
    by_hostname: dict[str, SourceRecord] = {}
    for entry in watchlist.entries:
        for url in entry.source_urls:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            if not hostname:
                raise ValueError(f"watchlist source URL missing hostname: {url}")
            if hostname in by_hostname:
                continue
            scheme = parsed.scheme or "https"
            base_url = f"{scheme}://{hostname}"
            by_hostname[hostname] = SourceRecord(
                source_id=_source_id_for_hostname(hostname),
                source_name=hostname,
                source_type="company_ir_press",
                base_url=base_url,
                license_label="public",
                data_class="public_evidence",
                reliability_score=0.80,
                metadata={"origin": "watchlist_seed", "hostname": hostname},
                active=True,
                created_at=now,
                updated_at=now,
            )
    return tuple(by_hostname.values())


def build_frontier_url_records(
    watchlist: AIEquityWatchlist,
    *,
    now: datetime,
) -> tuple[FrontierUrlRecord, ...]:
    require_aware_datetime(now, "now")
    records: list[FrontierUrlRecord] = []
    for entry in watchlist.entries:
        priority = _priority_score(entry.priority)
        for url in entry.source_urls:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            if not hostname:
                raise ValueError(f"watchlist source URL missing hostname: {url}")
            url_hash = sha256(url.encode("utf-8")).hexdigest()
            records.append(
                FrontierUrlRecord(
                    frontier_url_id=f"frontier-{entry.ticker.lower()}-{url_hash[:16]}",
                    source_id=_source_id_for_hostname(hostname),
                    url=url,
                    url_hash=url_hash,
                    ticker=entry.ticker,
                    priority=priority,
                    discovered_at=now,
                    next_attempt_at=now,
                    status="queued",
                    attempt_count=0,
                    max_attempts=3,
                    metadata={"origin": "watchlist_seed"},
                    created_at=now,
                    updated_at=now,
                )
            )
    return tuple(records)


def build_provider_source_records(
    watchlist: AIEquityWatchlist,
    *,
    now: datetime,
) -> tuple[SourceRecord, ...]:
    """Build SourceRecord rows for each API provider in the watchlist.

    Independent of `build_source_records`, which derives sources from
    watchlist entry hostnames. API providers (SEC EDGAR, yfinance, FRED, etc.)
    are configured under the top-level `providers:` block.
    """
    require_aware_datetime(now, "now")
    records: list[SourceRecord] = []
    for provider in watchlist.providers:
        metadata: dict[str, object] = {
            "origin": "api_provider",
            "ticker_fanout": provider.ticker_fanout,
            "series_fanout": list(provider.series_fanout),
            "theme_fanout": provider.theme_fanout,
            "url_templates": list(provider.url_templates),
            "requires_secret": provider.requires_secret,
        }
        records.append(
            SourceRecord(
                source_id=provider.source_id,
                source_name=provider.source_name,
                source_type=provider.source_type,
                base_url=provider.base_url,
                license_label=provider.license_label,
                data_class=provider.data_class,
                reliability_score=provider.reliability_score,
                metadata=metadata,
                active=True,
                created_at=now,
                updated_at=now,
            )
        )
    return tuple(records)


def build_provider_frontier_urls(
    watchlist: AIEquityWatchlist,
    *,
    now: datetime,
) -> tuple[FrontierUrlRecord, ...]:
    """Generate frontier URL rows for ticker-fanout providers only.

    Series-fanout (e.g. FRED) and theme-fanout (e.g. GDELT) providers do
    not bind to a single watchlist ticker. Their crawls are scheduled
    separately by reading the provider's metadata at run time, so they
    produce no rows here.
    """
    require_aware_datetime(now, "now")
    records: list[FrontierUrlRecord] = []
    for provider in watchlist.providers:
        if not provider.ticker_fanout:
            continue
        for entry in watchlist.entries:
            priority = _priority_score(entry.priority)
            for template in provider.url_templates:
                url = _frontier_url_from_template(template, ticker=entry.ticker)
                url_hash = sha256(url.encode("utf-8")).hexdigest()
                records.append(
                    FrontierUrlRecord(
                        frontier_url_id=(
                            f"frontier-{entry.ticker.lower()}-{url_hash[:16]}"
                        ),
                        source_id=provider.source_id,
                        url=url,
                        url_hash=url_hash,
                        ticker=entry.ticker,
                        priority=priority,
                        discovered_at=now,
                        next_attempt_at=now,
                        status="queued",
                        attempt_count=0,
                        max_attempts=3,
                        metadata={
                            "origin": "api_provider",
                            "provider_source_id": provider.source_id,
                            "url_template": template,
                        },
                        created_at=now,
                        updated_at=now,
                    )
                )
    return tuple(records)


def build_source_registry_seed_plan(
    watchlist: AIEquityWatchlist,
    registry: SourceRegistry,
    *,
    now: datetime,
    environ: dict[str, str] | None = None,
) -> SourceRegistrySeedPlan:
    """Build source and frontier rows from source_registry + watchlist.

    Optional-secret sources are still represented in `source_records` so source
    quality metadata remains visible, but their frontier rows are skipped until
    the configured secret exists. Secret placeholders are never materialized in
    stored URLs.
    """
    require_aware_datetime(now, "now")
    env = environ if environ is not None else {}
    source_records: list[SourceRecord] = []
    frontier_records: list[FrontierUrlRecord] = []
    skipped: list[SkippedSourceRecord] = []

    for source in registry.sources:
        skip_reason = _skip_reason(source, env)
        source_records.append(_source_record_from_registry(source, now=now, skip_reason=skip_reason))
        if skip_reason is not None:
            skipped.append(SkippedSourceRecord(source_id=source.source_id, reason=skip_reason))
            continue
        frontier_records.extend(
            _frontier_records_from_registry_source(
                watchlist,
                source,
                now=now,
            )
        )

    return SourceRegistrySeedPlan(
        source_records=tuple(source_records),
        frontier_url_records=tuple(frontier_records),
        skipped_sources=tuple(skipped),
    )


def build_crawl_queue_items(
    frontier_urls: tuple[FrontierUrlRecord, ...],
    *,
    now: datetime,
) -> tuple[CrawlQueueItemRecord, ...]:
    require_aware_datetime(now, "now")
    return tuple(
        CrawlQueueItemRecord(
            queue_id=f"queue-{record.frontier_url_id.removeprefix('frontier-')}",
            frontier_url_id=record.frontier_url_id,
            ticker=record.ticker,
            priority=record.priority,
            status="queued",
            next_attempt_at=now,
            created_at=now,
            updated_at=now,
        )
        for record in frontier_urls
    )


def _priority_score(priority_label: str) -> int:
    try:
        return PRIORITY_SCORES[priority_label.lower()]
    except KeyError as exc:
        raise ValueError(f"unknown priority label: {priority_label}") from exc


class _PreserveUnknownPlaceholders(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _frontier_url_from_template(template: str, *, ticker: str) -> str:
    formatted = template.format_map(_PreserveUnknownPlaceholders(ticker=ticker))
    parsed = urlparse(formatted)
    secret_placeholders = {"{api_key}", "{api_token}"}
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if value not in secret_placeholders
    ]
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(query_pairs, doseq=True),
            parsed.fragment,
        )
    )


def _source_record_from_registry(
    source: RegistrySource,
    *,
    now: datetime,
    skip_reason: str | None,
) -> SourceRecord:
    metadata: dict[str, object] = {
        "origin": "source_registry",
        "tier": source.tier,
        "source_kind": source.source_kind,
        "trust_weight": source.trust_weight,
        "refresh_interval_minutes": source.refresh_interval_minutes,
        "requires_secret": source.requires_secret,
        "secret_env_var": source.secret_env_var,
        "metadata_only": source.metadata_only,
        "fanout": source.fanout,
        "ticker_allowlist": list(source.ticker_allowlist),
        "series_ids": list(source.series_ids),
        "themes": list(source.themes),
        "url_templates": list(source.url_templates),
    }
    if skip_reason is not None:
        metadata["seed_status"] = "skipped_frontier"
        metadata["skip_reason"] = skip_reason
    return SourceRecord(
        source_id=source.source_id,
        source_name=source.source_name,
        source_type=source.source_kind,
        base_url=source.base_url,
        license_label=source.license_label,
        data_class=source.data_class,
        reliability_score=source.trust_weight,
        metadata=metadata,
        active=True,
        created_at=now,
        updated_at=now,
    )


def _frontier_records_from_registry_source(
    watchlist: AIEquityWatchlist,
    source: RegistrySource,
    *,
    now: datetime,
) -> tuple[FrontierUrlRecord, ...]:
    entries = _entries_for_source(watchlist, source)
    records: list[FrontierUrlRecord] = []
    for entry in entries:
        priority = _priority_score(entry.priority)
        for template in source.url_templates:
            if source.fanout == "series":
                for series_id in source.series_ids:
                    url = _frontier_url_from_registry_template(
                        template,
                        ticker=entry.ticker,
                        company_name=entry.company_name,
                        series_id=series_id,
                    )
                    records.append(
                        _frontier_record_from_registry_url(
                            source,
                            url=url,
                            ticker=entry.ticker,
                            priority=priority,
                            now=now,
                            metadata_extra={"series_id": series_id},
                        )
                    )
            else:
                url = _frontier_url_from_registry_template(
                    template,
                    ticker=entry.ticker,
                    company_name=entry.company_name,
                    series_id=None,
                )
                records.append(
                    _frontier_record_from_registry_url(
                        source,
                        url=url,
                        ticker=entry.ticker,
                        priority=priority,
                        now=now,
                        metadata_extra={},
                    )
                )
    return tuple(records)


def _entries_for_source(watchlist: AIEquityWatchlist, source: RegistrySource):
    if not source.ticker_allowlist:
        return watchlist.entries
    allowed = set(source.ticker_allowlist)
    return tuple(entry for entry in watchlist.entries if entry.ticker in allowed)


def _frontier_record_from_registry_url(
    source: RegistrySource,
    *,
    url: str,
    ticker: str,
    priority: int,
    now: datetime,
    metadata_extra: dict[str, object],
) -> FrontierUrlRecord:
    canonical = canonicalize_url(url)
    url_hash = sha256(canonical.canonical_url.encode("utf-8")).hexdigest()
    metadata: dict[str, object] = {
        "origin": "source_registry",
        "tier": source.tier,
        "source_kind": source.source_kind,
        "trust_weight": source.trust_weight,
        "refresh_interval_minutes": source.refresh_interval_minutes,
        "metadata_only": source.metadata_only,
        "access_mode": "metadata_excerpt_only" if source.metadata_only else "public_source",
        "license_label": source.license_label,
        "data_class": source.data_class,
    }
    metadata.update(metadata_extra)
    return FrontierUrlRecord(
        frontier_url_id=f"frontier-{ticker.lower()}-{url_hash[:16]}",
        source_id=source.source_id,
        url=canonical.canonical_url,
        url_hash=url_hash,
        ticker=ticker,
        priority=priority,
        discovered_at=now,
        next_attempt_at=now,
        status="queued",
        attempt_count=0,
        max_attempts=3,
        metadata=metadata,
        created_at=now,
        updated_at=now,
    )


class _RegistryTemplateValues(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _frontier_url_from_registry_template(
    template: str,
    *,
    ticker: str,
    company_name: str,
    series_id: str | None,
) -> str:
    values = _RegistryTemplateValues(
        ticker=ticker,
        company_name=company_name,
        company_slug=_slug_for(company_name),
    )
    if series_id is not None:
        values["series_id"] = series_id
    formatted = template.format_map(values)
    return _strip_secret_placeholders(formatted)


def _strip_secret_placeholders(url: str) -> str:
    parsed = urlparse(url)
    secret_keys = {"api_key", "api_token", "token"}
    secret_values = {"{api_key}", "{api_token}", "{token}"}
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in secret_keys and value not in secret_values
    ]
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(query_pairs, doseq=True),
            parsed.fragment,
        )
    )


def _skip_reason(source: RegistrySource, environ: dict[str, str]) -> str | None:
    if not source.requires_secret:
        return None
    env_var = source.secret_env_var or ""
    if environ.get(env_var):
        return None
    return f"missing_secret:{env_var}"


def _slug_for(value: str) -> str:
    return _SLUG_PATTERN.sub("-", value.lower()).strip("-")


_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def _source_id_for_hostname(hostname: str) -> str:
    slug = _SLUG_PATTERN.sub("-", hostname.lower()).strip("-")
    return f"source-host-{slug}"


__all__ = [
    "PRIORITY_SCORES",
    "CrawlQueueItemRecord",
    "FrontierUrlRecord",
    "SkippedSourceRecord",
    "SourceRecord",
    "SourceRegistrySeedPlan",
    "WatchedEquityRecord",
    "build_crawl_queue_items",
    "build_frontier_url_records",
    "build_provider_frontier_urls",
    "build_provider_source_records",
    "build_source_registry_seed_plan",
    "build_source_records",
    "build_watched_equity_records",
]
