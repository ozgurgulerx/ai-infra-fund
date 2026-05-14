from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import json
from typing import Protocol

from ai_infra_fund_core.contracts.common import (
    canonicalize,
    require_aware_datetime,
    require_content_hash,
    require_text,
)


class Cursor(Protocol):
    description: object

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...

    def fetchall(self) -> list[object]:
        ...

    def fetchone(self) -> object | None:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...

    def commit(self) -> None:
        ...


FRONTIER_COLUMNS = (
    "frontier_url_id",
    "source_id",
    "url",
    "url_hash",
    "ticker",
    "priority",
    "discovered_at",
    "next_attempt_at",
    "status",
    "attempt_count",
    "max_attempts",
    "metadata",
    "created_at",
    "updated_at",
)

LATEST_SUMMARY_COLUMNS = (
    "ticker",
    "latest_event_at",
    "latest_event_summary",
    "sentiment_snapshot_id",
    "sentiment_as_of",
    "sentiment_score",
    "technical_snapshot_id",
    "technical_as_of",
    "trend_label",
    "fundamental_snapshot_id",
    "fundamental_as_of",
    "rating_label",
    "latest_run_id",
    "latest_run_status",
)

FRONTIER_STATUSES = frozenset({"queued", "leased", "captured", "retry", "failed", "skipped"})
REFRESH_JOB_STATUSES = frozenset({"queued", "running", "succeeded", "failed", "cancelled"})
RUN_STATUSES = frozenset({"pending", "running", "succeeded", "failed", "cancelled"})
SEVERITIES = frozenset({"low", "medium", "high", "critical"})


UPSERT_WATCHED_EQUITY_SQL = """
INSERT INTO core.watched_equities (
    ticker,
    company_name,
    exchange,
    asset_type,
    active,
    priority,
    tags,
    thesis,
    created_at,
    updated_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (ticker) DO UPDATE SET
    company_name = EXCLUDED.company_name,
    exchange = EXCLUDED.exchange,
    asset_type = EXCLUDED.asset_type,
    active = EXCLUDED.active,
    priority = EXCLUDED.priority,
    tags = EXCLUDED.tags,
    thesis = EXCLUDED.thesis,
    updated_at = EXCLUDED.updated_at;
"""


UPSERT_SOURCE_SQL = """
INSERT INTO evidence.source_registry (
    source_id,
    source_name,
    source_type,
    base_url,
    license_label,
    data_class,
    reliability_score,
    metadata_json,
    active,
    created_at,
    updated_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s
) ON CONFLICT (source_id) DO UPDATE SET
    source_name = EXCLUDED.source_name,
    source_type = EXCLUDED.source_type,
    base_url = EXCLUDED.base_url,
    license_label = EXCLUDED.license_label,
    data_class = EXCLUDED.data_class,
    reliability_score = EXCLUDED.reliability_score,
    metadata_json = EXCLUDED.metadata_json,
    active = EXCLUDED.active,
    updated_at = EXCLUDED.updated_at;
"""


UPSERT_FRONTIER_URL_SQL = """
INSERT INTO evidence.source_frontier_urls (
    frontier_url_id,
    source_id,
    url,
    url_hash,
    ticker,
    priority,
    discovered_at,
    next_attempt_at,
    status,
    attempt_count,
    max_attempts,
    metadata_json,
    created_at,
    updated_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s
) ON CONFLICT (source_id, url_hash) DO UPDATE SET
    url = EXCLUDED.url,
    ticker = EXCLUDED.ticker,
    priority = GREATEST(evidence.source_frontier_urls.priority, EXCLUDED.priority),
    next_attempt_at = LEAST(evidence.source_frontier_urls.next_attempt_at, EXCLUDED.next_attempt_at),
    status = CASE
        WHEN evidence.source_frontier_urls.status IN ('captured', 'failed', 'skipped') THEN evidence.source_frontier_urls.status
        ELSE EXCLUDED.status
    END,
    max_attempts = EXCLUDED.max_attempts,
    metadata_json = EXCLUDED.metadata_json,
    updated_at = EXCLUDED.updated_at;
"""


