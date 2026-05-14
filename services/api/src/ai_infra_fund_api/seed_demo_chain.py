from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from typing import Protocol

from ai_infra_fund_core.runtime.config import RuntimeSettings


DEMO_CHAIN_ID = "demo-ai-infra-nvda"
DEMO_EVIDENCE_ID = "evidence-demo-ai-infra-nvda"
DEMO_CHUNK_ID = "chunk-demo-ai-infra-nvda-0"
DEMO_CLAIM_ID = "claim-demo-ai-infra-nvda-demand"
DEMO_MODEL_RUN_ID = "model-run-demo-local-review"
DEMO_SIGNAL_BUNDLE_ID = "signal-bundle-demo-nvda"
DEMO_TARGET_WEIGHTS_ID = "target-weights-demo-ai-infra"
DEMO_RECOMMENDATION_ID = "recommendation-demo-nvda"
DEMO_AUDIT_ID = "recommendation-audit-demo-nvda"
DEMO_BACKTEST_RUN_ID = "evaluation-demo-ai-infra"
DEMO_RUN_ARTIFACT_ID = "run-demo-advisory-chain"
DEMO_CREATED_AT = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)

DEMO_TEXT = (
    "AI infrastructure demand is constrained by accelerator supply, advanced packaging, "
    "HBM availability, networking, and datacenter power delivery. NVDA remains the demo "
    "beneficiary, while valuation and capacity normalization remain explicit risks."
)


class Cursor(Protocol):
    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...

    def commit(self) -> None:
        ...


UPSERT_MODEL_RUN_SQL = """
INSERT INTO audit.model_runs (
    model_run_id,
    task_role,
    model_id,
    deployment,
    provider,
    prompt_version,
    input_hash,
    output_hash,
    latency_ms,
    token_estimate_input,
    token_estimate_output,
    schema_valid,
    retry_count,
    data_classes,
    status,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (model_run_id) DO UPDATE SET
    task_role = EXCLUDED.task_role,
    model_id = EXCLUDED.model_id,
    deployment = EXCLUDED.deployment,
    provider = EXCLUDED.provider,
    prompt_version = EXCLUDED.prompt_version,
    input_hash = EXCLUDED.input_hash,
    output_hash = EXCLUDED.output_hash,
    latency_ms = EXCLUDED.latency_ms,
    token_estimate_input = EXCLUDED.token_estimate_input,
    token_estimate_output = EXCLUDED.token_estimate_output,
    schema_valid = EXCLUDED.schema_valid,
    retry_count = EXCLUDED.retry_count,
    data_classes = EXCLUDED.data_classes,
    status = EXCLUDED.status,
    created_at = EXCLUDED.created_at;
"""


UPSERT_EVIDENCE_ITEM_SQL = """
INSERT INTO evidence.evidence_items (
    evidence_id,
    source_uri,
    source_type,
    title,
    publisher,
    published_at,
    ingested_at,
    content_hash,
    license_label,
    data_class,
    tickers,
    themes,
    summary,
    storage_uri,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (evidence_id) DO UPDATE SET
    source_uri = EXCLUDED.source_uri,
    source_type = EXCLUDED.source_type,
    title = EXCLUDED.title,
    publisher = EXCLUDED.publisher,
    published_at = EXCLUDED.published_at,
    ingested_at = EXCLUDED.ingested_at,
    content_hash = EXCLUDED.content_hash,
    license_label = EXCLUDED.license_label,
    data_class = EXCLUDED.data_class,
    tickers = EXCLUDED.tickers,
    themes = EXCLUDED.themes,
    summary = EXCLUDED.summary,
    storage_uri = EXCLUDED.storage_uri,
    created_at = EXCLUDED.created_at;
"""


