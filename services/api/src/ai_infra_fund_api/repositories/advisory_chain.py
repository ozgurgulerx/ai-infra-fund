from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
import json
from typing import Protocol


DEMO_CHAIN_ID = "demo-ai-infra-nvda"
DEMO_RECOMMENDATION_ID = "recommendation-demo-nvda"
LATEST_LOCAL_CHAIN_ID = "latest-local-advisory"
LOCAL_ADVISORY_RUN_TYPE = "local_advisory"


class Cursor(Protocol):
    description: object

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...

    def fetchall(self) -> list[object]:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...


SELECT_DEMO_ADVISORY_CHAIN_SQL = """
SELECT
    evidence_item.evidence_id,
    evidence_item.source_uri,
    evidence_item.source_type,
    evidence_item.title,
    evidence_item.license_label,
    evidence_item.data_class,
    evidence_item.content_hash,
    evidence_item.ingested_at,
    evidence_item.tickers,
    evidence_item.themes,
    evidence_chunk.chunk_id,
    evidence_chunk.chunk_index,
    evidence_chunk.span_ref,
    evidence_chunk.content_hash AS chunk_content_hash,
    evidence_claim.claim_id,
    evidence_claim.ticker_or_theme,
    evidence_claim.claim_type,
    evidence_claim.direction,
    evidence_claim.magnitude,
    evidence_claim.time_horizon,
    evidence_claim.confidence,
    evidence_claim.quote_or_span_ref,
    evidence_claim.extracted_by_model_run_id,
    signal_bundle.signal_bundle_id,
    signal_bundle.ticker,
    signal_bundle.as_of,
    signal_bundle.strategic_thesis_score,
    signal_bundle.tactical_technical_score,
    signal_bundle.forward_indicator_score,
    signal_bundle.portfolio_risk_score,
    signal_bundle.formula_versions,
    signal_bundle.input_snapshot_hash,
    target_weights.target_weights_id,
    target_weights.cash_weight,
    target_weights.weights_json,
    target_weights.constraints_json,
    target_weights.generated_by,
    target_weights.validation_status,
    recommendation.recommendation_id,
    recommendation.ticker_or_portfolio,
    recommendation.advisory_label,
    recommendation.action,
    recommendation.horizon,
    recommendation.score_breakdown_json,
    recommendation.evidence_ids,
    recommendation.model_run_ids,
    recommendation.risks_json,
    recommendation.contradictions_json,
    recommendation.final_payload_json,
    recommendation_audit.audit_id,
    recommendation_audit.deterministic_checks_json,
    recommendation_audit.reviewer_findings_json,
    recommendation_audit.schema_valid,
    backtest.backtest_run_id,
    backtest.strategy_id,
    backtest.dataset_snapshot_ids,
    backtest.summary_metrics_json,
    backtest.transaction_cost_model_json,
    backtest.status AS evaluation_status,
    run_artifact.run_id,
    run_artifact.run_type,
    run_artifact.artifact_uri,
    run_artifact.status AS run_status
FROM recommendations.recommendation_artifacts AS recommendation
JOIN signals.signal_bundles AS signal_bundle
    ON signal_bundle.signal_bundle_id = recommendation.signal_bundle_id
JOIN recommendations.target_weights AS target_weights
    ON target_weights.target_weights_id = recommendation.target_weights_id
JOIN evidence.evidence_items AS evidence_item
    ON evidence_item.evidence_id = recommendation.evidence_ids[1]
JOIN evidence.evidence_chunks AS evidence_chunk
    ON evidence_chunk.evidence_id = evidence_item.evidence_id
JOIN evidence.evidence_claims AS evidence_claim
    ON evidence_claim.evidence_id = evidence_item.evidence_id
    AND evidence_claim.chunk_id = evidence_chunk.chunk_id
JOIN recommendations.recommendation_audits AS recommendation_audit
    ON recommendation_audit.recommendation_id = recommendation.recommendation_id
LEFT JOIN audit.backtest_runs AS backtest
    ON backtest.summary_metrics_json ->> 'recommendation_id' = recommendation.recommendation_id
LEFT JOIN audit.run_artifacts AS run_artifact
    ON run_artifact.run_id = backtest.summary_metrics_json ->> 'run_artifact_id'
WHERE recommendation.recommendation_id = %s
ORDER BY evidence_chunk.chunk_index ASC, evidence_claim.created_at ASC, recommendation_audit.created_at ASC
LIMIT 1;
"""