LEASE_DUE_FRONTIER_URLS_SQL = """
WITH lease_input AS (
    SELECT
        %s::text AS worker_id,
        %s::timestamptz AS lease_expires_at,
        %s::timestamptz AS now_at
),
due_urls AS (
    SELECT frontier_url_id
    FROM evidence.source_frontier_urls
    WHERE status IN ('queued', 'retry')
        AND next_attempt_at <= (SELECT now_at FROM lease_input)
    ORDER BY priority DESC, next_attempt_at ASC, frontier_url_id ASC
    LIMIT %s
    FOR UPDATE SKIP LOCKED
)
UPDATE evidence.source_frontier_urls AS frontier
SET
    status = 'leased',
    leased_by = lease_input.worker_id,
    lease_expires_at = lease_input.lease_expires_at,
    updated_at = lease_input.now_at
FROM due_urls, lease_input
WHERE frontier.frontier_url_id = due_urls.frontier_url_id
RETURNING
    frontier.frontier_url_id,
    frontier.source_id,
    frontier.url,
    frontier.url_hash,
    frontier.ticker,
    frontier.priority,
    frontier.discovered_at,
    frontier.next_attempt_at,
    frontier.status,
    frontier.attempt_count,
    frontier.max_attempts,
    frontier.metadata_json AS metadata,
    frontier.created_at,
    frontier.updated_at;
"""


RECORD_FRONTIER_FAILURE_SQL = """
UPDATE evidence.source_frontier_urls
SET
    attempt_count = attempt_count + 1,
    status = CASE WHEN attempt_count + 1 >= max_attempts THEN 'failed' ELSE 'retry' END,
    last_error_summary = %s,
    next_attempt_at = %s,
    lease_expires_at = NULL,
    leased_by = NULL,
    updated_at = %s
WHERE frontier_url_id = %s;
"""


COMPLETE_FRONTIER_URL_SQL = """
UPDATE evidence.source_frontier_urls
SET
    status = 'captured',
    lease_expires_at = NULL,
    leased_by = NULL,
    updated_at = %s
WHERE frontier_url_id = %s;
"""


UPSERT_REFRESH_JOB_SQL = """
INSERT INTO evidence.source_refresh_jobs (
    refresh_job_id,
    ticker,
    reason,
    priority_boost,
    requested_at,
    status
) VALUES (
    %s, %s, %s, %s, %s, %s
) ON CONFLICT (refresh_job_id) DO UPDATE SET
    reason = EXCLUDED.reason,
    priority_boost = EXCLUDED.priority_boost,
    requested_at = EXCLUDED.requested_at,
    status = EXCLUDED.status,
    updated_at = EXCLUDED.requested_at;
"""


BOOST_FRONTIER_PRIORITY_SQL = """
UPDATE evidence.source_frontier_urls
SET
    priority = priority + %s,
    next_attempt_at = LEAST(next_attempt_at, %s),
    updated_at = now()
WHERE ticker = %s
    AND status IN ('queued', 'retry', 'leased');
"""


UPSERT_CAPTURE_SQL = """
INSERT INTO evidence.source_raw_captures (
    capture_id,
    frontier_url_id,
    source_id,
    url,
    captured_at,
    http_status,
    content_hash,
    storage_uri,
    content_type,
    byte_size,
    metadata_json,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s
) ON CONFLICT (content_hash) DO UPDATE SET
    frontier_url_id = EXCLUDED.frontier_url_id,
    source_id = EXCLUDED.source_id,
    url = EXCLUDED.url,
    captured_at = EXCLUDED.captured_at,
    http_status = EXCLUDED.http_status,
    storage_uri = EXCLUDED.storage_uri,
    content_type = EXCLUDED.content_type,
    byte_size = EXCLUDED.byte_size,
    metadata_json = EXCLUDED.metadata_json;
"""