UPSERT_EVIDENCE_CHUNK_SQL = """
INSERT INTO evidence.evidence_chunks (
    chunk_id,
    evidence_id,
    chunk_index,
    chunk_text,
    span_ref,
    content_hash,
    embedding_model,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (chunk_id) DO UPDATE SET
    evidence_id = EXCLUDED.evidence_id,
    chunk_index = EXCLUDED.chunk_index,
    chunk_text = EXCLUDED.chunk_text,
    span_ref = EXCLUDED.span_ref,
    content_hash = EXCLUDED.content_hash,
    embedding_model = EXCLUDED.embedding_model,
    created_at = EXCLUDED.created_at;
"""


UPSERT_EVIDENCE_CLAIM_SQL = """
INSERT INTO evidence.evidence_claims (
    claim_id,
    evidence_id,
    chunk_id,
    ticker_or_theme,
    claim_type,
    direction,
    magnitude,
    time_horizon,
    confidence,
    quote_or_span_ref,
    extracted_by_model_run_id,
    validated_at,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (claim_id) DO UPDATE SET
    evidence_id = EXCLUDED.evidence_id,
    chunk_id = EXCLUDED.chunk_id,
    ticker_or_theme = EXCLUDED.ticker_or_theme,
    claim_type = EXCLUDED.claim_type,
    direction = EXCLUDED.direction,
    magnitude = EXCLUDED.magnitude,
    time_horizon = EXCLUDED.time_horizon,
    confidence = EXCLUDED.confidence,
    quote_or_span_ref = EXCLUDED.quote_or_span_ref,
    extracted_by_model_run_id = EXCLUDED.extracted_by_model_run_id,
    validated_at = EXCLUDED.validated_at,
    created_at = EXCLUDED.created_at;
"""


UPSERT_SIGNAL_BUNDLE_SQL = """
INSERT INTO signals.signal_bundles (
    signal_bundle_id,
    ticker,
    as_of,
    strategic_thesis_score,
    tactical_technical_score,
    forward_indicator_score,
    portfolio_risk_score,
    formula_versions,
    input_snapshot_hash,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s
) ON CONFLICT (signal_bundle_id) DO UPDATE SET
    ticker = EXCLUDED.ticker,
    as_of = EXCLUDED.as_of,
    strategic_thesis_score = EXCLUDED.strategic_thesis_score,
    tactical_technical_score = EXCLUDED.tactical_technical_score,
    forward_indicator_score = EXCLUDED.forward_indicator_score,
    portfolio_risk_score = EXCLUDED.portfolio_risk_score,
    formula_versions = EXCLUDED.formula_versions,
    input_snapshot_hash = EXCLUDED.input_snapshot_hash,
    created_at = EXCLUDED.created_at;
"""


UPSERT_TARGET_WEIGHTS_SQL = """
INSERT INTO recommendations.target_weights (
    target_weights_id,
    as_of,
    portfolio_id,
    cash_weight,
    weights_json,
    constraints_json,
    source_signal_bundle_ids,
    generated_by,
    validation_status,
    created_at
) VALUES (
    %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s
) ON CONFLICT (target_weights_id) DO UPDATE SET
    as_of = EXCLUDED.as_of,
    portfolio_id = EXCLUDED.portfolio_id,
    cash_weight = EXCLUDED.cash_weight,
    weights_json = EXCLUDED.weights_json,
    constraints_json = EXCLUDED.constraints_json,
    source_signal_bundle_ids = EXCLUDED.source_signal_bundle_ids,
    generated_by = EXCLUDED.generated_by,
    validation_status = EXCLUDED.validation_status,
    created_at = EXCLUDED.created_at;
"""


UPSERT_RECOMMENDATION_SQL = """
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
) ON CONFLICT (recommendation_id) DO UPDATE SET
    ticker_or_portfolio = EXCLUDED.ticker_or_portfolio,
    advisory_label = EXCLUDED.advisory_label,
    action = EXCLUDED.action,
    horizon = EXCLUDED.horizon,
    score_breakdown_json = EXCLUDED.score_breakdown_json,
    target_weights_id = EXCLUDED.target_weights_id,
    signal_bundle_id = EXCLUDED.signal_bundle_id,
    evidence_ids = EXCLUDED.evidence_ids,
    model_run_ids = EXCLUDED.model_run_ids,
    risks_json = EXCLUDED.risks_json,
    contradictions_json = EXCLUDED.contradictions_json,
    final_payload_json = EXCLUDED.final_payload_json,
    created_at = EXCLUDED.created_at;
"""


