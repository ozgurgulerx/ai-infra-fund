from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Protocol, TypeVar

from ai_infra_fund_core.contracts.common import canonicalize, require_text
from ai_infra_fund_core.contracts.recommendations import (
    RecommendationArtifact,
    RecommendationAudit,
)


class Cursor(Protocol):
    description: object

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...

    def fetchall(self) -> list[object]:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...

    def commit(self) -> None:
        ...


RecommendationArtifactT = TypeVar("RecommendationArtifactT")
RecommendationAuditT = TypeVar("RecommendationAuditT")


INSERT_RECOMMENDATION_ARTIFACT_SQL = """
INSERT INTO recommendations.recommendation_artifacts (
    recommendation_id,
    ticker_or_portfolio,
    advisory_label,
    action,
    horizon,
    score_breakdown_json,
    target_weights_id,
    signal_bundle_id,
    evidence_ids,
    model_run_ids,
    risks_json,
    contradictions_json,
    final_payload_json,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s
);
"""


INSERT_RECOMMENDATION_AUDIT_SQL = """
INSERT INTO recommendations.recommendation_audits (
    audit_id,
    recommendation_id,
    target_weights_id,
    signal_bundle_id,
    evidence_ids,
    model_run_ids,
    deterministic_checks_json,
    reviewer_findings_json,
    schema_valid,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s
);
"""


SELECT_RECOMMENDATION_WITH_AUDITS_SQL = """
SELECT
    artifact.recommendation_id,
    artifact.ticker_or_portfolio,
    artifact.advisory_label,
    artifact.action,
    artifact.horizon,
    artifact.score_breakdown_json,
    artifact.target_weights_id,
    artifact.signal_bundle_id,
    artifact.evidence_ids,
    artifact.model_run_ids,
    artifact.risks_json,
    artifact.contradictions_json,
    artifact.final_payload_json,
    artifact.created_at,
    audit.audit_id,
    audit.recommendation_id AS audit_recommendation_id,
    audit.target_weights_id AS audit_target_weights_id,
    audit.signal_bundle_id AS audit_signal_bundle_id,
    audit.evidence_ids AS audit_evidence_ids,
    audit.model_run_ids AS audit_model_run_ids,
    audit.deterministic_checks_json,
    audit.reviewer_findings_json,
    audit.schema_valid,
    audit.created_at AS audit_created_at
FROM recommendations.recommendation_artifacts AS artifact
LEFT JOIN recommendations.recommendation_audits AS audit
    ON audit.recommendation_id = artifact.recommendation_id
WHERE artifact.recommendation_id = %s
ORDER BY audit.created_at ASC, audit.audit_id ASC;
"""


class RecommendationRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def save_artifact(self, artifact: RecommendationArtifactT) -> RecommendationArtifactT:
        params = _artifact_params(artifact)
        with self._connection.cursor() as cursor:
            cursor.execute(INSERT_RECOMMENDATION_ARTIFACT_SQL, params)
        self._connection.commit()
        return artifact

    def save_audit(self, audit: RecommendationAuditT) -> RecommendationAuditT:
        params = _audit_params(audit)
        with self._connection.cursor() as cursor:
            cursor.execute(INSERT_RECOMMENDATION_AUDIT_SQL, params)
        self._connection.commit()
        return audit

    def get_artifact_with_audits(self, recommendation_id: str) -> dict[str, object] | None:
        normalized_id = require_text(recommendation_id, "recommendation_id")
        with self._connection.cursor() as cursor:
            cursor.execute(SELECT_RECOMMENDATION_WITH_AUDITS_SQL, (normalized_id,))
            rows = cursor.fetchall()
            if not rows:
                return None
            column_names = _column_names(cursor.description)

        row_dicts = [_row_to_dict(row, column_names) for row in rows]
        return _artifact_with_audits(row_dicts)


def _artifact_params(artifact: object) -> tuple[object, ...]:
    normalized = _normalize_artifact(artifact)
    return (
        normalized.recommendation_id,
        normalized.ticker_or_portfolio,
        normalized.advisory_label.value,
        normalized.action.value,
        normalized.horizon,
        _json_param(normalized.score_breakdown),
        normalized.target_weights_id,
        normalized.signal_bundle_id,
        list(normalized.evidence_ids),
        list(normalized.model_run_ids),
        _json_param(list(normalized.risks)),
        _json_param(list(normalized.contradictions)),
        _json_param(normalized.final_payload),
        normalized.created_at,
    )


