from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Protocol
from uuid import uuid4

from ai_infra_fund_api.repositories.crawl_logs import (
    CrawlLogRecord,
    CrawlLogRepository,
)
from ai_infra_fund_api.repositories.equity_intelligence import (
    EquityIntelligenceRepository,
)
from ai_infra_fund_core.equity_intelligence.advisory_materializer import (
    materialize_crawl_advisory_records,
)
from ai_infra_fund_core.equity_intelligence.capture import LocalCaptureStore
from ai_infra_fund_core.equity_intelligence.event_extractor import extract_events
from ai_infra_fund_core.equity_intelligence.extraction import extract
from ai_infra_fund_core.equity_intelligence.fetcher import FetchResult
from ai_infra_fund_core.equity_intelligence.frontier import FrontierPolicy
from ai_infra_fund_core.equity_intelligence.research_extractor import (
    CaptureContext,
    LLMClaimExtractor,
)


# Effectively "never retry" (matches BLOCKED_AVAILABLE_AT in core frontier).
_BLOCKED_BACKOFF = timedelta(days=365 * 10)


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
            error_summary=_safe_exception_summary(error),
            fetch_method="error",
            http_status=None,
            latency_ms=0,
            bytes_fetched=None,
        )

    # 304: nothing changed, write log + complete.
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
        repo.complete_frontier_url(frontier_url_id=frontier_url_id, now=now)
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

    event_records = extract_events(
        ticker=ticker_value,
        source_id=source_value,
        capture_id=capture_id,
        extracted=extracted,
        fetched_at=now,
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
        },
        created_at=now,
    )
    materialized = materialize_crawl_advisory_records(
        capture=capture_record,
        equity_events=event_records,
        frontier_metadata=_merged_frontier_metadata(row=row, metadata=metadata),
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

    repo.save_crawl_capture_advisory_materials_and_run(
        source_raw_capture=capture_record,
        equity_events=event_records,
        source_signals=materialized.source_signals,
        market_events=materialized.market_events,
        intelligence_run=run_record,
    )

    repo.update_frontier_metadata(
        frontier_url_id=frontier_url_id,
        metadata={
            "etag": result.etag,
            "last_modified": result.last_modified,
            "last_capture_id": capture_id,
        },
        now=now,
    )
    repo.complete_frontier_url(frontier_url_id=frontier_url_id, now=now)

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
) -> datetime:
    next_attempt_count = attempt_count_before + 1
    if next_attempt_count >= max_attempts:
        return now + _BLOCKED_BACKOFF
    return now + policy.backoff_base * (2 ** (next_attempt_count - 1))


def _safe_exception_summary(error: Exception) -> str:
    return f"unexpected_exception:{type(error).__name__}"


def _ticker_from_frontier_id(frontier_url_id: str) -> str:
    parts = frontier_url_id.split("-")
    if len(parts) >= 2:
        return parts[1].upper()
    return "UNKNOWN"


__all__ = ["CrawlBatchReport", "Fetcher", "run_crawl_batch"]
