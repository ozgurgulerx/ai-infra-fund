from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol


class Cursor(Protocol):
    description: object

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...

    def fetchall(self) -> list[object]:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...


EVIDENCE_SUMMARY_SQL = """
WITH item_counts AS (
    SELECT COUNT(*) AS total_items
    FROM evidence.evidence_items
),
chunk_counts AS (
    SELECT COUNT(*) AS total_chunks
    FROM evidence.evidence_chunks
),
claim_counts AS (
    SELECT COUNT(*) AS total_claims
    FROM evidence.evidence_claims
),
items_by_data_class AS (
    SELECT COALESCE(jsonb_object_agg(data_class, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT data_class, COUNT(*) AS total_count
        FROM evidence.evidence_items
        GROUP BY data_class
    ) AS grouped_items
),
created_rows AS (
    SELECT created_at FROM evidence.evidence_items
    UNION ALL
    SELECT created_at FROM evidence.evidence_chunks
    UNION ALL
    SELECT created_at FROM evidence.evidence_claims
)
SELECT
    item_counts.total_items,
    chunk_counts.total_chunks,
    claim_counts.total_claims,
    items_by_data_class.counts AS items_by_data_class,
    (SELECT MAX(ingested_at) FROM evidence.evidence_items) AS latest_ingested_at,
    (SELECT MAX(created_at) FROM created_rows) AS latest_created_at
FROM item_counts, chunk_counts, claim_counts, items_by_data_class;
"""


RECOMMENDATION_SUMMARY_SQL = """
WITH artifact_counts AS (
    SELECT COUNT(*) AS total_recommendations
    FROM recommendations.recommendation_artifacts
),
audit_counts AS (
    SELECT
        COUNT(*) AS total_audits,
        COUNT(*) FILTER (WHERE schema_valid IS TRUE) AS schema_valid_audits,
        COUNT(*) FILTER (WHERE schema_valid IS FALSE) AS schema_invalid_audits
    FROM recommendations.recommendation_audits
),
created_rows AS (
    SELECT created_at FROM recommendations.recommendation_artifacts
    UNION ALL
    SELECT created_at FROM recommendations.recommendation_audits
)
SELECT
    artifact_counts.total_recommendations,
    audit_counts.total_audits,
    audit_counts.schema_valid_audits,
    audit_counts.schema_invalid_audits,
    (SELECT MAX(created_at) FROM created_rows) AS latest_created_at
FROM artifact_counts, audit_counts;
"""


MODEL_RUN_SUMMARY_SQL = """
WITH run_counts AS (
    SELECT COUNT(*) AS total_model_runs
    FROM audit.model_runs
),
runs_by_status AS (
    SELECT COALESCE(jsonb_object_agg(status, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT status, COUNT(*) AS total_count
        FROM audit.model_runs
        GROUP BY status
    ) AS grouped_runs
)
SELECT
    run_counts.total_model_runs,
    runs_by_status.counts AS runs_by_status,
    (SELECT MAX(created_at) FROM audit.model_runs) AS latest_created_at
FROM run_counts, runs_by_status;
"""


EVALUATION_SUMMARY_SQL = """
WITH backtest_counts AS (
    SELECT COUNT(*) AS total_backtest_runs
    FROM audit.backtest_runs
),
backtest_runs_by_status AS (
    SELECT COALESCE(jsonb_object_agg(status, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT status, COUNT(*) AS total_count
        FROM audit.backtest_runs
        GROUP BY status
    ) AS grouped_backtests
),
artifact_counts AS (
    SELECT COUNT(*) AS total_run_artifacts
    FROM audit.run_artifacts
),
run_artifacts_by_status AS (
    SELECT COALESCE(jsonb_object_agg(status, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT status, COUNT(*) AS total_count
        FROM audit.run_artifacts
        GROUP BY status
    ) AS grouped_artifacts
),
created_rows AS (
    SELECT created_at FROM audit.backtest_runs
    UNION ALL
    SELECT created_at FROM audit.run_artifacts
)
SELECT
    backtest_counts.total_backtest_runs,
    backtest_runs_by_status.counts AS backtest_runs_by_status,
    artifact_counts.total_run_artifacts,
    run_artifacts_by_status.counts AS run_artifacts_by_status,
    (SELECT MAX(created_at) FROM created_rows) AS latest_created_at
FROM backtest_counts, backtest_runs_by_status, artifact_counts, run_artifacts_by_status;
"""


