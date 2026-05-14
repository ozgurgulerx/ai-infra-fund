from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from typing import Protocol
from urllib.parse import urlencode

from ai_infra_fund_core.runtime.config import RuntimeConfigError, RuntimeSettings


RUN_TYPE = "advisory_demo"
DEMO_EVIDENCE_ID = "evidence-demo-ai-infra-nvda"
DEMO_CLAIM_ID = "claim-demo-ai-infra-nvda-demand"
DEMO_SIGNAL_BUNDLE_ID = "signal-bundle-demo-nvda"
DEMO_TARGET_WEIGHTS_ID = "target-weights-demo-ai-infra"
DEMO_RECOMMENDATION_ID = "recommendation-demo-nvda"
DEMO_AUDIT_ID = "recommendation-audit-demo-nvda"
DEMO_BACKTEST_RUN_ID = "evaluation-demo-ai-infra"
DEMO_RUN_AT = datetime(2026, 5, 14, 12, 5, tzinfo=timezone.utc)

EXPECTED_IDS = (
    DEMO_EVIDENCE_ID,
    DEMO_CLAIM_ID,
    DEMO_SIGNAL_BUNDLE_ID,
    DEMO_TARGET_WEIGHTS_ID,
    DEMO_RECOMMENDATION_ID,
    DEMO_AUDIT_ID,
    DEMO_BACKTEST_RUN_ID,
)


class Cursor(Protocol):
    description: object

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...

    def fetchone(self) -> object:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...

    def commit(self) -> None:
        ...


SELECT_PREREQUISITES_SQL = """
WITH expected AS (
    SELECT
        %s::text AS evidence_id,
        %s::text AS claim_id,
        %s::text AS signal_bundle_id,
        %s::text AS target_weights_id,
        %s::text AS recommendation_id,
        %s::text AS audit_id,
        %s::text AS backtest_run_id
)
SELECT
    evidence_item.evidence_id,
    evidence_item.content_hash AS evidence_content_hash,
    evidence_claim.claim_id,
    evidence_claim.extracted_by_model_run_id,
    signal_bundle.signal_bundle_id,
    signal_bundle.input_snapshot_hash AS signal_input_snapshot_hash,
    target_weights.target_weights_id,
    target_weights.generated_by AS target_weights_generated_by,
    target_weights.validation_status AS target_weights_validation_status,
    recommendation.recommendation_id,
    recommendation.advisory_label,
    recommendation.evidence_ids AS recommendation_evidence_ids,
    recommendation.model_run_ids AS recommendation_model_run_ids,
    recommendation.score_breakdown_json AS recommendation_score_breakdown,
    recommendation.final_payload_json AS recommendation_final_payload,
    recommendation_audit.audit_id,
    recommendation_audit.schema_valid AS audit_schema_valid,
    recommendation_audit.deterministic_checks_json AS audit_deterministic_checks,
    backtest.backtest_run_id,
    backtest.status AS backtest_status,
    backtest.summary_metrics_json AS backtest_summary_metrics,
    evaluation_run_artifact.run_id AS evaluation_run_artifact_id,
    evaluation_run_artifact.status AS evaluation_run_status,
    evaluation_run_artifact.inputs_hash AS evaluation_inputs_hash,
    evaluation_run_artifact.output_hash AS evaluation_output_hash
FROM expected
LEFT JOIN evidence.evidence_items AS evidence_item
    ON evidence_item.evidence_id = expected.evidence_id
LEFT JOIN evidence.evidence_claims AS evidence_claim
    ON evidence_claim.claim_id = expected.claim_id
    AND evidence_claim.evidence_id = expected.evidence_id
LEFT JOIN signals.signal_bundles AS signal_bundle
    ON signal_bundle.signal_bundle_id = expected.signal_bundle_id
LEFT JOIN recommendations.target_weights AS target_weights
    ON target_weights.target_weights_id = expected.target_weights_id
    AND expected.signal_bundle_id = ANY(target_weights.source_signal_bundle_ids)
LEFT JOIN recommendations.recommendation_artifacts AS recommendation
    ON recommendation.recommendation_id = expected.recommendation_id
    AND recommendation.target_weights_id = expected.target_weights_id
    AND recommendation.signal_bundle_id = expected.signal_bundle_id
    AND expected.evidence_id = ANY(recommendation.evidence_ids)
LEFT JOIN recommendations.recommendation_audits AS recommendation_audit
    ON recommendation_audit.audit_id = expected.audit_id
    AND recommendation_audit.recommendation_id = expected.recommendation_id
    AND recommendation_audit.target_weights_id = expected.target_weights_id
    AND recommendation_audit.signal_bundle_id = expected.signal_bundle_id
    AND expected.evidence_id = ANY(recommendation_audit.evidence_ids)
LEFT JOIN audit.backtest_runs AS backtest
    ON backtest.backtest_run_id = expected.backtest_run_id
    AND backtest.summary_metrics_json ->> 'recommendation_id' = expected.recommendation_id
LEFT JOIN audit.run_artifacts AS evaluation_run_artifact
    ON evaluation_run_artifact.run_id = backtest.summary_metrics_json ->> 'run_artifact_id'
    AND evaluation_run_artifact.run_type = 'evaluation';
"""


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


