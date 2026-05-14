from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)

CHAIN_COLUMNS = (
    "evidence_id",
    "source_uri",
    "source_type",
    "title",
    "license_label",
    "data_class",
    "content_hash",
    "ingested_at",
    "tickers",
    "themes",
    "chunk_id",
    "chunk_index",
    "span_ref",
    "chunk_content_hash",
    "claim_id",
    "ticker_or_theme",
    "claim_type",
    "direction",
    "magnitude",
    "time_horizon",
    "confidence",
    "quote_or_span_ref",
    "extracted_by_model_run_id",
    "signal_bundle_id",
    "ticker",
    "as_of",
    "strategic_thesis_score",
    "tactical_technical_score",
    "forward_indicator_score",
    "portfolio_risk_score",
    "formula_versions",
    "input_snapshot_hash",
    "target_weights_id",
    "cash_weight",
    "weights_json",
    "constraints_json",
    "generated_by",
    "validation_status",
    "recommendation_id",
    "ticker_or_portfolio",
    "advisory_label",
    "action",
    "horizon",
    "score_breakdown_json",
    "evidence_ids",
    "model_run_ids",
    "risks_json",
    "contradictions_json",
    "final_payload_json",
    "audit_id",
    "deterministic_checks_json",
    "reviewer_findings_json",
    "schema_valid",
    "backtest_run_id",
    "strategy_id",
    "dataset_snapshot_ids",
    "summary_metrics_json",
    "transaction_cost_model_json",
    "evaluation_status",
    "run_id",
    "run_type",
    "artifact_uri",
    "run_status",
)


class AdvisoryChainRepositoryTests(unittest.TestCase):
    def test_latest_chain_prefers_real_local_run_over_demo(self) -> None:
        from ai_infra_fund_api.repositories.advisory_chain import AdvisoryChainRepository

        local_row = chain_row(
            recommendation_id="recommendation-local-nvda",
            run_id="run-local-advisory-1",
            run_type="local_advisory",
            artifact_uri="artifact://local/advisory-run/run-local-advisory-1",
        )
        connection = FakeConnection(
            [
                ResultSet([local_row], CHAIN_COLUMNS),
                ResultSet([chain_row()], CHAIN_COLUMNS),
            ]
        )

        payload = AdvisoryChainRepository(connection).get_latest_chain()

        self.assertEqual("available", payload["status"])
        self.assertEqual("latest-local-advisory", payload["chain_id"])
        self.assertEqual("recommendation-local-nvda", payload["recommendation"]["recommendation_id"])
        self.assertEqual("run-local-advisory-1", payload["evaluation"]["run_artifact"]["run_id"])
        self.assertEqual(1, len(connection.cursor_instance.executions))
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("WHERE run_artifact.run_type = %s", statement)
        self.assertIn("ORDER BY run_artifact.started_at DESC", statement)
        self.assertEqual(("local_advisory",), params)

    def test_latest_chain_falls_back_to_demo_when_no_real_local_run_exists(self) -> None:
        from ai_infra_fund_api.repositories.advisory_chain import AdvisoryChainRepository

        connection = FakeConnection(
            [
                ResultSet([], CHAIN_COLUMNS),
                ResultSet([chain_row()], CHAIN_COLUMNS),
            ]
        )

        payload = AdvisoryChainRepository(connection).get_latest_chain()

        self.assertEqual("available", payload["status"])
        self.assertEqual("demo-ai-infra-nvda", payload["chain_id"])
        self.assertEqual("recommendation-demo-nvda", payload["recommendation"]["recommendation_id"])
        self.assertEqual(2, len(connection.cursor_instance.executions))

    def test_returns_complete_linked_demo_chain_without_raw_chunk_text(self) -> None:
        from ai_infra_fund_api.repositories.advisory_chain import AdvisoryChainRepository

        connection = FakeConnection(
            ResultSet([chain_row()], CHAIN_COLUMNS)
        )

        payload = AdvisoryChainRepository(connection).get_demo_chain()

        self.assertEqual("available", payload["status"])
        self.assertEqual("advisory_only", payload["advisory_label"])
        self.assertEqual("recommendation-demo-nvda", payload["recommendation"]["recommendation_id"])
        self.assertEqual("evidence-demo-ai-infra-nvda", payload["evidence"]["evidence_id"])
        self.assertEqual("chunk-demo-ai-infra-nvda-0", payload["chunk"]["chunk_id"])
        self.assertEqual("claim-demo-ai-infra-nvda-demand", payload["claim"]["claim_id"])
        self.assertEqual("signal-bundle-demo-nvda", payload["signal_bundle"]["signal_bundle_id"])
        self.assertEqual("target-weights-demo-ai-infra", payload["target_weights"]["target_weights_id"])
        self.assertEqual("recommendation-audit-demo-nvda", payload["audit"]["audit_id"])
        self.assertEqual("evaluation-demo-ai-infra", payload["evaluation"]["backtest_run_id"])
        self.assertEqual("run-demo-advisory-chain", payload["evaluation"]["run_artifact"]["run_id"])
        self.assertNotIn("chunk_text", str(payload))

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM recommendations.recommendation_artifacts", statement)
        self.assertIn("JOIN evidence.evidence_items", statement)
        self.assertIn("JOIN evidence.evidence_chunks", statement)
        self.assertIn("JOIN evidence.evidence_claims", statement)
        self.assertEqual(("recommendation-demo-nvda",), params)

    def test_missing_demo_chain_returns_empty_state(self) -> None:
        from ai_infra_fund_api.repositories.advisory_chain import AdvisoryChainRepository

        connection = FakeConnection(ResultSet([], CHAIN_COLUMNS))

        payload = AdvisoryChainRepository(connection).get_demo_chain()

        self.assertEqual(
            {
                "status": "empty",
                "chain_id": "demo-ai-infra-nvda",
                "detail": "Demo advisory chain has not been seeded.",
            },
            payload,
        )