UPSERT_EQUITY_EVENT_SQL = """
INSERT INTO signals.equity_events (
    event_id,
    ticker,
    event_type,
    event_time,
    source_capture_id,
    summary,
    severity,
    evidence_ids,
    metadata_json,
    content_hash,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s
) ON CONFLICT (content_hash) DO UPDATE SET
    event_type = EXCLUDED.event_type,
    event_time = EXCLUDED.event_time,
    source_capture_id = EXCLUDED.source_capture_id,
    summary = EXCLUDED.summary,
    severity = EXCLUDED.severity,
    evidence_ids = EXCLUDED.evidence_ids,
    metadata_json = EXCLUDED.metadata_json;
"""


UPSERT_SENTIMENT_SNAPSHOT_SQL = """
INSERT INTO signals.sentiment_snapshots (
    snapshot_id,
    ticker,
    as_of,
    source_capture_id,
    sentiment_score,
    confidence,
    drivers_json,
    content_hash,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s
) ON CONFLICT (content_hash) DO UPDATE SET
    as_of = EXCLUDED.as_of,
    source_capture_id = EXCLUDED.source_capture_id,
    sentiment_score = EXCLUDED.sentiment_score,
    confidence = EXCLUDED.confidence,
    drivers_json = EXCLUDED.drivers_json;
"""


UPSERT_TECHNICAL_SNAPSHOT_SQL = """
INSERT INTO signals.technical_snapshots (
    snapshot_id,
    ticker,
    as_of,
    indicators_json,
    trend_label,
    content_hash,
    created_at
) VALUES (
    %s, %s, %s, %s::jsonb, %s, %s, %s
) ON CONFLICT (content_hash) DO UPDATE SET
    as_of = EXCLUDED.as_of,
    indicators_json = EXCLUDED.indicators_json,
    trend_label = EXCLUDED.trend_label;
"""


UPSERT_FUNDAMENTAL_SNAPSHOT_SQL = """
INSERT INTO signals.fundamental_snapshots (
    snapshot_id,
    ticker,
    as_of,
    metrics_json,
    rating_label,
    content_hash,
    created_at
) VALUES (
    %s, %s, %s, %s::jsonb, %s, %s, %s
) ON CONFLICT (content_hash) DO UPDATE SET
    as_of = EXCLUDED.as_of,
    metrics_json = EXCLUDED.metrics_json,
    rating_label = EXCLUDED.rating_label;
"""


UPSERT_INTELLIGENCE_RUN_SQL = """
INSERT INTO audit.equity_intelligence_runs (
    run_id,
    ticker,
    started_at,
    completed_at,
    status,
    source_refresh_job_ids,
    frontier_url_ids,
    capture_ids,
    event_ids,
    sentiment_snapshot_id,
    technical_snapshot_id,
    fundamental_snapshot_id,
    summary_json,
    model_run_ids,
    error_summary,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s
) ON CONFLICT (run_id) DO UPDATE SET
    completed_at = EXCLUDED.completed_at,
    status = EXCLUDED.status,
    source_refresh_job_ids = EXCLUDED.source_refresh_job_ids,
    frontier_url_ids = EXCLUDED.frontier_url_ids,
    capture_ids = EXCLUDED.capture_ids,
    event_ids = EXCLUDED.event_ids,
    sentiment_snapshot_id = EXCLUDED.sentiment_snapshot_id,
    technical_snapshot_id = EXCLUDED.technical_snapshot_id,
    fundamental_snapshot_id = EXCLUDED.fundamental_snapshot_id,
    summary_json = EXCLUDED.summary_json,
    model_run_ids = EXCLUDED.model_run_ids,
    error_summary = EXCLUDED.error_summary;
"""


