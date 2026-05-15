from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol


class Cursor(Protocol):
    description: object

    def execute(
        self, statement: str, params: tuple[object, ...] | None = None
    ) -> None: ...

    def fetchone(self) -> tuple[object, ...] | None: ...

    def fetchall(self) -> list[tuple[object, ...]]: ...


class Connection(Protocol):
    def cursor(self) -> object: ...

    def commit(self) -> None: ...


INSERT_REQUEST_SQL = """
INSERT INTO audit.backtest_requests (
    request_id,
    strategy_id,
    dataset_snapshot_ids,
    validation_protocol,
    cost_assumptions,
    pipeline_inputs,
    formula_version,
    model_run_id,
    git_sha,
    as_of,
    status,
    created_at,
    updated_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'queued', %s, %s)
ON CONFLICT (request_id) DO NOTHING;
"""


LEASE_QUEUED_SQL = """
UPDATE audit.backtest_requests
SET status = 'leased',
    leased_by = %s,
    lease_expires_at = %s,
    attempt_count = attempt_count + 1,
    updated_at = now()
WHERE request_id = (
    SELECT request_id FROM audit.backtest_requests
    WHERE status = 'queued'
    ORDER BY created_at ASC, request_id ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING request_id, strategy_id, dataset_snapshot_ids, validation_protocol,
    cost_assumptions, pipeline_inputs, formula_version, model_run_id, git_sha,
    as_of, status, leased_by, lease_expires_at, attempt_count, backtest_run_id,
    error_summary, created_at, updated_at;
"""


MARK_RUNNING_SQL = """
UPDATE audit.backtest_requests
SET status = 'running', updated_at = now()
WHERE request_id = %s;
"""


MARK_SUCCEEDED_SQL = """
UPDATE audit.backtest_requests
SET status = 'succeeded',
    backtest_run_id = %s,
    error_summary = NULL,
    updated_at = now()
WHERE request_id = %s;
"""


MARK_FAILED_SQL = """
UPDATE audit.backtest_requests
SET status = 'failed',
    error_summary = %s,
    updated_at = now()
WHERE request_id = %s;
"""


SELECT_BY_ID_SQL = """
SELECT request_id, strategy_id, dataset_snapshot_ids, validation_protocol,
    cost_assumptions, pipeline_inputs, formula_version, model_run_id, git_sha,
    as_of, status, leased_by, lease_expires_at, attempt_count, backtest_run_id,
    error_summary, created_at, updated_at
FROM audit.backtest_requests
WHERE request_id = %s
LIMIT 1;
"""


SELECT_RECENT_SQL = """
SELECT request_id, strategy_id, dataset_snapshot_ids, validation_protocol,
    cost_assumptions, pipeline_inputs, formula_version, model_run_id, git_sha,
    as_of, status, leased_by, lease_expires_at, attempt_count, backtest_run_id,
    error_summary, created_at, updated_at
FROM audit.backtest_requests
ORDER BY created_at DESC, request_id DESC
LIMIT %s;
"""


RECLAIM_EXPIRED_LEASES_SQL = """
UPDATE audit.backtest_requests
SET status = 'queued',
    leased_by = NULL,
    lease_expires_at = NULL,
    updated_at = now()
WHERE status = 'leased'
  AND lease_expires_at IS NOT NULL
  AND lease_expires_at < %s
RETURNING request_id;
"""


class BacktestRequestRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def enqueue(
        self,
        *,
        request_id: str,
        strategy_id: str,
        dataset_snapshot_ids: Sequence[str],
        validation_protocol: str,
        cost_assumptions: Mapping[str, Any],
        pipeline_inputs: Mapping[str, Any],
        formula_version: str,
        model_run_id: str,
        git_sha: str,
        as_of: datetime,
        created_at: datetime | None = None,
    ) -> None:
        for label, value in (
            ("formula_version", formula_version),
            ("model_run_id", model_run_id),
            ("git_sha", git_sha),
        ):
            if not value or not value.strip():
                raise ValueError(f"{label} is required")
        timestamp = created_at or datetime.now(timezone.utc)
        params = (
            request_id,
            strategy_id,
            list(dataset_snapshot_ids),
            validation_protocol,
            json.dumps(dict(cost_assumptions), sort_keys=True, separators=(",", ":")),
            json.dumps(dict(pipeline_inputs), sort_keys=True, separators=(",", ":")),
            formula_version,
            model_run_id,
            git_sha,
            as_of,
            timestamp,
            timestamp,
        )
        with self._connection.cursor() as cursor:
            cursor.execute(INSERT_REQUEST_SQL, params)
        self._connection.commit()

    def lease_next(
        self, *, leased_by: str, ttl_seconds: int = 300
    ) -> dict[str, object] | None:
        lease_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=int(ttl_seconds)
        )
        with self._connection.cursor() as cursor:
            cursor.execute(LEASE_QUEUED_SQL, (leased_by, lease_expires_at))
            row = cursor.fetchone()
            if row is None:
                return None
            column_names = _column_names(cursor.description)
        self._connection.commit()
        return _row_to_dict(row, column_names)

    def reclaim_expired_leases(self, *, now: datetime | None = None) -> list[str]:
        cutoff = now or datetime.now(timezone.utc)
        with self._connection.cursor() as cursor:
            cursor.execute(RECLAIM_EXPIRED_LEASES_SQL, (cutoff,))
            rows = cursor.fetchall()
        self._connection.commit()
        return [str(row[0]) for row in rows]

    def mark_running(self, *, request_id: str) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(MARK_RUNNING_SQL, (request_id,))
        self._connection.commit()

    def mark_succeeded(self, *, request_id: str, backtest_run_id: str) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(MARK_SUCCEEDED_SQL, (backtest_run_id, request_id))
        self._connection.commit()

    def mark_failed(self, *, request_id: str, error_summary: str) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(MARK_FAILED_SQL, (error_summary, request_id))
        self._connection.commit()

    def get_by_id(self, request_id: str) -> dict[str, object] | None:
        with self._connection.cursor() as cursor:
            cursor.execute(SELECT_BY_ID_SQL, (request_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            column_names = _column_names(cursor.description)
        return _row_to_dict(row, column_names)

    def list_recent(self, *, limit: int = 50) -> list[dict[str, object]]:
        bounded_limit = max(1, min(int(limit), 500))
        with self._connection.cursor() as cursor:
            cursor.execute(SELECT_RECENT_SQL, (bounded_limit,))
            rows = cursor.fetchall()
            column_names = _column_names(cursor.description)
        return [_row_to_dict(row, column_names) for row in rows]


def _column_names(description: object) -> tuple[str, ...]:
    return tuple(_column_name(item) for item in description or ())


def _column_name(item: object) -> str:
    name = getattr(item, "name", None)
    if name is not None:
        return str(name)
    return str(item[0])  # type: ignore[index]


def _row_to_dict(row: object, column_names: tuple[str, ...]) -> dict[str, object]:
    if isinstance(row, Mapping):
        data = dict(row)
    else:
        data = dict(zip(column_names, row, strict=True))  # type: ignore[arg-type]
    for json_field in ("cost_assumptions", "pipeline_inputs"):
        value = data.get(json_field)
        if isinstance(value, str):
            try:
                data[json_field] = json.loads(value)
            except json.JSONDecodeError:
                data[json_field] = {}
    for ts_field in ("as_of", "lease_expires_at", "created_at", "updated_at"):
        ts_value = data.get(ts_field)
        if isinstance(ts_value, datetime):
            data[ts_field] = ts_value.isoformat()
    return data


__all__ = ["BacktestRequestRepository"]