class ResultSet:
    def __init__(self, rows: list[tuple[object, ...]], columns: tuple[str, ...]) -> None:
        self.rows = rows
        self.columns = columns


class FakeCursor:
    def __init__(self, result_sets: list[ResultSet]) -> None:
        self._result_sets = result_sets
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.description: tuple[tuple[str], ...] = ()
        self.rows: list[tuple[object, ...]] = []

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params if params is not None else ()))
        result_set = self._result_sets[min(len(self.executions) - 1, len(self._result_sets) - 1)]
        self.rows = result_set.rows
        self.description = tuple((column,) for column in result_set.columns)

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self, result_set: ResultSet | list[ResultSet]) -> None:
        result_sets = result_set if isinstance(result_set, list) else [result_set]
        self.cursor_instance = FakeCursor(result_sets)

    def cursor(self) -> FakeCursor:
        return self.cursor_instance


def chain_row(**overrides: object) -> tuple[object, ...]:
    row = {
        "evidence_id": "evidence-demo-ai-infra-nvda",
        "source_uri": "demo://situational-awareness/ai-infra",
        "source_type": "manual_report",
        "title": "Demo AI Infrastructure Thesis",
        "license_label": "demo_public",
        "data_class": "public_evidence",
        "content_hash": "a" * 64,
        "ingested_at": NOW,
        "tickers": ["NVDA"],
        "themes": ["ai_accelerators"],
        "chunk_id": "chunk-demo-ai-infra-nvda-0",
        "chunk_index": 0,
        "span_ref": "chars:0-240",
        "chunk_content_hash": "b" * 64,
        "claim_id": "claim-demo-ai-infra-nvda-demand",
        "ticker_or_theme": "NVDA",
        "claim_type": "supply_demand",
        "direction": "positive",
        "magnitude": "0.82",
        "time_horizon": "medium_term",
        "confidence": "0.86",
        "quote_or_span_ref": "chars:38-160",
        "extracted_by_model_run_id": "model-run-demo-local-review",
        "signal_bundle_id": "signal-bundle-demo-nvda",
        "ticker": "NVDA",
        "as_of": NOW,
        "strategic_thesis_score": "0.84",
        "tactical_technical_score": "0.61",
        "forward_indicator_score": "0.72",
        "portfolio_risk_score": "0.32",
        "formula_versions": {"strategic": "v1"},
        "input_snapshot_hash": "c" * 64,
        "target_weights_id": "target-weights-demo-ai-infra",
        "cash_weight": "0.40",
        "weights_json": {"NVDA": "0.12", "MSFT": "0.18"},
        "constraints_json": {"max_single_name_weight": "0.25"},
        "generated_by": "deterministic_demo_seed",
        "validation_status": "validated",
        "recommendation_id": "recommendation-demo-nvda",
        "ticker_or_portfolio": "NVDA",
        "advisory_label": "advisory_only",
        "action": "accumulate",
        "horizon": "medium_term",
        "score_breakdown_json": {"combined_score": "0.74"},
        "evidence_ids": ["evidence-demo-ai-infra-nvda"],
        "model_run_ids": ["model-run-demo-local-review"],
        "risks_json": ["valuation", "supply chain"],
        "contradictions_json": ["capacity normalization"],
        "final_payload_json": {"summary": "Accumulate advisory-only."},
        "audit_id": "recommendation-audit-demo-nvda",
        "deterministic_checks_json": {"checks_passed": True},
        "reviewer_findings_json": {"status": "deterministic_seed"},
        "schema_valid": True,
        "backtest_run_id": "evaluation-demo-ai-infra",
        "strategy_id": "strategy-demo-ai-infra",
        "dataset_snapshot_ids": ["dataset-snapshot-demo-ai-infra"],
        "summary_metrics_json": {"benchmark_version": "demo-benchmark-v1"},
        "transaction_cost_model_json": {"slippage_bps": "5"},
        "evaluation_status": "succeeded",
        "run_id": "run-demo-advisory-chain",
        "run_type": "evaluation",
        "artifact_uri": "artifact://demo/advisory-chain",
        "run_status": "succeeded",
    }
    row.update(overrides)
    return tuple(row[column] for column in CHAIN_COLUMNS)


if __name__ == "__main__":
    unittest.main()