SELECT_LATEST_LOCAL_ADVISORY_CHAIN_SQL = """
SELECT
    evidence_item.evidence_id,
    evidence_item.source_uri,
    evidence_item.source_type,
    evidence_item.title,
    evidence_item.license_label,
    evidence_item.data_class,
    evidence_item.content_hash,
    evidence_item.ingested_at,
    evidence_item.tickers,
    evidence_item.themes,
    evidence_chunk.chunk_id,
    evidence_chunk.chunk_index,
    evidence_chunk.span_ref,
    evidence_chunk.content_hash AS chunk_content_hash,
    evidence_claim.claim_id,
    evidence_claim.ticker_or_theme,
    evidence_claim.claim_type,
    evidence_claim.direction,
    evidence_claim.magnitude,
    evidence_claim.time_horizon,
    evidence_claim.confidence,
    evidence_claim.quote_or_span_ref,
    evidence_claim.extracted_by_model_run_id,
    signal_bundle.signal_bundle_id,
    signal_bundle.ticker,
    signal_bundle.as_of,
    signal_bundle.strategic_thesis_score,
    signal_bundle.tactical_technical_score,
    signal_bundle.forward_indicator_score,
    signal_bundle.portfolio_risk_score,
    signal_bundle.formula_versions,
    signal_bundle.input_snapshot_hash,
    target_weights.target_weights_id,
    target_weights.cash_weight,
    target_weights.weights_json,
    target_weights.constraints_json,
    target_weights.generated_by,
    target_weights.validation_status,
    recommendation.recommendation_id,
    recommendation.ticker_or_portfolio,
    recommendation.advisory_label,
    recommendation.action,
    recommendation.horizon,
    recommendation.score_breakdown_json,
    recommendation.evidence_ids,
    recommendation.model_run_ids,
    recommendation.risks_json,
    recommendation.contradictions_json,
    recommendation.final_payload_json,
    recommendation_audit.audit_id,
    recommendation_audit.deterministic_checks_json,
    recommendation_audit.reviewer_findings_json,
    recommendation_audit.schema_valid,
    backtest.backtest_run_id,
    backtest.strategy_id,
    backtest.dataset_snapshot_ids,
    backtest.summary_metrics_json,
    backtest.transaction_cost_model_json,
    backtest.status AS evaluation_status,
    run_artifact.run_id,
    run_artifact.run_type,
    run_artifact.artifact_uri,
    run_artifact.status AS run_status
FROM audit.run_artifacts AS run_artifact
JOIN audit.backtest_runs AS backtest
    ON backtest.summary_metrics_json ->> 'local_run_artifact_id' = run_artifact.run_id
JOIN recommendations.recommendation_artifacts AS recommendation
    ON recommendation.recommendation_id = backtest.summary_metrics_json ->> 'recommendation_id'
JOIN signals.signal_bundles AS signal_bundle
    ON signal_bundle.signal_bundle_id = recommendation.signal_bundle_id
JOIN recommendations.target_weights AS target_weights
    ON target_weights.target_weights_id = recommendation.target_weights_id
JOIN evidence.evidence_items AS evidence_item
    ON evidence_item.evidence_id = recommendation.evidence_ids[1]
JOIN evidence.evidence_chunks AS evidence_chunk
    ON evidence_chunk.evidence_id = evidence_item.evidence_id
JOIN evidence.evidence_claims AS evidence_claim
    ON evidence_claim.evidence_id = evidence_item.evidence_id
    AND evidence_claim.chunk_id = evidence_chunk.chunk_id
JOIN recommendations.recommendation_audits AS recommendation_audit
    ON recommendation_audit.recommendation_id = recommendation.recommendation_id
WHERE run_artifact.run_type = %s
    AND run_artifact.status = 'succeeded'
ORDER BY run_artifact.started_at DESC, run_artifact.created_at DESC, evidence_chunk.chunk_index ASC
LIMIT 1;
"""


class AdvisoryChainRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get_demo_chain(self) -> dict[str, object]:
        with self._connection.cursor() as cursor:
            cursor.execute(SELECT_DEMO_ADVISORY_CHAIN_SQL, (DEMO_RECOMMENDATION_ID,))
            rows = cursor.fetchall()
            column_names = _column_names(cursor.description)

        if not rows:
            return {
                "status": "empty",
                "chain_id": DEMO_CHAIN_ID,
                "detail": "Demo advisory chain has not been seeded.",
            }

        return _chain_payload(_row_to_dict(rows[0], column_names), chain_id=DEMO_CHAIN_ID)

    def get_latest_chain(self) -> dict[str, object]:
        with self._connection.cursor() as cursor:
            cursor.execute(SELECT_LATEST_LOCAL_ADVISORY_CHAIN_SQL, (LOCAL_ADVISORY_RUN_TYPE,))
            rows = cursor.fetchall()
            column_names = _column_names(cursor.description)

        if rows:
            return _chain_payload(_row_to_dict(rows[0], column_names), chain_id=LATEST_LOCAL_CHAIN_ID)

        return self.get_demo_chain()