def run_advisory_demo(connection: Connection) -> dict[str, object]:
    row = _fetch_prerequisites(connection)
    missing = _missing_prerequisites(row)
    result = _failed_result(row, missing) if missing else _succeeded_result(row)
    _write_run_artifact(connection, result)
    return result


def _fetch_prerequisites(connection: Connection) -> dict[str, object]:
    with connection.cursor() as cursor:
        cursor.execute(SELECT_PREREQUISITES_SQL, EXPECTED_IDS)
        row = cursor.fetchone()
        column_names = _column_names(cursor.description)
    return _row_to_dict(row, column_names)


def _succeeded_result(row: Mapping[str, object]) -> dict[str, object]:
    inputs_hash = _hash("advisory_demo_inputs", _input_payload(row))
    run_id = f"run-advisory-demo-{inputs_hash[:16]}"
    artifact_uri = _artifact_uri(run_id, row)
    output_hash = _hash(
        "advisory_demo_output",
        {
            "artifact_uri": artifact_uri,
            "recommendation_id": row["recommendation_id"],
            "run_id": run_id,
            "run_type": RUN_TYPE,
            "status": "succeeded",
        },
    )
    return {
        "run_id": run_id,
        "run_type": RUN_TYPE,
        "status": "succeeded",
        "exit_code": 0,
        "inputs_hash": inputs_hash,
        "output_hash": output_hash,
        "artifact_uri": artifact_uri,
        "missing_prerequisites": [],
        "error_summary": None,
    }


def _artifact_uri(run_id: str, row: Mapping[str, object]) -> str:
    query = urlencode(
        {
            "recommendation_id": str(row["recommendation_id"]),
            "audit_id": str(row["audit_id"]),
            "evaluation_id": str(row["backtest_run_id"]),
            "backtest_run_id": str(row["backtest_run_id"]),
            "advisory_label": str(row["advisory_label"]),
        }
    )
    return f"artifact://demo/advisory-run/{run_id}?{query}"


def _failed_result(row: Mapping[str, object], missing: Sequence[str]) -> dict[str, object]:
    inputs_hash = _hash(
        "advisory_demo_missing_inputs",
        {
            "expected_ids": EXPECTED_IDS,
            "missing_prerequisites": tuple(missing),
            "present": _present_payload(row),
        },
    )
    return {
        "run_id": f"run-advisory-demo-failed-{inputs_hash[:16]}",
        "run_type": RUN_TYPE,
        "status": "failed",
        "exit_code": 1,
        "inputs_hash": inputs_hash,
        "output_hash": None,
        "artifact_uri": None,
        "missing_prerequisites": list(missing),
        "error_summary": f"Missing advisory demo prerequisites: {', '.join(missing)}",
    }


