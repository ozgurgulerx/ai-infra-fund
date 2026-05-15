from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from ai_infra_fund_core.contracts.common import require_aware_datetime, require_text


FETCH_METHODS = frozenset({"http_get", "http_head", "http_304", "stub", "error"})


@dataclass(frozen=True, slots=True)
class CrawlLogRecord:
    attempt_id: str
    frontier_url_id: str | None
    ticker: str | None
    source_id: str | None
    url: str
    attempted_at: datetime
    fetch_method: str
    http_status: int | None
    latency_ms: int | None
    bytes_fetched: int | None
    capture_id: str | None
    error_summary: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "attempt_id", require_text(self.attempt_id, "attempt_id").strip()
        )
        object.__setattr__(self, "url", require_text(self.url, "url").strip())
        require_aware_datetime(self.attempted_at, "attempted_at")
        method = require_text(self.fetch_method, "fetch_method").strip()
        if method not in FETCH_METHODS:
            raise ValueError(f"fetch_method must be one of {sorted(FETCH_METHODS)}")
        object.__setattr__(self, "fetch_method", method)


class Cursor(Protocol):
    description: object

    def execute(
        self, statement: str, params: tuple[object, ...] | None = None
    ) -> None: ...

    def fetchall(self) -> list[object]: ...

    def fetchone(self) -> object | None: ...


class Connection(Protocol):
    def cursor(self) -> object: ...

    def commit(self) -> None: ...


INSERT_CRAWL_LOG_SQL = """
INSERT INTO evidence.crawl_logs (
    attempt_id,
    frontier_url_id,
    ticker,
    source_id,
    url,
    attempted_at,
    fetch_method,
    http_status,
    latency_ms,
    bytes_fetched,
    capture_id,
    error_summary
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
);
"""


SUMMARIZE_RECENT_SQL = """
SELECT fetch_method, http_status, COUNT(*) AS attempts
FROM evidence.crawl_logs
WHERE attempted_at >= %s
GROUP BY fetch_method, http_status;
"""


class CrawlLogRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def record_attempt(self, record: CrawlLogRecord) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                INSERT_CRAWL_LOG_SQL,
                (
                    record.attempt_id,
                    record.frontier_url_id,
                    record.ticker,
                    record.source_id,
                    record.url,
                    record.attempted_at,
                    record.fetch_method,
                    record.http_status,
                    record.latency_ms,
                    record.bytes_fetched,
                    record.capture_id,
                    record.error_summary,
                ),
            )
        self._connection.commit()

    def summarize_recent(self, *, window: timedelta, now: datetime) -> dict[str, int]:
        if window <= timedelta(0):
            raise ValueError("window must be positive")
        require_aware_datetime(now, "now")
        with self._connection.cursor() as cursor:
            cursor.execute(SUMMARIZE_RECENT_SQL, (now - window,))
            rows = cursor.fetchall()
        return _bucket(rows)


def _bucket(rows: list[object]) -> dict[str, int]:
    summary = {
        "total": 0,
        "succeeded": 0,
        "not_modified": 0,
        "client_error": 0,
        "server_error": 0,
        "failed": 0,
    }
    for row in rows:
        fetch_method, http_status, count = _row_triple(row)
        summary["total"] += count
        if fetch_method == "http_304":
            summary["not_modified"] += count
        elif fetch_method == "error":
            summary["failed"] += count
        elif fetch_method in ("http_get", "http_head"):
            if isinstance(http_status, int):
                if 200 <= http_status < 300:
                    summary["succeeded"] += count
                elif 400 <= http_status < 500:
                    summary["client_error"] += count
                elif http_status >= 500:
                    summary["server_error"] += count
    return summary


def _row_triple(row: object) -> tuple[str, int | None, int]:
    if isinstance(row, Mapping):
        return (
            str(row["fetch_method"]),
            None if row.get("http_status") is None else int(row["http_status"]),
            int(row.get("attempts") or row.get("count") or 0),
        )
    sequence = list(row)  # type: ignore[arg-type]
    return (
        str(sequence[0]),
        None if sequence[1] is None else int(sequence[1]),
        int(sequence[2]),
    )


__all__ = ["CrawlLogRecord", "CrawlLogRepository"]