LATEST_EQUITY_SUMMARY_SQL = """
SELECT
    watched.ticker,
    latest_event.event_time AS latest_event_at,
    latest_event.summary AS latest_event_summary,
    latest_sentiment.snapshot_id AS sentiment_snapshot_id,
    latest_sentiment.as_of AS sentiment_as_of,
    latest_sentiment.sentiment_score,
    latest_technical.snapshot_id AS technical_snapshot_id,
    latest_technical.as_of AS technical_as_of,
    latest_technical.trend_label,
    latest_fundamental.snapshot_id AS fundamental_snapshot_id,
    latest_fundamental.as_of AS fundamental_as_of,
    latest_fundamental.rating_label,
    latest_run.run_id AS latest_run_id,
    latest_run.status AS latest_run_status
FROM core.watched_equities AS watched
LEFT JOIN LATERAL (
    SELECT event_time, summary
    FROM signals.equity_events
    WHERE ticker = watched.ticker
    ORDER BY event_time DESC, created_at DESC, event_id DESC
    LIMIT 1
) AS latest_event ON true
LEFT JOIN LATERAL (
    SELECT snapshot_id, as_of, sentiment_score
    FROM signals.sentiment_snapshots
    WHERE ticker = watched.ticker
    ORDER BY as_of DESC, created_at DESC, snapshot_id DESC
    LIMIT 1
) AS latest_sentiment ON true
LEFT JOIN LATERAL (
    SELECT snapshot_id, as_of, trend_label
    FROM signals.technical_snapshots
    WHERE ticker = watched.ticker
    ORDER BY as_of DESC, created_at DESC, snapshot_id DESC
    LIMIT 1
) AS latest_technical ON true
LEFT JOIN LATERAL (
    SELECT snapshot_id, as_of, rating_label
    FROM signals.fundamental_snapshots
    WHERE ticker = watched.ticker
    ORDER BY as_of DESC, created_at DESC, snapshot_id DESC
    LIMIT 1
) AS latest_fundamental ON true
LEFT JOIN LATERAL (
    SELECT run_id, status
    FROM audit.equity_intelligence_runs
    WHERE ticker = watched.ticker
    ORDER BY started_at DESC, created_at DESC, run_id DESC
    LIMIT 1
) AS latest_run ON true
WHERE watched.ticker = %s
LIMIT 1;
"""


class EquityIntelligenceRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def upsert_watched_equity(self, equity: object) -> object:
        with self._connection.cursor() as cursor:
            cursor.execute(UPSERT_WATCHED_EQUITY_SQL, _watched_equity_params(equity))
        self._connection.commit()
        return equity

    def upsert_source(self, source: object) -> object:
        with self._connection.cursor() as cursor:
            cursor.execute(UPSERT_SOURCE_SQL, _source_params(source))
        self._connection.commit()
        return source

    def upsert_frontier_url(self, frontier_url: object) -> object:
        with self._connection.cursor() as cursor:
            cursor.execute(UPSERT_FRONTIER_URL_SQL, _frontier_url_params(frontier_url))
        self._connection.commit()
        return frontier_url

    def lease_due_frontier_urls(
        self,
        *,
        worker_id: str,
        lease_expires_at: datetime,
        limit: int,
        now: datetime,
    ) -> list[dict[str, object]]:
        normalized_limit = _positive_int(limit, "limit")
        require_aware_datetime(lease_expires_at, "lease_expires_at")
        require_aware_datetime(now, "now")
        with self._connection.cursor() as cursor:
            cursor.execute(
                LEASE_DUE_FRONTIER_URLS_SQL,
                (require_text(worker_id, "worker_id"), lease_expires_at, now, normalized_limit),
            )
            rows = cursor.fetchall()
            column_names = _column_names(cursor.description) or FRONTIER_COLUMNS
        return [_row_to_dict(row, column_names) for row in rows]

    def record_frontier_failure(
        self,
        *,
        frontier_url_id: str,
        error_summary: str,
        next_attempt_at: datetime,
        now: datetime,
    ) -> None:
        require_aware_datetime(next_attempt_at, "next_attempt_at")
        require_aware_datetime(now, "now")
        with self._connection.cursor() as cursor:
            cursor.execute(
                RECORD_FRONTIER_FAILURE_SQL,
                (
                    require_text(error_summary, "error_summary"),
                    next_attempt_at,
                    now,
                    require_text(frontier_url_id, "frontier_url_id"),
                ),
            )
        self._connection.commit()

    def complete_frontier_url(self, *, frontier_url_id: str, now: datetime) -> None:
        require_aware_datetime(now, "now")
        with self._connection.cursor() as cursor:
            cursor.execute(COMPLETE_FRONTIER_URL_SQL, (now, require_text(frontier_url_id, "frontier_url_id")))
        self._connection.commit()

    def boost_refresh_priority(self, refresh_job: object) -> object:
        params = _refresh_job_params(refresh_job)
        with self._connection.cursor() as cursor:
            cursor.execute(UPSERT_REFRESH_JOB_SQL, params)
            cursor.execute(BOOST_FRONTIER_PRIORITY_SQL, (params[3], params[4], params[1]))
        self._connection.commit()
        return refresh_job

    def save_capture_event_snapshots_and_run(
        self,
        *,
        source_raw_capture: object,
        equity_event: object,
        sentiment_snapshot: object,
        technical_snapshot: object,
        fundamental_snapshot: object,
        intelligence_run: object,
    ) -> dict[str, object]:
        with self._connection.cursor() as cursor:
            cursor.execute(UPSERT_CAPTURE_SQL, _capture_params(source_raw_capture))
            cursor.execute(UPSERT_EQUITY_EVENT_SQL, _event_params(equity_event))
            cursor.execute(UPSERT_SENTIMENT_SNAPSHOT_SQL, _sentiment_params(sentiment_snapshot))
            cursor.execute(UPSERT_TECHNICAL_SNAPSHOT_SQL, _technical_params(technical_snapshot))
            cursor.execute(UPSERT_FUNDAMENTAL_SNAPSHOT_SQL, _fundamental_params(fundamental_snapshot))
            cursor.execute(UPSERT_INTELLIGENCE_RUN_SQL, _run_params(intelligence_run))
        self._connection.commit()
        return {
            "source_raw_capture": source_raw_capture,
            "equity_event": equity_event,
            "sentiment_snapshot": sentiment_snapshot,
            "technical_snapshot": technical_snapshot,
            "fundamental_snapshot": fundamental_snapshot,
            "intelligence_run": intelligence_run,
        }

    def get_latest_equity_summary(self, ticker: str) -> dict[str, object] | None:
        with self._connection.cursor() as cursor:
            cursor.execute(LATEST_EQUITY_SUMMARY_SQL, (require_text(ticker, "ticker"),))
            row = cursor.fetchone()
            if row is None:
                return None
            column_names = _column_names(cursor.description) or LATEST_SUMMARY_COLUMNS
        return _json_safe_mapping(_row_to_dict(row, column_names))