def _write_run_artifact(connection: Connection, result: Mapping[str, object]) -> None:
    params = (
        result["run_id"],
        result["run_type"],
        DEMO_RUN_AT,
        DEMO_RUN_AT,
        result["inputs_hash"],
        result["output_hash"],
        result["artifact_uri"],
        result["status"],
        result["error_summary"],
        DEMO_RUN_AT,
    )
    with connection.cursor() as cursor:
        cursor.execute(UPSERT_RUN_ARTIFACT_SQL, params)
    connection.commit()


def _missing_prerequisites(row: Mapping[str, object]) -> list[str]:
    missing: list[str] = []
    if not _has_text(row.get("evidence_id")):
        missing.append("evidence")
    if not _has_text(row.get("claim_id")):
        missing.append("claim")
    if not _has_text(row.get("signal_bundle_id")):
        missing.append("signal_bundle")
    if (
        not _has_text(row.get("target_weights_id"))
        or row.get("target_weights_validation_status") != "validated"
        or row.get("target_weights_generated_by") != "deterministic_demo_seed"
    ):
        missing.append("target_weights")
    if (
        not _has_text(row.get("recommendation_id"))
        or row.get("advisory_label") != "advisory_only"
    ):
        missing.append("recommendation")
    if not _has_text(row.get("audit_id")) or row.get("audit_schema_valid") is not True:
        missing.append("audit")
    if (
        not _has_text(row.get("backtest_run_id"))
        or row.get("backtest_status") != "succeeded"
        or not _has_text(row.get("evaluation_run_artifact_id"))
        or row.get("evaluation_run_status") != "succeeded"
    ):
        missing.append("evaluation/backtest")
    return missing


def _input_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "audit": {
            "audit_id": row.get("audit_id"),
            "deterministic_checks": row.get("audit_deterministic_checks"),
        },
        "claim": {
            "claim_id": row.get("claim_id"),
            "extracted_by_model_run_id": row.get("extracted_by_model_run_id"),
        },
        "evaluation": {
            "backtest_run_id": row.get("backtest_run_id"),
            "evaluation_inputs_hash": row.get("evaluation_inputs_hash"),
            "evaluation_output_hash": row.get("evaluation_output_hash"),
            "evaluation_run_artifact_id": row.get("evaluation_run_artifact_id"),
            "summary_metrics": row.get("backtest_summary_metrics"),
        },
        "evidence": {
            "content_hash": row.get("evidence_content_hash"),
            "evidence_id": row.get("evidence_id"),
        },
        "recommendation": {
            "advisory_label": row.get("advisory_label"),
            "evidence_ids": row.get("recommendation_evidence_ids"),
            "final_payload": row.get("recommendation_final_payload"),
            "model_run_ids": row.get("recommendation_model_run_ids"),
            "recommendation_id": row.get("recommendation_id"),
            "score_breakdown": row.get("recommendation_score_breakdown"),
        },
        "signal_bundle": {
            "input_snapshot_hash": row.get("signal_input_snapshot_hash"),
            "signal_bundle_id": row.get("signal_bundle_id"),
        },
        "target_weights": {
            "generated_by": row.get("target_weights_generated_by"),
            "target_weights_id": row.get("target_weights_id"),
            "validation_status": row.get("target_weights_validation_status"),
        },
    }


def _present_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in _input_payload(row).items() if value}


def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _hash(*parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=_json_default)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
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
    if row is None:
        return {}
    return dict(zip(column_names, row, strict=True))  # type: ignore[arg-type]


def run_from_environment() -> dict[str, object]:
    import psycopg

    settings = RuntimeSettings.from_env(os.environ, allow_defaults=True)
    with psycopg.connect(settings.database_url) as connection:
        return run_advisory_demo(connection)


def main() -> None:
    try:
        result = run_from_environment()
    except RuntimeConfigError as error:
        result = {
            "run_type": RUN_TYPE,
            "status": "failed",
            "exit_code": 2,
            "error_summary": str(error),
        }

    print(json.dumps(result, sort_keys=True, default=_json_default))
    exit_code = int(result.get("exit_code", 1))
    if exit_code != 0:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
