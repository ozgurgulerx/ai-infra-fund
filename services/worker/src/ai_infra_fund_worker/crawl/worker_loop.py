from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Protocol
from uuid import uuid4

from ai_infra_fund_api.repositories.crawl_logs import (
    CrawlLogRecord,
    CrawlLogRepository,
)
from ai_infra_fund_api.repositories.evidence import EvidenceRepository
from ai_infra_fund_api.repositories.equity_intelligence import (
    EquityIntelligenceRepository,
)
from ai_infra_fund_core.contracts.common import DataClass
from ai_infra_fund_core.contracts.evidence import EvidenceItem
from ai_infra_fund_core.equity_intelligence.advisory_materializer import (
    materialize_crawl_advisory_records,
)
from ai_infra_fund_core.equity_intelligence.capture import LocalCaptureStore
from ai_infra_fund_core.equity_intelligence.event_extractor import extract_events
from ai_infra_fund_core.equity_intelligence.extraction import ExtractedDocument, extract
from ai_infra_fund_core.equity_intelligence.fetcher import FetchResult
from ai_infra_fund_core.equity_intelligence.frontier import FrontierPolicy
from ai_infra_fund_core.equity_intelligence.research_extractor import (
    CaptureContext,
    LLMClaimExtractor,
)


# Effectively "never retry" (matches BLOCKED_AVAILABLE_AT in core frontier).
_BLOCKED_BACKOFF = timedelta(days=365 * 10)
_RATE_LIMIT_BACKOFF_BASE = timedelta(hours=1)
_FORBIDDEN_BACKOFF_BASE = timedelta(hours=24)
_DEFAULT_RECRAWL_AFTER = timedelta(hours=12)
_RECRAWL_FALLBACKS = {
    "sec_filings": timedelta(hours=1),
    "company_investor_relations": timedelta(hours=6),
    "company_ir_press": timedelta(hours=6),
    "earnings_releases": timedelta(hours=12),
    "semiconductor_supply_chain_news": timedelta(hours=12),
    "cowos_advanced_packaging_news": timedelta(hours=12),
    "datacenter_leasing_power_contracts": timedelta(hours=12),
    "power_grid_nuclear_gas": timedelta(hours=12),
    "ai_model_progress": timedelta(hours=12),
    "public_sentiment_news_flow": timedelta(hours=12),
    "macro_rates_liquidity_commentary": timedelta(hours=24),
    "utility_load_growth_guidance": timedelta(hours=24),
    "market_price_snapshot": timedelta(hours=24),
    "static_product_page": timedelta(hours=24),
}


@dataclass(frozen=True, slots=True)
class CrawlBatchReport:
    leased: int
    succeeded: int
    not_modified: int
    failed: int