def _watched_equity_params(equity: object) -> tuple[object, ...]:
    return (
        _required_text_attr(equity, "ticker"),
        _required_text_attr(equity, "company_name"),
        _optional_text_attr(equity, "exchange"),
        _required_text_attr(equity, "asset_type"),
        _bool_attr(equity, "active"),
        _int_attr(equity, "priority"),
        _text_array(getattr(equity, "tags", ()), "tags"),
        _optional_text_attr(equity, "thesis"),
        _required_aware_datetime_attr(equity, "created_at"),
        _required_aware_datetime_attr(equity, "updated_at"),
    )


def _source_params(source: object) -> tuple[object, ...]:
    return (
        _required_text_attr(source, "source_id"),
        _required_text_attr(source, "source_name"),
        _required_text_attr(source, "source_type"),
        _required_text_attr(source, "base_url"),
        _required_text_attr(source, "license_label"),
        _required_text_attr(source, "data_class"),
        _optional_decimal_attr(source, "reliability_score"),
        _json_param(getattr(source, "metadata", {})),
        _bool_attr(source, "active"),
        _required_aware_datetime_attr(source, "created_at"),
        _required_aware_datetime_attr(source, "updated_at"),
    )


def _frontier_url_params(frontier_url: object) -> tuple[object, ...]:
    status = _required_text_attr(frontier_url, "status")
    _require_member(status, FRONTIER_STATUSES, "status")
    return (
        _required_text_attr(frontier_url, "frontier_url_id"),
        _required_text_attr(frontier_url, "source_id"),
        _required_text_attr(frontier_url, "url"),
        _required_text_attr(frontier_url, "url_hash"),
        _required_text_attr(frontier_url, "ticker"),
        _int_attr(frontier_url, "priority"),
        _required_aware_datetime_attr(frontier_url, "discovered_at"),
        _required_aware_datetime_attr(frontier_url, "next_attempt_at"),
        status,
        _non_negative_int_attr(frontier_url, "attempt_count"),
        _positive_int_attr(frontier_url, "max_attempts"),
        _json_param(getattr(frontier_url, "metadata", {})),
        _required_aware_datetime_attr(frontier_url, "created_at"),
        _required_aware_datetime_attr(frontier_url, "updated_at"),
    )


