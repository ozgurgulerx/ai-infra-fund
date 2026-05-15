from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Protocol


class Cursor(Protocol):
    description: object

    def execute(
        self, statement: str, params: tuple[object, ...] | None = None
    ) -> None: ...

    def fetchall(self) -> list[tuple[object, ...]]: ...


class Connection(Protocol):
    def cursor(self) -> object: ...

    def commit(self) -> None: ...


EVENT_COLUMNS: tuple[str, ...] = (
    "event_id",
    "kind",
    "run_id",
    "severity",
    "payload",
    "occurred_at",
    "created_at",
)


INSERT_EVENT_SQL = """
INSERT INTO audit.experiment_events (
    event_id,
    kind,
    run_id,
    severity,
    payload,
    occurred_at,
    created_at
) VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (event_id) DO NOTHING;
"""


SELECT_RECENT_SQL = """
SELECT event_id, kind, run_id, severity, payload, occurred_at, created_at
FROM audit.experiment_events
ORDER BY occurred_at DESC, created_at DESC, event_id DESC
LIMIT %s;
"""


SELECT_RECENT_SINCE_SQL = """
SELECT event_id, kind, run_id, severity, payload, occurred_at, created_at
FROM audit.experiment_events
WHERE occurred_at >= %s
ORDER BY occurred_at DESC, created_at DESC, event_id DESC
LIMIT %s;
"""


SELECT_FOR_RUN_SQL = """
SELECT event_id, kind, run_id, severity, payload, occurred_at, created_at
FROM audit.experiment_events
WHERE run_id = %s
ORDER BY occurred_at DESC, created_at DESC, event_id DESC
LIMIT %s;
"""


class ExperimentEventRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def record(self, event: object) -> None:
        params = _event_params(event)
        with self._connection.cursor() as cursor:
            cursor.execute(INSERT_EVENT_SQL, params)
        self._connection.commit()

    def list_recent(
        self,
        *,
        limit: int = 50,
        since: datetime | None = None,
    ) -> list[dict[str, object]]:
        bounded_limit = max(1, min(int(limit), 500))
        with self._connection.cursor() as cursor:
            if since is None:
                cursor.execute(SELECT_RECENT_SQL, (bounded_limit,))
            else:
                cursor.execute(SELECT_RECENT_SINCE_SQL, (since, bounded_limit))
            rows = cursor.fetchall()
            column_names = _column_names(cursor.description)
        return [_row_to_event_dict(row, column_names) for row in rows]

    def list_for_run(self, run_id: str, *, limit: int = 200) -> list[dict[str, object]]:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id is required")
        bounded_limit = max(1, min(int(limit), 500))
        with self._connection.cursor() as cursor:
            cursor.execute(SELECT_FOR_RUN_SQL, (run_id.strip(), bounded_limit))
            rows = cursor.fetchall()
            column_names = _column_names(cursor.description)
        return [_row_to_event_dict(row, column_names) for row in rows]


def _event_params(event: object) -> tuple[object, ...]:
    event_id = getattr(event, "event_id")
    kind = getattr(event, "kind")
    run_id = getattr(event, "run_id")
    severity = getattr(event, "severity")
    payload = getattr(event, "payload")
    occurred_at = getattr(event, "occurred_at")
    created_at = getattr(event, "created_at", None) or occurred_at

    payload_dict = dict(payload) if isinstance(payload, Mapping) else {}
    payload_json = json.dumps(payload_dict, sort_keys=True, separators=(",", ":"))

    return (
        event_id,
        kind,
        run_id,
        severity,
        payload_json,
        occurred_at,
        created_at,
    )


def _column_names(description: object) -> tuple[str, ...]:
    return tuple(_column_name(item) for item in description or ())


def _column_name(item: object) -> str:
    name = getattr(item, "name", None)
    if name is not None:
        return str(name)
    return str(item[0])  # type: ignore[index]


def _row_to_event_dict(row: object, column_names: tuple[str, ...]) -> dict[str, object]:
    if isinstance(row, Mapping):
        data = dict(row)
    else:
        data = dict(zip(column_names, row, strict=True))  # type: ignore[arg-type]

    payload_value = data.get("payload")
    if isinstance(payload_value, str):
        try:
            data["payload"] = json.loads(payload_value)
        except json.JSONDecodeError:
            data["payload"] = {}
    occurred = data.get("occurred_at")
    if isinstance(occurred, datetime):
        data["occurred_at"] = occurred.isoformat()
    created = data.get("created_at")
    if isinstance(created, datetime):
        data["created_at"] = created.isoformat()
    return data


__all__ = ["ExperimentEventRepository"]
