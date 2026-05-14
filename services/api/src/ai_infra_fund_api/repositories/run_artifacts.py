from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Protocol, TypeVar
from urllib.parse import parse_qsl, urlsplit

from ai_infra_fund_core.contracts.common import require_text
from ai_infra_fund_core.contracts.evaluation import RunArtifact


class Cursor(Protocol):
    description: object

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...

    def fetchone(self) -> object | None:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...

    def commit(self) -> None:
        ...


RunArtifactT = TypeVar("RunArtifactT")

RUN_ARTIFACT_STATUSES = frozenset({"pending", "running", "succeeded", "failed", "cancelled"})
DEFAULT_RUN_TYPE = "advisory_demo"
ALL_RUN_TYPES = "all"
TRACEABILITY_KEYS = frozenset(
    {
        "recommendation_id",
        "audit_id",
        "evaluation_id",
        "backtest_run_id",
        "advisory_label",
    }
)
RUN_ARTIFACT_COLUMNS = (
    "run_id",
    "run_type",
    "started_at",
    "completed_at",
    "inputs_hash",
    "output_hash",
    "artifact_uri",
    "status",
    "error_summary",
    "created_at",
)


UPSERT_RUN_ARTIFACT_SQL = """
INSERT INTO audit.run_artifacts (
    run_id,
    run_type,
    started_at,
    completed_at,
    inputs_hash,
    output_hash,
    artifact_uri,
    status,
    error_summary,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (run_id) DO UPDATE SET
    run_type = EXCLUDED.run_type,
    started_at = EXCLUDED.started_at,
    completed_at = EXCLUDED.completed_at,
    inputs_hash = EXCLUDED.inputs_hash,
    output_hash = EXCLUDED.output_hash,
    artifact_uri = EXCLUDED.artifact_uri,
    status = EXCLUDED.status,
    error_summary = EXCLUDED.error_summary,
    created_at = EXCLUDED.created_at;
"""


SELECT_RUN_ARTIFACT_BY_ID_SQL = """
SELECT
    run_id,
    run_type,
    started_at,
    completed_at,
    inputs_hash,
    output_hash,
    artifact_uri,
    status,
    error_summary,
    created_at
FROM audit.run_artifacts
WHERE run_id = %s
LIMIT 1;
"""


SELECT_LATEST_RUN_ARTIFACT_SQL = """
SELECT
    run_id,
    run_type,
    started_at,
    completed_at,
    inputs_hash,
    output_hash,
    artifact_uri,
    status,
    error_summary,
    created_at
FROM audit.run_artifacts
WHERE run_type = %s
ORDER BY started_at DESC, created_at DESC, run_id DESC
LIMIT 1;
"""


SELECT_LATEST_RUN_ARTIFACT_ANY_TYPE_SQL = """
SELECT
    run_id,
    run_type,
    started_at,
    completed_at,
    inputs_hash,
    output_hash,
    artifact_uri,
    status,
    error_summary,
    created_at
FROM audit.run_artifacts
ORDER BY started_at DESC, created_at DESC, run_id DESC
LIMIT 1;
"""


class RunArtifactRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def save(self, artifact: RunArtifactT) -> RunArtifactT:
        params = _run_artifact_params(artifact)
        with self._connection.cursor() as cursor:
            cursor.execute(UPSERT_RUN_ARTIFACT_SQL, params)
        self._connection.commit()
        return artifact

    def get_latest(self, run_type: str | None = DEFAULT_RUN_TYPE) -> dict[str, object] | None:
        statement, params = _latest_query(run_type)
        with self._connection.cursor() as cursor:
            cursor.execute(statement, params)
            row = cursor.fetchone()
            if row is None:
                return None
            column_names = _column_names(cursor.description)
        return _artifact_payload(_row_to_dict(row, column_names))

    def get_by_id(self, run_id: str) -> dict[str, object] | None:
        normalized_id = require_text(run_id, "run_id")
        with self._connection.cursor() as cursor:
            cursor.execute(SELECT_RUN_ARTIFACT_BY_ID_SQL, (normalized_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            column_names = _column_names(cursor.description)
        return _artifact_payload(_row_to_dict(row, column_names))


def _run_artifact_params(artifact: object) -> tuple[object, ...]:
    normalized = _normalize_run_artifact(artifact)
    if normalized.status not in RUN_ARTIFACT_STATUSES:
        allowed = sorted(RUN_ARTIFACT_STATUSES)
        raise ValueError(f"status must be one of {allowed}")
    return (
        normalized.run_id,
        normalized.run_type,
        normalized.started_at,
        normalized.completed_at,
        normalized.inputs_hash,
        normalized.output_hash,
        normalized.artifact_uri,
        normalized.status,
        normalized.error_summary,
        normalized.created_at,
    )


def _normalize_run_artifact(artifact: object) -> RunArtifact:
    if isinstance(artifact, RunArtifact):
        return artifact
    return RunArtifact(
        run_id=getattr(artifact, "run_id", None),
        run_type=getattr(artifact, "run_type", None),
        started_at=getattr(artifact, "started_at", None),
        completed_at=getattr(artifact, "completed_at", None),
        inputs_hash=getattr(artifact, "inputs_hash", None),
        output_hash=getattr(artifact, "output_hash", None),
        artifact_uri=getattr(artifact, "artifact_uri", None),
        status=getattr(artifact, "status", None),
        error_summary=getattr(artifact, "error_summary", None),
        created_at=getattr(artifact, "created_at", None),
    )


def _latest_query(run_type: str | None) -> tuple[str, tuple[object, ...]]:
    if run_type is None:
        return SELECT_LATEST_RUN_ARTIFACT_ANY_TYPE_SQL, ()

    normalized_type = require_text(run_type, "run_type")
    if normalized_type == ALL_RUN_TYPES:
        return SELECT_LATEST_RUN_ARTIFACT_ANY_TYPE_SQL, ()
    return SELECT_LATEST_RUN_ARTIFACT_SQL, (normalized_type,)


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


def _artifact_payload(row: Mapping[str, object]) -> dict[str, object]:
    artifact = {column: _json_safe(row[column]) for column in RUN_ARTIFACT_COLUMNS}
    artifact["traceability"] = _traceability_from_uri(row.get("artifact_uri"))
    return artifact


def _json_safe(value: object) -> object:
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def _traceability_from_uri(artifact_uri: object) -> dict[str, str]:
    if not isinstance(artifact_uri, str) or not artifact_uri:
        return {}

    try:
        query_pairs = parse_qsl(
            urlsplit(artifact_uri).query,
            keep_blank_values=False,
            strict_parsing=False,
            max_num_fields=20,
        )
    except ValueError:
        return {}

    traceability: dict[str, str] = {}
    for key, value in query_pairs:
        if key in TRACEABILITY_KEYS and key not in traceability:
            traceability[key] = value
    return traceability


__all__ = ["RunArtifactRepository"]