def _refresh_job_params(job: object) -> tuple[object, ...]:
    status = _required_text_attr(job, "status")
    _require_member(status, REFRESH_JOB_STATUSES, "status")
    return (
        _required_text_attr(job, "refresh_job_id"),
        _required_text_attr(job, "ticker"),
        _required_text_attr(job, "reason"),
        _int_attr(job, "priority_boost"),
        _required_aware_datetime_attr(job, "requested_at"),
        status,
    )


def _capture_params(capture: object) -> tuple[object, ...]:
    return (
        _required_text_attr(capture, "capture_id"),
        _optional_text_attr(capture, "frontier_url_id"),
        _required_text_attr(capture, "source_id"),
        _required_text_attr(capture, "url"),
        _required_aware_datetime_attr(capture, "captured_at"),
        _optional_int_attr(capture, "http_status"),
        require_content_hash(getattr(capture, "content_hash", None)),
        _required_text_attr(capture, "storage_uri"),
        _optional_text_attr(capture, "content_type"),
        _optional_int_attr(capture, "byte_size"),
        _json_param(getattr(capture, "metadata", {})),
        _required_aware_datetime_attr(capture, "created_at"),
    )


def _event_params(event: object) -> tuple[object, ...]:
    severity = _required_text_attr(event, "severity")
    _require_member(severity, SEVERITIES, "severity")
    return (
        _required_text_attr(event, "event_id"),
        _required_text_attr(event, "ticker"),
        _required_text_attr(event, "event_type"),
        _required_aware_datetime_attr(event, "event_time"),
        _optional_text_attr(event, "source_capture_id"),
        _required_text_attr(event, "summary"),
        severity,
        _text_array(getattr(event, "evidence_ids", ()), "evidence_ids"),
        _json_param(getattr(event, "metadata", {})),
        require_content_hash(getattr(event, "content_hash", None)),
        _required_aware_datetime_attr(event, "created_at"),
    )


def _sentiment_params(snapshot: object) -> tuple[object, ...]:
    return (
        _required_text_attr(snapshot, "snapshot_id"),
        _required_text_attr(snapshot, "ticker"),
        _required_aware_datetime_attr(snapshot, "as_of"),
        _optional_text_attr(snapshot, "source_capture_id"),
        _decimal_range_attr(snapshot, "sentiment_score", Decimal("-1"), Decimal("1")),
        _decimal_range_attr(snapshot, "confidence", Decimal("0"), Decimal("1")),
        _json_param(getattr(snapshot, "drivers", {})),
        require_content_hash(getattr(snapshot, "content_hash", None)),
        _required_aware_datetime_attr(snapshot, "created_at"),
    )


def _technical_params(snapshot: object) -> tuple[object, ...]:
    return (
        _required_text_attr(snapshot, "snapshot_id"),
        _required_text_attr(snapshot, "ticker"),
        _required_aware_datetime_attr(snapshot, "as_of"),
        _json_param(getattr(snapshot, "indicators", {})),
        _required_text_attr(snapshot, "trend_label"),
        require_content_hash(getattr(snapshot, "content_hash", None)),
        _required_aware_datetime_attr(snapshot, "created_at"),
    )


def _fundamental_params(snapshot: object) -> tuple[object, ...]:
    return (
        _required_text_attr(snapshot, "snapshot_id"),
        _required_text_attr(snapshot, "ticker"),
        _required_aware_datetime_attr(snapshot, "as_of"),
        _json_param(getattr(snapshot, "metrics", {})),
        _required_text_attr(snapshot, "rating_label"),
        require_content_hash(getattr(snapshot, "content_hash", None)),
        _required_aware_datetime_attr(snapshot, "created_at"),
    )