DATA_QUALITY_SUMMARY_SQL = """
WITH check_counts AS (
    SELECT COUNT(*) AS total_checks
    FROM governance.data_quality_checks
),
checks_by_status AS (
    SELECT COALESCE(jsonb_object_agg(status, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT status, COUNT(*) AS total_count
        FROM governance.data_quality_checks
        GROUP BY status
    ) AS grouped_statuses
),
checks_by_severity AS (
    SELECT COALESCE(jsonb_object_agg(severity, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT severity, COUNT(*) AS total_count
        FROM governance.data_quality_checks
        GROUP BY severity
    ) AS grouped_severities
)
SELECT
    check_counts.total_checks,
    checks_by_status.counts AS checks_by_status,
    checks_by_severity.counts AS checks_by_severity,
    (SELECT MAX(checked_at) FROM governance.data_quality_checks) AS latest_checked_at,
    (SELECT MAX(created_at) FROM governance.data_quality_checks) AS latest_created_at
FROM check_counts, checks_by_status, checks_by_severity;
"""


INCIDENT_SUMMARY_SQL = """
WITH incident_counts AS (
    SELECT
        COUNT(*) AS total_incidents,
        COUNT(*) FILTER (WHERE resolved_at IS NULL) AS open_incidents
    FROM governance.incident_records
),
incidents_by_severity AS (
    SELECT COALESCE(jsonb_object_agg(severity, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT severity, COUNT(*) AS total_count
        FROM governance.incident_records
        GROUP BY severity
    ) AS grouped_severities
),
incidents_by_freeze_status AS (
    SELECT COALESCE(jsonb_object_agg(freeze_status, total_count), '{}'::jsonb) AS counts
    FROM (
        SELECT freeze_status, COUNT(*) AS total_count
        FROM governance.incident_records
        GROUP BY freeze_status
    ) AS grouped_freeze_statuses
)
SELECT
    incident_counts.total_incidents,
    incidents_by_severity.counts AS incidents_by_severity,
    incidents_by_freeze_status.counts AS incidents_by_freeze_status,
    incident_counts.open_incidents,
    (SELECT MAX(created_at) FROM governance.incident_records) AS latest_created_at
FROM incident_counts, incidents_by_severity, incidents_by_freeze_status;
"""


class DashboardRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get_status_overview(self) -> dict[str, object]:
        return self.overview()

    def get_status_modules(self) -> dict[str, object]:
        evidence = self.evidence_summary()
        recommendations = self.recommendation_summary()
        model_runs = self.model_run_summary()
        evaluations = self.evaluation_summary()
        data_quality = self.data_quality_summary()
        incidents = self.incident_summary()
        return {
            "modules": [
                _module_summary(
                    "data-plane",
                    status="available",
                    source_label="PostgreSQL dashboard repository",
                    detail="Dashboard summary queries reached the canonical PostgreSQL data spine.",
                    visible_value="DB summaries available",
                ),
                _module_summary(
                    "evidence-plane",
                    status=str(evidence.get("status", "empty")),
                    source_label="PostgreSQL evidence summary",
                    detail=(
                        f"{_int(evidence.get('total_items'))} items, "
                        f"{_int(evidence.get('total_chunks'))} chunks, "
                        f"{_int(evidence.get('total_claims'))} claims."
                    ),
                    visible_value=f"{_int(evidence.get('total_items'))} evidence items",
                ),
                _module_summary(
                    "recommendation-artifacts",
                    status=str(recommendations.get("status", "empty")),
                    source_label="PostgreSQL recommendation summary",
                    detail=(
                        f"{_int(recommendations.get('total_recommendations'))} artifacts, "
                        f"{_int(recommendations.get('total_audits'))} audits."
                    ),
                    visible_value=f"{_int(recommendations.get('total_recommendations'))} artifacts",
                ),
                _module_summary(
                    "model-router",
                    status=str(model_runs.get("status", "empty")),
                    source_label="PostgreSQL ModelRun summary",
                    detail=f"{_int(model_runs.get('total_model_runs'))} audited model runs.",
                    visible_value=f"{_int(model_runs.get('total_model_runs'))} model runs",
                ),
                _module_summary(
                    "evaluation-harness",
                    status=str(evaluations.get("status", "empty")),
                    source_label="PostgreSQL evaluation summary",
                    detail=(
                        f"{_int(evaluations.get('total_backtest_runs'))} backtests, "
                        f"{_int(evaluations.get('total_run_artifacts'))} run artifacts."
                    ),
                    visible_value=f"{_int(evaluations.get('total_backtest_runs'))} backtests",
                ),
                _module_summary(
                    "data-quality",
                    status=str(data_quality.get("status", "empty")),
                    source_label="PostgreSQL data-quality summary",
                    detail=f"{_int(data_quality.get('total_checks'))} data-quality checks.",
                    visible_value=f"{_int(data_quality.get('total_checks'))} checks",
                ),
                _module_summary(
                    "incidents",
                    status=str(incidents.get("status", "empty")),
                    source_label="PostgreSQL incident summary",
                    detail=(
                        f"{_int(incidents.get('open_incidents'))} open incidents, "
                        f"{_int(incidents.get('total_incidents'))} total."
                    ),
                    visible_value=f"{_int(incidents.get('open_incidents'))} open incidents",
                ),
            ]
        }

    def get_evidence_summary(self) -> dict[str, object]:
        return self.evidence_summary()

    def get_recommendation_summary(self) -> dict[str, object]:
        return self.recommendation_summary()

    def get_evaluation_summary(self) -> dict[str, object]:
        return self.evaluation_summary()

    def get_model_run_summary(self) -> dict[str, object]:
        return self.model_run_summary()

    def get_data_quality_summary(self) -> dict[str, object]:
        return self.data_quality_summary()

    def get_incident_summary(self) -> dict[str, object]:
        return self.incident_summary()

    def evidence_summary(self) -> dict[str, object]:
        row = self._fetch_one(EVIDENCE_SUMMARY_SQL)
        total_items = _int(row.get("total_items"))
        total_chunks = _int(row.get("total_chunks"))
        total_claims = _int(row.get("total_claims"))
        return {
            "status": _status(total_items + total_chunks + total_claims),
            "total_items": total_items,
            "total_chunks": total_chunks,
            "total_claims": total_claims,
            "items_by_data_class": _count_map(row.get("items_by_data_class")),
            "latest_ingested_at": _iso_or_none(row.get("latest_ingested_at")),
            "latest_created_at": _iso_or_none(row.get("latest_created_at")),
        }

    def recommendation_summary(self) -> dict[str, object]:
        row = self._fetch_one(RECOMMENDATION_SUMMARY_SQL)
        total_recommendations = _int(row.get("total_recommendations"))
        total_audits = _int(row.get("total_audits"))
        return {
            "status": _status(total_recommendations + total_audits),
            "total_recommendations": total_recommendations,
            "total_audits": total_audits,
            "schema_valid_audits": _int(row.get("schema_valid_audits")),
            "schema_invalid_audits": _int(row.get("schema_invalid_audits")),
            "latest_created_at": _iso_or_none(row.get("latest_created_at")),
        }

    def model_run_summary(self) -> dict[str, object]:
        row = self._fetch_one(MODEL_RUN_SUMMARY_SQL)
        total_model_runs = _int(row.get("total_model_runs"))
        return {
            "status": _status(total_model_runs),
            "total_model_runs": total_model_runs,
            "runs_by_status": _count_map(row.get("runs_by_status")),
            "latest_created_at": _iso_or_none(row.get("latest_created_at")),
        }

    def evaluation_summary(self) -> dict[str, object]:
        row = self._fetch_one(EVALUATION_SUMMARY_SQL)
        total_backtest_runs = _int(row.get("total_backtest_runs"))
        total_run_artifacts = _int(row.get("total_run_artifacts"))
        return {
            "status": _status(total_backtest_runs + total_run_artifacts),
            "total_backtest_runs": total_backtest_runs,
            "backtest_runs_by_status": _count_map(row.get("backtest_runs_by_status")),
            "total_run_artifacts": total_run_artifacts,
            "run_artifacts_by_status": _count_map(row.get("run_artifacts_by_status")),
            "latest_created_at": _iso_or_none(row.get("latest_created_at")),
        }

    def data_quality_summary(self) -> dict[str, object]:
        row = self._fetch_one(DATA_QUALITY_SUMMARY_SQL)
        total_checks = _int(row.get("total_checks"))
        return {
            "status": _status(total_checks),
            "total_checks": total_checks,
            "checks_by_status": _count_map(row.get("checks_by_status")),
            "checks_by_severity": _count_map(row.get("checks_by_severity")),
            "latest_checked_at": _iso_or_none(row.get("latest_checked_at")),
            "latest_created_at": _iso_or_none(row.get("latest_created_at")),
        }

    def incident_summary(self) -> dict[str, object]:
        row = self._fetch_one(INCIDENT_SUMMARY_SQL)
        total_incidents = _int(row.get("total_incidents"))
        open_incidents = _int(row.get("open_incidents"))
        return {
            "status": "degraded" if open_incidents > 0 else _status(total_incidents),
            "total_incidents": total_incidents,
            "incidents_by_severity": _count_map(row.get("incidents_by_severity")),
            "incidents_by_freeze_status": _count_map(row.get("incidents_by_freeze_status")),
            "open_incidents": open_incidents,
            "latest_created_at": _iso_or_none(row.get("latest_created_at")),
        }

    def overview(self) -> dict[str, object]:
        evidence = self.evidence_summary()
        recommendations = self.recommendation_summary()
        model_runs = self.model_run_summary()
        evaluations = self.evaluation_summary()
        data_quality = self.data_quality_summary()
        incidents = self.incident_summary()
        sections = (evidence, recommendations, model_runs, evaluations, data_quality, incidents)
        return {
            "status": _overview_status(sections),
            "evidence": evidence,
            "recommendations": recommendations,
            "model_runs": model_runs,
            "evaluations": evaluations,
            "data_quality": data_quality,
            "incidents": incidents,
        }

    def _fetch_one(self, statement: str) -> dict[str, object]:
        with self._connection.cursor() as cursor:
            cursor.execute(statement, ())
            rows = cursor.fetchall()
            column_names = _column_names(cursor.description)
        if not rows:
            return {}
        return _row_to_dict(rows[0], column_names)


def _overview_status(sections: tuple[dict[str, object], ...]) -> str:
    statuses = tuple(str(section.get("status", "empty")) for section in sections)
    if "degraded" in statuses:
        return "degraded"
    if any(status == "available" for status in statuses):
        return "available"
    return "empty"


def _module_summary(
    module_id: str,
    *,
    status: str,
    source_label: str,
    detail: str,
    visible_value: str,
) -> dict[str, object]:
    return {
        "id": module_id,
        "status": status,
        "source_type": "run_artifact",
        "source_label": source_label,
        "detail": detail,
        "visible_value": visible_value,
    }


def _status(total_count: int) -> str:
    if total_count <= 0:
        return "empty"
    return "available"


def _int(value: object) -> int:
    if value is None:
        return 0
    return int(value)


def _count_map(value: object) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): _int(count) for key, count in value.items() if key is not None}


def _iso_or_none(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


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


__all__ = ["DashboardRepository"]