UPSERT_RECOMMENDATION_AUDIT_SQL = """
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
) ON CONFLICT (audit_id) DO UPDATE SET
    recommendation_id = EXCLUDED.recommendation_id,
    target_weights_id = EXCLUDED.target_weights_id,
    signal_bundle_id = EXCLUDED.signal_bundle_id,
    evidence_ids = EXCLUDED.evidence_ids,
    model_run_ids = EXCLUDED.model_run_ids,
    deterministic_checks_json = EXCLUDED.deterministic_checks_json,
    reviewer_findings_json = EXCLUDED.reviewer_findings_json,
    schema_valid = EXCLUDED.schema_valid,
    created_at = EXCLUDED.created_at;
"""


UPSERT_BACKTEST_RUN_SQL = """
INSERT INTO audit.backtest_runs (
    backtest_run_id,
    strategy_id,
    dataset_snapshot_ids,
    started_at,
    completed_at,
    walk_forward_config_json,
    summary_metrics_json,
    transaction_cost_model_json,
    status,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s
) ON CONFLICT (backtest_run_id) DO UPDATE SET
    strategy_id = EXCLUDED.strategy_id,
    dataset_snapshot_ids = EXCLUDED.dataset_snapshot_ids,
    started_at = EXCLUDED.started_at,
    completed_at = EXCLUDED.completed_at,
    walk_forward_config_json = EXCLUDED.walk_forward_config_json,
    summary_metrics_json = EXCLUDED.summary_metrics_json,
    transaction_cost_model_json = EXCLUDED.transaction_cost_model_json,
    status = EXCLUDED.status,
    created_at = EXCLUDED.created_at;
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
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (run_id) DO UPDATE SET
    run_type = EXCLUDED.run_type,
    started_at = EXCLUDED.started_at,
    completed_at = EXCLUDED.completed_at,
    inputs_hash = EXCLUDED.inputs_hash,
    output_hash = EXCLUDED.output_hash,
    artifact_uri = EXCLUDED.artifact_uri,
    status = EXCLUDED.status,
    created_at = EXCLUDED.created_at;
"""


def seed_demo_advisory_chain(connection: Connection) -> dict[str, object]:
    values = _seed_values()
    with connection.cursor() as cursor:
        for statement, params in _seed_statements(values):
            cursor.execute(statement, params)
    connection.commit()
    return {
        "chain_id": DEMO_CHAIN_ID,
        "advisory_label": "advisory_only",
        "evidence_id": DEMO_EVIDENCE_ID,
        "chunk_id": DEMO_CHUNK_ID,
        "claim_id": DEMO_CLAIM_ID,
        "model_run_id": DEMO_MODEL_RUN_ID,
        "signal_bundle_id": DEMO_SIGNAL_BUNDLE_ID,
        "target_weights_id": DEMO_TARGET_WEIGHTS_ID,
        "recommendation_id": DEMO_RECOMMENDATION_ID,
        "audit_id": DEMO_AUDIT_ID,
        "backtest_run_id": DEMO_BACKTEST_RUN_ID,
        "run_artifact_id": DEMO_RUN_ARTIFACT_ID,
    }