class Fetcher(Protocol):
    def fetch(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult: ...


class EvidenceItemWriter(Protocol):
    def save_item(self, item: EvidenceItem) -> EvidenceItem: ...


def run_crawl_batch(
    connection: object,
    *,
    worker_id: str,
    policy: FrontierPolicy,
    fetcher: Fetcher,
    capture_store: LocalCaptureStore,
    research_extractor: LLMClaimExtractor,
    now: datetime,
) -> CrawlBatchReport:
    """Lease a batch of due frontier URLs, fetch them, persist captures + events.

    All HTTP failures are recorded; the deterministic core decides backoff.
    Snapshots (sentiment/technical/fundamental) are not produced here — those
    belong to downstream signal computation pipelines.
    """
    repo = EquityIntelligenceRepository(connection)  # type: ignore[arg-type]
    crawl_log_repo = CrawlLogRepository(connection)  # type: ignore[arg-type]
    evidence_repo = EvidenceRepository(connection)  # type: ignore[arg-type]

    lease_until = now + policy.lease_duration
    leased = repo.lease_due_frontier_urls(
        worker_id=worker_id,
        lease_expires_at=lease_until,
        limit=policy.batch_size,
        now=now,
    )

    succeeded = 0
    not_modified = 0
    failed = 0

    for row in leased:
        outcome = _process_one(
            row=row,
            repo=repo,
            crawl_log_repo=crawl_log_repo,
            policy=policy,
            fetcher=fetcher,
            capture_store=capture_store,
            research_extractor=research_extractor,
            now=now,
            evidence_repo=evidence_repo,
        )
        if outcome == "succeeded":
            succeeded += 1
        elif outcome == "not_modified":
            not_modified += 1
        else:
            failed += 1

    return CrawlBatchReport(
        leased=len(leased),
        succeeded=succeeded,
        not_modified=not_modified,
        failed=failed,
    )


def _process_one(
    *,
    row: dict,
    repo: EquityIntelligenceRepository,
    crawl_log_repo: CrawlLogRepository,
    policy: FrontierPolicy,
    fetcher: Fetcher,
    capture_store: LocalCaptureStore,
    research_extractor: LLMClaimExtractor,
    now: datetime,
    evidence_repo: EvidenceItemWriter | None = None,
) -> str:
    frontier_url_id = str(row["frontier_url_id"])
    ticker = str(row["ticker"]) if row.get("ticker") else None
    source_id = str(row["source_id"]) if row.get("source_id") else None
    url = str(row["url"])
    attempt_count_before = int(row.get("attempt_count", 0) or 0)
    max_attempts = int(row.get("max_attempts", 3) or 3)
    attempt_id = f"attempt-{uuid4().hex}"

    metadata = repo.get_frontier_metadata(frontier_url_id=frontier_url_id)
    etag = _maybe_str(metadata.get("etag"))
    last_modified = _maybe_str(metadata.get("last_modified"))

    try:
        result = fetcher.fetch(url, etag=etag, last_modified=last_modified)
    except Exception as error:
        return _record_failed_attempt(
            repo=repo,
            crawl_log_repo=crawl_log_repo,
            frontier_url_id=frontier_url_id,
            ticker=ticker,
            source_id=source_id,
            url=url,
            attempt_id=attempt_id,
            attempt_count_before=attempt_count_before,
            max_attempts=max_attempts,
            policy=policy,
            now=now,
            frontier_metadata=metadata,
            error_summary=_safe_exception_summary(error),
            fetch_method="error",
            http_status=None,
            latency_ms=0,
            bytes_fetched=None,
        )

    # 304: nothing changed, write log + schedule the next configured recrawl.
    if result.http_status == 304:
        crawl_log_repo.record_attempt(
            CrawlLogRecord(
                attempt_id=attempt_id,
                frontier_url_id=frontier_url_id,
                ticker=ticker,
                source_id=source_id,
                url=url,
                attempted_at=now,
                fetch_method="http_304",
                http_status=304,
                latency_ms=result.latency_ms,
                bytes_fetched=0,
                capture_id=None,
                error_summary=None,
            )
        )
        repo.update_frontier_metadata(
            frontier_url_id=frontier_url_id,
            metadata=_success_metadata(
                existing=metadata,
                result=result,
                now=now,
                capture_id=None,
            ),
            now=now,
        )
        repo.schedule_frontier_recrawl(
            frontier_url_id=frontier_url_id,
            next_attempt_at=_next_recrawl_at(row=row, metadata=metadata, now=now),
            now=now,
        )
        return "not_modified"

    # Failure path: any error_summary, missing status, or HTTP >= 400.
    if (
        result.error_summary is not None
        or result.http_status is None
        or result.http_status >= 400
    ):
        error_summary = result.error_summary or f"http_{result.http_status}"
        # Transport-level vs HTTP-status failures: keep `error` for the former
        # so the dashboard's "client_error"/"server_error" buckets reflect real
        # 4xx/5xx responses, not connect/timeout failures.
        log_fetch_method = "error" if result.http_status is None else "http_get"
        return _record_failed_attempt(
            repo=repo,
            crawl_log_repo=crawl_log_repo,
            frontier_url_id=frontier_url_id,
            ticker=ticker,
            source_id=source_id,
            url=url,
            attempt_id=attempt_id,
            attempt_count_before=attempt_count_before,
            max_attempts=max_attempts,
            policy=policy,
            now=now,
            frontier_metadata=metadata,
            error_summary=error_summary,
            fetch_method=log_fetch_method,
            http_status=result.http_status,
            latency_ms=result.latency_ms,
            bytes_fetched=len(result.body_bytes) or None,
        )

    # Success: capture, extract, persist atomically.
    stored = capture_store.store(
        result.body_bytes,
        response_headers={
            "Content-Type": result.content_type or "",
            "ETag": result.etag or "",
            "Last-Modified": result.last_modified or "",
        },
    )
    capture_id = f"capture-{stored.content_hash[:24]}"
    extracted = extract(
        result.content_type or "text/html",
        result.body_bytes,
        base_url=url,
    )

    ticker_value = ticker or _ticker_from_frontier_id(frontier_url_id)
    source_value = source_id or "source-unknown"
    frontier_metadata = _merged_frontier_metadata(row=row, metadata=metadata)
    evidence_item = _build_evidence_item(
        url=url,
        source_value=source_value,
        ticker_value=ticker_value,
        stored=stored,
        extracted=extracted,
        result=result,
        frontier_metadata=frontier_metadata,
        now=now,
    )

    raw_event_records = extract_events(
        ticker=ticker_value,
        source_id=source_value,
        capture_id=capture_id,
        extracted=extracted,
        fetched_at=now,
    )
    event_records = tuple(
        replace(record, evidence_ids=[evidence_item.evidence_id])
        for record in raw_event_records
    )

    # Deep-research extension point (v1 stub: returns empty result, no LLM call).
    research_extractor.extract_claims(
        capture=CaptureContext(
            ticker=ticker_value,
            source_id=source_value,
            capture_id=capture_id,
            url=url,
            data_class="public_evidence",
            extracted=extracted,
            fetched_at=now,
        ),
        model_router=None,
    )

    capture_record = SimpleNamespace(
        capture_id=capture_id,
        frontier_url_id=frontier_url_id,
        source_id=source_value,
        url=url,
        captured_at=now,
        http_status=result.http_status,
        content_hash=stored.content_hash,
        storage_uri=stored.storage_uri,
        content_type=result.content_type,
        byte_size=stored.byte_size,
        metadata={
            "etag": result.etag or "",
            "last_modified": result.last_modified or "",
            "fetch_method": result.fetch_method,
            "evidence_id": evidence_item.evidence_id,
        },
        created_at=now,
    )
    materialized = materialize_crawl_advisory_records(
        capture=capture_record,
        equity_events=event_records,
        frontier_metadata=frontier_metadata,
    )
    run_record = SimpleNamespace(
        run_id=f"run-crawl-{attempt_id.removeprefix('attempt-')[:16]}",
        ticker=ticker_value,
        started_at=now,
        completed_at=now,
        status="succeeded",
        source_refresh_job_ids=[],
        frontier_url_ids=[frontier_url_id],
        capture_ids=[capture_id],
        event_ids=[record.event_id for record in event_records],
        sentiment_snapshot_id=None,
        technical_snapshot_id=None,
        fundamental_snapshot_id=None,
        summary={
            "fetch_method": result.fetch_method,
            "latency_ms": result.latency_ms,
            "byte_size": stored.byte_size,
            "events_emitted": len(event_records),
            "source_signals_emitted": len(materialized.source_signals),
            "market_events_emitted": len(materialized.market_events),
            "source_signal_ids": [
                record.signal_id for record in materialized.source_signals
            ],
            "market_event_ids": [
                record.event_id for record in materialized.market_events
            ],
        },
        model_run_ids=[],
        error_summary=None,
        created_at=now,
    )

    if evidence_repo is not None:
        evidence_repo.save_item(evidence_item)

    repo.save_crawl_capture_advisory_materials_and_run(
        source_raw_capture=capture_record,
        equity_events=event_records,
        source_signals=materialized.source_signals,
        market_events=materialized.market_events,
        intelligence_run=run_record,
    )

    repo.update_frontier_metadata(
        frontier_url_id=frontier_url_id,
        metadata=_success_metadata(
            existing=metadata,
            result=result,
            now=now,
            capture_id=capture_id,
        ),
        now=now,
    )
    repo.schedule_frontier_recrawl(
        frontier_url_id=frontier_url_id,
        next_attempt_at=_next_recrawl_at(row=row, metadata=frontier_metadata, now=now),
        now=now,
    )

    crawl_log_repo.record_attempt(
        CrawlLogRecord(
            attempt_id=attempt_id,
            frontier_url_id=frontier_url_id,
            ticker=ticker_value,
            source_id=source_value,
            url=url,
            attempted_at=now,
            fetch_method="http_get",
            http_status=result.http_status,
            latency_ms=result.latency_ms,
            bytes_fetched=len(result.body_bytes),
            capture_id=capture_id,
            error_summary=None,
        )
    )
    return "succeeded"


def _maybe_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _merged_frontier_metadata(
    *,
    row: dict,
    metadata: dict[str, object],
) -> dict[str, object]:
    row_metadata = row.get("metadata")
    merged: dict[str, object] = {}
    if isinstance(row_metadata, dict):
        merged.update(row_metadata)
    merged.update(metadata)
    return merged


def _success_metadata(
    *,
    existing: dict[str, object],
    result: FetchResult,
    now: datetime,
    capture_id: str | None,
) -> dict[str, object]:
    metadata = dict(existing)
    metadata.update(
        {
            "etag": result.etag,
            "last_modified": result.last_modified,
            "last_http_status": result.http_status,
            "last_success_at": now.isoformat(),
            "consecutive_failures": 0,
            "crawl_allowed": True,
            "render_strategy": metadata.get("render_strategy") or "http_only",
        }
    )
    if capture_id is not None:
        metadata["last_capture_id"] = capture_id
    metadata.pop("backoff_until", None)
    metadata.pop("blocked_until", None)
    metadata.pop("last_error_summary", None)
    return metadata


def _build_evidence_item(
    *,
    url: str,
    source_value: str,
    ticker_value: str,
    stored: object,
    extracted: object,
    result: FetchResult,
    frontier_metadata: dict[str, object],
    now: datetime,
) -> EvidenceItem:
    content_hash = str(getattr(stored, "content_hash"))
    capture_id = f"capture-{content_hash[:24]}"
    return EvidenceItem(
        evidence_id=f"evidence-{capture_id}",
        source_uri=url,
        source_type=_evidence_source_type(
            source_value=source_value,
            result=result,
            frontier_metadata=frontier_metadata,
        ),
        title=_evidence_title(extracted),
        publisher=_optional_metadata_text(frontier_metadata, "publisher"),
        author=None,
        published_at=_evidence_published_at(extracted),
        ingested_at=now,
        content_hash=content_hash,
        license_label=_license_label(frontier_metadata),
        data_class=_evidence_data_class(frontier_metadata),
        tickers=(ticker_value.upper(),),
        themes=_evidence_themes(frontier_metadata),
        summary=_evidence_summary(extracted),
        storage_uri=str(getattr(stored, "storage_uri")),
        created_at=now,
    )


def _evidence_source_type(
    *,
    source_value: str,
    result: FetchResult,
    frontier_metadata: dict[str, object],
) -> str:
    for key in ("source_kind", "source_type"):
        value = _optional_metadata_text(frontier_metadata, key)
        if value:
            return value
    content_type = (result.content_type or "").split(";")[0].strip()
    if content_type:
        return content_type
    return source_value


def _evidence_title(extracted: object) -> str | None:
    if isinstance(extracted, ExtractedDocument):
        return extracted.title
    if isinstance(extracted, tuple) and extracted:
        return str(getattr(extracted[0], "title", "")).strip() or None
    return None


def _evidence_published_at(extracted: object) -> datetime | None:
    if isinstance(extracted, ExtractedDocument):
        return extracted.published_at
    if isinstance(extracted, tuple) and extracted:
        value = getattr(extracted[0], "published_at", None)
        if isinstance(value, datetime):
            return value
    return None


def _evidence_summary(extracted: object) -> str | None:
    if isinstance(extracted, ExtractedDocument):
        text = extracted.clean_text.strip()
        return text[:500] if text else None
    if isinstance(extracted, tuple):
        return f"RSS/Atom feed capture with {len(extracted)} item(s)."
    return None


def _license_label(frontier_metadata: dict[str, object]) -> str:
    return _optional_metadata_text(frontier_metadata, "license_label") or "public_source"


def _evidence_data_class(frontier_metadata: dict[str, object]) -> DataClass:
    value = (
        _optional_metadata_text(frontier_metadata, "data_class")
        or DataClass.PUBLIC_EVIDENCE.value
    )
    data_class = DataClass(value)
    if data_class not in (DataClass.PUBLIC_EVIDENCE, DataClass.PUBLIC_MARKET_DATA):
        raise ValueError("crawler evidence must use a public data class")
    return data_class


def _evidence_themes(frontier_metadata: dict[str, object]) -> tuple[str, ...]:
    raw_themes = frontier_metadata.get("themes")
    if isinstance(raw_themes, str):
        values = (raw_themes,)
    elif isinstance(raw_themes, (list, tuple)):
        values = tuple(str(value) for value in raw_themes)
    else:
        values = ()
    normalized = tuple(value.strip() for value in values if value.strip())
    return normalized or ("ai_infrastructure",)


def _optional_metadata_text(
    frontier_metadata: dict[str, object],
    key: str,
) -> str | None:
    value = frontier_metadata.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _record_failed_attempt(
    *,
    repo: EquityIntelligenceRepository,
    crawl_log_repo: CrawlLogRepository,
    frontier_url_id: str,
    ticker: str | None,
    source_id: str | None,
    url: str,
    attempt_id: str,
    attempt_count_before: int,
    max_attempts: int,
    policy: FrontierPolicy,
    now: datetime,
    frontier_metadata: dict[str, object] | None = None,
    error_summary: str,
    fetch_method: str,
    http_status: int | None,
    latency_ms: int | None,
    bytes_fetched: int | None,
) -> str:
    next_attempt_at = _next_attempt_at(
        attempt_count_before=attempt_count_before,
        max_attempts=max_attempts,
        policy=policy,
        now=now,
        http_status=http_status,
    )
    metadata = _failure_metadata(
        existing=frontier_metadata or {},
        error_summary=error_summary,
        http_status=http_status,
        next_attempt_at=next_attempt_at,
        now=now,
    )
    repo.update_frontier_metadata(
        frontier_url_id=frontier_url_id,
        metadata=metadata,
        now=now,
    )
    repo.record_frontier_failure(
        frontier_url_id=frontier_url_id,
        error_summary=error_summary,
        next_attempt_at=next_attempt_at,
        now=now,
    )
    crawl_log_repo.record_attempt(
        CrawlLogRecord(
            attempt_id=attempt_id,
            frontier_url_id=frontier_url_id,
            ticker=ticker,
            source_id=source_id,
            url=url,
            attempted_at=now,
            fetch_method=fetch_method,
            http_status=http_status,
            latency_ms=latency_ms,
            bytes_fetched=bytes_fetched,
            capture_id=None,
            error_summary=error_summary,
        )
    )
    return "failed"


def _next_attempt_at(
    *,
    attempt_count_before: int,
    max_attempts: int,
    policy: FrontierPolicy,
    now: datetime,
    http_status: int | None,
) -> datetime:
    next_attempt_count = attempt_count_before + 1
    if http_status == 403:
        return now + _FORBIDDEN_BACKOFF_BASE
    if next_attempt_count >= max_attempts:
        return now + _BLOCKED_BACKOFF
    backoff_base = (
        _RATE_LIMIT_BACKOFF_BASE if http_status == 429 else policy.backoff_base
    )
    return now + backoff_base * (2 ** (next_attempt_count - 1))


def _failure_metadata(
    *,
    existing: dict[str, object],
    error_summary: str,
    http_status: int | None,
    next_attempt_at: datetime,
    now: datetime,
) -> dict[str, object]:
    metadata = dict(existing)
    current_failures = _int_metadata(metadata.get("consecutive_failures"), default=0)
    metadata.update(
        {
            "consecutive_failures": current_failures + 1,
            "last_failure_at": now.isoformat(),
            "last_http_status": http_status,
            "last_error_summary": error_summary,
            "backoff_until": next_attempt_at.isoformat(),
            "render_strategy": metadata.get("render_strategy") or "http_only",
        }
    )
    if http_status == 429:
        metadata["blocked_until"] = next_attempt_at.isoformat()
    if http_status == 403 or error_summary == "robots_disallowed":
        metadata["blocked_until"] = next_attempt_at.isoformat()
        metadata["render_strategy"] = "blocked"
        metadata["crawl_allowed"] = False
    else:
        metadata.setdefault("crawl_allowed", True)
    if error_summary == "robots_disallowed":
        metadata["robots_disallow"] = True
    return metadata


def _next_recrawl_at(
    *,
    row: dict,
    metadata: dict[str, object],
    now: datetime,
) -> datetime:
    return now + _recrawl_after(row=row, metadata=metadata)


def _recrawl_after(*, row: dict, metadata: dict[str, object]) -> timedelta:
    minutes = _refresh_interval_minutes(row=row, metadata=metadata)
    if minutes is not None:
        return timedelta(minutes=minutes)
    source_kind = _metadata_text(row=row, metadata=metadata, key="source_kind")
    if source_kind in _RECRAWL_FALLBACKS:
        return _RECRAWL_FALLBACKS[source_kind]
    source_id = (str(row.get("source_id") or "")).lower()
    if "sec" in source_id:
        return timedelta(hours=1)
    if "fred" in source_id or "eia" in source_id:
        return timedelta(hours=24)
    if "gdelt" in source_id or "news" in source_id or "rss" in source_id:
        return timedelta(hours=12)
    return _DEFAULT_RECRAWL_AFTER


def _refresh_interval_minutes(
    *,
    row: dict,
    metadata: dict[str, object],
) -> int | None:
    for value in (
        metadata.get("refresh_interval_minutes"),
        row.get("refresh_interval_minutes"),
    ):
        minutes = _int_metadata(value, default=0)
        if minutes > 0:
            return minutes
    row_metadata = row.get("metadata")
    if isinstance(row_metadata, dict):
        minutes = _int_metadata(row_metadata.get("refresh_interval_minutes"), default=0)
        if minutes > 0:
            return minutes
    return None


def _metadata_text(*, row: dict, metadata: dict[str, object], key: str) -> str | None:
    value = metadata.get(key)
    if value is None and isinstance(row.get("metadata"), dict):
        value = row["metadata"].get(key)  # type: ignore[index]
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_metadata(value: object, *, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _safe_exception_summary(error: Exception) -> str:
    return f"unexpected_exception:{type(error).__name__}"


def _ticker_from_frontier_id(frontier_url_id: str) -> str:
    parts = frontier_url_id.split("-")
    if len(parts) >= 2:
        return parts[1].upper()
    return "UNKNOWN"


__all__ = ["CrawlBatchReport", "Fetcher", "run_crawl_batch"]