def _chain_payload(row: Mapping[str, object], *, chain_id: str) -> dict[str, object]:
    evidence_ids = _text_list(row.get("evidence_ids"))
    model_run_ids = _text_list(row.get("model_run_ids"))
    return {
        "status": "available",
        "chain_id": chain_id,
        "advisory_label": row["advisory_label"],
        "ids": {
            "evidence_id": row["evidence_id"],
            "chunk_id": row["chunk_id"],
            "claim_id": row["claim_id"],
            "model_run_ids": model_run_ids,
            "signal_bundle_id": row["signal_bundle_id"],
            "target_weights_id": row["target_weights_id"],
            "recommendation_id": row["recommendation_id"],
            "audit_id": row["audit_id"],
            "backtest_run_id": row["backtest_run_id"],
            "run_artifact_id": row["run_id"],
        },
        "evidence": {
            "evidence_id": row["evidence_id"],
            "source_uri": row["source_uri"],
            "source_type": row["source_type"],
            "title": row["title"],
            "license_label": row["license_label"],
            "data_class": row["data_class"],
            "content_hash": row["content_hash"],
            "ingested_at": _iso_or_none(row["ingested_at"]),
            "tickers": _text_list(row["tickers"]),
            "themes": _text_list(row["themes"]),
        },
        "chunk": {
            "chunk_id": row["chunk_id"],
            "chunk_index": _int(row["chunk_index"]),
            "span_ref": row["span_ref"],
            "content_hash": row["chunk_content_hash"],
        },
        "claim": {
            "claim_id": row["claim_id"],
            "ticker_or_theme": row["ticker_or_theme"],
            "claim_type": row["claim_type"],
            "direction": row["direction"],
            "magnitude": _decimal_text(row["magnitude"]),
            "time_horizon": row["time_horizon"],
            "confidence": _decimal_text(row["confidence"]),
            "quote_or_span_ref": row["quote_or_span_ref"],
            "extracted_by_model_run_id": row["extracted_by_model_run_id"],
        },
        "signal_bundle": {
            "signal_bundle_id": row["signal_bundle_id"],
            "ticker": row["ticker"],
            "as_of": _iso_or_none(row["as_of"]),
            "strategic_thesis_score": _decimal_text(row["strategic_thesis_score"]),
            "tactical_technical_score": _decimal_text(row["tactical_technical_score"]),
            "forward_indicator_score": _decimal_text(row["forward_indicator_score"]),
            "portfolio_risk_score": _decimal_text(row["portfolio_risk_score"]),
            "formula_versions": _json_value(row["formula_versions"]),
            "input_snapshot_hash": row["input_snapshot_hash"],
        },
        "target_weights": {
            "target_weights_id": row["target_weights_id"],
            "cash_weight": _decimal_text(row["cash_weight"]),
            "weights": _json_value(row["weights_json"]),
            "constraints": _json_value(row["constraints_json"]),
            "generated_by": row["generated_by"],
            "validation_status": row["validation_status"],
        },
        "recommendation": {
            "recommendation_id": row["recommendation_id"],
            "ticker_or_portfolio": row["ticker_or_portfolio"],
            "advisory_label": row["advisory_label"],
            "action": row["action"],
            "horizon": row["horizon"],
            "score_breakdown": _json_value(row["score_breakdown_json"]),
            "evidence_ids": evidence_ids,
            "model_run_ids": model_run_ids,
            "risks": _json_value(row["risks_json"]),
            "contradictions": _json_value(row["contradictions_json"]),
            "final_payload": _json_value(row["final_payload_json"]),
        },
        "audit": {
            "audit_id": row["audit_id"],
            "deterministic_checks": _json_value(row["deterministic_checks_json"]),
            "reviewer_findings": _json_value(row["reviewer_findings_json"]),
            "schema_valid": bool(row["schema_valid"]),
        },
        "evaluation": {
            "backtest_run_id": row["backtest_run_id"],
            "strategy_id": row["strategy_id"],
            "dataset_snapshot_ids": _text_list(row["dataset_snapshot_ids"]),
            "summary_metrics": _json_value(row["summary_metrics_json"]),
            "transaction_cost_model": _json_value(row["transaction_cost_model_json"]),
            "status": row["evaluation_status"],
            "run_artifact": {
                "run_id": row["run_id"],
                "run_type": row["run_type"],
                "artifact_uri": row["artifact_uri"],
                "status": row["run_status"],
            },
        },
    }


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


def _json_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str):
        return json.loads(value)
    return value


def _text_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item) for item in value]
    return [str(value)]


def _decimal_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _int(value: object) -> int:
    if value is None:
        return 0
    return int(value)


def _iso_or_none(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


__all__ = ["AdvisoryChainRepository"]