def _seed_values() -> dict[str, object]:
    input_hash = _hash("demo-input", DEMO_TEXT)
    output_hash = _hash("demo-output", DEMO_RECOMMENDATION_ID)
    signal_hash = _hash("demo-signal", DEMO_SIGNAL_BUNDLE_ID)
    chunk_hash = _hash("demo-chunk", DEMO_TEXT)
    return {
        "input_hash": input_hash,
        "output_hash": output_hash,
        "signal_hash": signal_hash,
        "evidence_hash": _hash("demo-evidence", DEMO_TEXT),
        "chunk_hash": chunk_hash,
        "formula_versions": _json(
            {
                "strategic_thesis_score": "strategic-thesis-v1",
                "tactical_technical_score": "tactical-technical-v1",
                "forward_indicator_score": "forward-indicator-v1",
                "portfolio_risk_score": "portfolio-risk-v1",
            }
        ),
        "weights": _json({"NVDA": "0.12", "MSFT": "0.18", "cash": "0.40"}),
        "constraints": _json(
            {
                "max_single_name_weight": "0.25",
                "cash_floor": "0.20",
                "turnover_cap": "0.15",
                "liquidity_floor": "0.70",
            }
        ),
        "score_breakdown": _json(
            {
                "strategic_thesis_score": "0.84",
                "tactical_technical_score": "0.61",
                "forward_indicator_score": "0.72",
                "portfolio_risk_score": "0.32",
                "combined_score": "0.74",
            }
        ),
        "risks": _json(["valuation", "capacity normalization", "supply chain bottleneck"]),
        "contradictions": _json(["Capacity additions could reduce scarcity premium."]),
        "final_payload": _json(
            {
                "summary": "Accumulate NVDA as an advisory-only demo chain; no order is generated.",
                "implementation": "Staged accumulation only after manual review.",
            }
        ),
        "deterministic_checks": _json(
            {
                "advisory_label_present": True,
                "evidence_ids_present": True,
                "model_run_ids_present": True,
                "signal_bundle_id_present": True,
                "target_weights_id_present": True,
                "target_weights_generated_by_deterministic_code": True,
            }
        ),
        "reviewer_findings": _json(
            {
                "status": "deterministic_seed",
                "contradictions": ["valuation risk and capacity normalization remain visible"],
            }
        ),
        "walk_forward_config": _json(
            {
                "validation_protocol": "demo-walk-forward-v1",
                "recommendation_id": DEMO_RECOMMENDATION_ID,
                "formula_versions": {"evaluation": "demo-evaluation-v1"},
            }
        ),
        "summary_metrics": _json(
            {
                "recommendation_id": DEMO_RECOMMENDATION_ID,
                "benchmark_version": "demo-ai-infra-benchmark-v1",
                "relative_return": "0.06",
                "max_drawdown": "-0.12",
                "volatility": "0.28",
                "run_artifact_id": DEMO_RUN_ARTIFACT_ID,
            }
        ),
        "transaction_cost_model": _json(
            {"spread_bps": "4", "slippage_bps": "6", "commission_bps": "1"}
        ),
    }