def _audit_params(audit: object) -> tuple[object, ...]:
    normalized = _normalize_audit(audit)
    return (
        normalized.audit_id,
        normalized.recommendation_id,
        normalized.target_weights_id,
        normalized.signal_bundle_id,
        list(normalized.evidence_ids),
        list(normalized.model_run_ids),
        _json_param(normalized.deterministic_checks),
        _json_param(normalized.reviewer_findings),
        normalized.schema_valid,
        normalized.created_at,
    )


def _normalize_artifact(artifact: object) -> RecommendationArtifact:
    if isinstance(artifact, RecommendationArtifact):
        return artifact
    return RecommendationArtifact(
        recommendation_id=getattr(artifact, "recommendation_id", None),
        ticker_or_portfolio=getattr(artifact, "ticker_or_portfolio", None),
        advisory_label=getattr(artifact, "advisory_label", None),
        action=getattr(artifact, "action", None),
        horizon=getattr(artifact, "horizon", None),
        score_breakdown=getattr(artifact, "score_breakdown", None),
        target_weights_id=getattr(artifact, "target_weights_id", None),
        evidence_ids=getattr(artifact, "evidence_ids", None),
        model_run_ids=getattr(artifact, "model_run_ids", None),
        signal_bundle_id=getattr(artifact, "signal_bundle_id", None),
        risks=getattr(artifact, "risks", None),
        contradictions=getattr(artifact, "contradictions", None),
        final_payload=getattr(artifact, "final_payload", None),
        created_at=getattr(artifact, "created_at", None),
    )


def _normalize_audit(audit: object) -> RecommendationAudit:
    if isinstance(audit, RecommendationAudit):
        return audit
    return RecommendationAudit(
        audit_id=getattr(audit, "audit_id", None),
        recommendation_id=getattr(audit, "recommendation_id", None),
        target_weights_id=getattr(audit, "target_weights_id", None),
        signal_bundle_id=getattr(audit, "signal_bundle_id", None),
        evidence_ids=getattr(audit, "evidence_ids", None),
        model_run_ids=getattr(audit, "model_run_ids", None),
        deterministic_checks=getattr(audit, "deterministic_checks", None),
        reviewer_findings=getattr(audit, "reviewer_findings", None),
        schema_valid=getattr(audit, "schema_valid", None),
        created_at=getattr(audit, "created_at", None),
    )


def _json_param(value: object) -> str | None:
    if value is None:
        return None
    return json.dumps(canonicalize(value), sort_keys=True, separators=(",", ":"))


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


def _artifact_with_audits(rows: list[dict[str, object]]) -> dict[str, object]:
    first = rows[0]
    artifact: dict[str, object] = {
        "recommendation_id": first["recommendation_id"],
        "ticker_or_portfolio": first["ticker_or_portfolio"],
        "advisory_label": first["advisory_label"],
        "action": first["action"],
        "horizon": first["horizon"],
        "score_breakdown": _json_value(first["score_breakdown_json"]),
        "target_weights_id": first["target_weights_id"],
        "signal_bundle_id": first["signal_bundle_id"],
        "evidence_ids": first["evidence_ids"],
        "model_run_ids": first["model_run_ids"],
        "risks": _json_value(first["risks_json"]),
        "contradictions": _json_value(first["contradictions_json"]),
        "final_payload": _json_value(first["final_payload_json"]),
        "created_at": first["created_at"],
        "audits": [],
    }

    audits = artifact["audits"]
    if not isinstance(audits, list):
        raise TypeError("audits must be a list")

    for row in rows:
        if row["audit_id"] is None:
            continue
        audits.append(
            {
                "audit_id": row["audit_id"],
                "recommendation_id": row["audit_recommendation_id"],
                "target_weights_id": row["audit_target_weights_id"],
                "signal_bundle_id": row["audit_signal_bundle_id"],
                "evidence_ids": row["audit_evidence_ids"],
                "model_run_ids": row["audit_model_run_ids"],
                "deterministic_checks": _json_value(row["deterministic_checks_json"]),
                "reviewer_findings": _json_value(row["reviewer_findings_json"]),
                "schema_valid": row["schema_valid"],
                "created_at": row["audit_created_at"],
            }
        )

    return artifact


def _json_value(value: object) -> object:
    if isinstance(value, str):
        return json.loads(value)
    return value


__all__ = ["RecommendationRepository"]