def _run_params(run: object) -> tuple[object, ...]:
    status = _required_text_attr(run, "status")
    _require_member(status, RUN_STATUSES, "status")
    completed_at = getattr(run, "completed_at", None)
    if completed_at is not None:
        require_aware_datetime(completed_at, "completed_at")
    return (
        _required_text_attr(run, "run_id"),
        _required_text_attr(run, "ticker"),
        _required_aware_datetime_attr(run, "started_at"),
        completed_at,
        status,
        _text_array(getattr(run, "source_refresh_job_ids", ()), "source_refresh_job_ids"),
        _text_array(getattr(run, "frontier_url_ids", ()), "frontier_url_ids"),
        _text_array(getattr(run, "capture_ids", ()), "capture_ids"),
        _text_array(getattr(run, "event_ids", ()), "event_ids"),
        _optional_text_attr(run, "sentiment_snapshot_id"),
        _optional_text_attr(run, "technical_snapshot_id"),
        _optional_text_attr(run, "fundamental_snapshot_id"),
        _json_param(getattr(run, "summary", {})),
        _text_array(getattr(run, "model_run_ids", ()), "model_run_ids"),
        _optional_text_attr(run, "error_summary"),
        _required_aware_datetime_attr(run, "created_at"),
    )


def _required_text_attr(record: object, field_name: str) -> str:
    return require_text(getattr(record, field_name, None), field_name)


def _optional_text_attr(record: object, field_name: str) -> str | None:
    value = getattr(record, field_name, None)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required_aware_datetime_attr(record: object, field_name: str) -> datetime:
    value = getattr(record, field_name, None)
    if value is None:
        raise ValueError(f"{field_name} is required")
    return require_aware_datetime(value, field_name)


def _bool_attr(record: object, field_name: str) -> bool:
    value = getattr(record, field_name, None)
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be boolean")
    return value


def _int_attr(record: object, field_name: str) -> int:
    value = getattr(record, field_name, None)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    return value


def _optional_int_attr(record: object, field_name: str) -> int | None:
    value = getattr(record, field_name, None)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    return value


def _non_negative_int_attr(record: object, field_name: str) -> int:
    value = _int_attr(record, field_name)
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _positive_int_attr(record: object, field_name: str) -> int:
    return _positive_int(_int_attr(record, field_name), field_name)


def _positive_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return value


def _optional_decimal_attr(record: object, field_name: str) -> Decimal | None:
    value = getattr(record, field_name, None)
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc


def _decimal_range_attr(record: object, field_name: str, low: Decimal, high: Decimal) -> Decimal:
    try:
        value = Decimal(str(getattr(record, field_name, None)))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if value < low or value > high:
        raise ValueError(f"{field_name} must be between {low} and {high}")
    return value


def _text_array(values: object, field_name: str) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        raise ValueError(f"{field_name} must be an iterable, not a string")
    return [require_text(str(value), field_name) for value in values]


def _json_param(value: object) -> str:
    return json.dumps(canonicalize(value), sort_keys=True, separators=(",", ":"))


def _require_member(value: str, allowed: frozenset[str], field_name: str) -> None:
    if value not in allowed:
        raise ValueError(f"{field_name} must be one of {sorted(allowed)}")


def _column_names(description: object) -> tuple[str, ...]:
    return tuple(_column_name(item) for item in description or ())


def _column_name(item: object) -> str:
    name = getattr(item, "name", None)
    if name is not None:
        return str(name)
    return str(item[0])  # type: ignore[index]


def _row_to_dict(row: object, column_names: tuple[str, ...]) -> dict[str, object]:
    if isinstance(row, Mapping):
        return dict(row)
    return dict(zip(column_names, row, strict=True))  # type: ignore[arg-type]


def _json_safe_mapping(row: Mapping[str, object]) -> dict[str, object]:
    return {key: _json_safe(value) for key, value in row.items()}


def _json_safe(value: object) -> object:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


__all__ = ["EquityIntelligenceRepository"]