def _seed_statements(values: dict[str, object]) -> tuple[tuple[str, tuple[object, ...]], ...]:
    return (
        (
            UPSERT_MODEL_RUN_SQL,
            (
                DEMO_MODEL_RUN_ID,
                "evidence_summary",
                "deterministic-demo-seed",
                "deterministic-demo-seed",
                "local",
                "demo-advisory-chain-v1",
                values["input_hash"],
                values["output_hash"],
                0,
                0,
                0,
                True,
                0,
                ["public_evidence", "run_audit"],
                "success",
                DEMO_CREATED_AT,
            ),
        ),
        (
            UPSERT_EVIDENCE_ITEM_SQL,
            (
                DEMO_EVIDENCE_ID,
                "demo://situational-awareness/ai-infrastructure",
                "manual_report",
                "Demo AI Infrastructure Thesis",
                "local_demo_seed",
                DEMO_CREATED_AT,
                DEMO_CREATED_AT,
                values["evidence_hash"],
                "demo_public",
                "public_evidence",
                ["NVDA", "MSFT"],
                ["ai_accelerators", "datacenter_power", "advanced_packaging"],
                "Demo public evidence for AI infrastructure demand, accelerator supply, and datacenter constraints.",
                "local://demo/advisory-chain",
                DEMO_CREATED_AT,
            ),
        ),
        (
            UPSERT_EVIDENCE_CHUNK_SQL,
            (
                DEMO_CHUNK_ID,
                DEMO_EVIDENCE_ID,
                0,
                DEMO_TEXT,
                "chars:0-240",
                values["chunk_hash"],
                "local-demo-null",
                DEMO_CREATED_AT,
            ),
        ),
        (
            UPSERT_EVIDENCE_CLAIM_SQL,
            (
                DEMO_CLAIM_ID,
                DEMO_EVIDENCE_ID,
                DEMO_CHUNK_ID,
                "NVDA",
                "supply_demand",
                "positive",
                Decimal("0.82"),
                "medium_term",
                Decimal("0.86"),
                "chars:38-160",
                DEMO_MODEL_RUN_ID,
                DEMO_CREATED_AT,
                DEMO_CREATED_AT,
            ),
        ),
        (
            UPSERT_SIGNAL_BUNDLE_SQL,
            (
                DEMO_SIGNAL_BUNDLE_ID,
                "NVDA",
                DEMO_CREATED_AT,
                Decimal("0.84"),
                Decimal("0.61"),
                Decimal("0.72"),
                Decimal("0.32"),
                values["formula_versions"],
                values["signal_hash"],
                DEMO_CREATED_AT,
            ),
        ),
        (
            UPSERT_TARGET_WEIGHTS_SQL,
            (
                DEMO_TARGET_WEIGHTS_ID,
                DEMO_CREATED_AT,
                "demo-ai-infra-portfolio",
                Decimal("0.40"),
                values["weights"],
                values["constraints"],
                [DEMO_SIGNAL_BUNDLE_ID],
                "deterministic_demo_seed",
                "validated",
                DEMO_CREATED_AT,
            ),
        ),
        (
            UPSERT_RECOMMENDATION_SQL,
            (
                DEMO_RECOMMENDATION_ID,
                "NVDA",
                "advisory_only",
                "accumulate",
                "medium_term",
                values["score_breakdown"],
                DEMO_TARGET_WEIGHTS_ID,
                DEMO_SIGNAL_BUNDLE_ID,
                [DEMO_EVIDENCE_ID],
                [DEMO_MODEL_RUN_ID],
                values["risks"],
                values["contradictions"],
                values["final_payload"],
                DEMO_CREATED_AT,
            ),
        ),
        (
            UPSERT_RECOMMENDATION_AUDIT_SQL,
            (
                DEMO_AUDIT_ID,
                DEMO_RECOMMENDATION_ID,
                DEMO_TARGET_WEIGHTS_ID,
                DEMO_SIGNAL_BUNDLE_ID,
                [DEMO_EVIDENCE_ID],
                [DEMO_MODEL_RUN_ID],
                values["deterministic_checks"],
                values["reviewer_findings"],
                True,
                DEMO_CREATED_AT,
            ),
        ),
        (
            UPSERT_BACKTEST_RUN_SQL,
            (
                DEMO_BACKTEST_RUN_ID,
                "strategy-demo-ai-infra",
                ["dataset-snapshot-demo-ai-infra"],
                DEMO_CREATED_AT,
                DEMO_CREATED_AT,
                values["walk_forward_config"],
                values["summary_metrics"],
                values["transaction_cost_model"],
                "succeeded",
                DEMO_CREATED_AT,
            ),
        ),
        (
            UPSERT_RUN_ARTIFACT_SQL,
            (
                DEMO_RUN_ARTIFACT_ID,
                "evaluation",
                DEMO_CREATED_AT,
                DEMO_CREATED_AT,
                values["input_hash"],
                values["output_hash"],
                "artifact://demo/advisory-chain",
                "succeeded",
                DEMO_CREATED_AT,
            ),
        ),
    )


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _hash(*parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    import psycopg

    settings = RuntimeSettings.from_env(os.environ, allow_defaults=True)
    with psycopg.connect(settings.database_url) as connection:
        result = seed_demo_advisory_chain(connection)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
