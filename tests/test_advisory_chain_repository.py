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
    def test_returns_complete_linked_demo_chain_without_raw_chunk_text(self) -> None:
        from ai_infra_fund_api.repositories.advisory_chain import AdvisoryChainRepository

        connection = FakeConnection(
            ResultSet(
                [
                    (
                        "evidence-demo-ai-infra-nvda",
                        "demo://situational-awareness/ai-infra",
                        "manual_report",
                        "Demo AI Infrastructure Thesis",
                        "demo_public",
                        "public_evidence",
                        "a" * 64,
                        NOW,
                        ["NVDA"],
                        ["ai_accelerators"],
                        "chunk-demo-ai-infra-nvda-0",
                        0,
                        "chars:0-240",
                        "b" * 64,
                        "claim-demo-ai-infra-nvda-demand",
                        "NVDA",
                        "supply_demand",
                        "positive",
                        "0.82",
                        "medium_term",
                        "0.86",
                        "chars:38-160",
                        "model-run-demo-local-review",
                        "signal-bundle-demo-nvda",
                        "NVDA",
                        NOW,
                        "0.84",
                        "0.61",
                        "0.72",
                        "0.32",
                        {"strategic": "v1"},
                        "c" * 64,
                        "target-weights-demo-ai-infra",
                        "0.40",
                        {"NVDA": "0.12", "MSFT": "0.18"},
                        {"max_single_name_weight": "0.25"},
                        "deterministic_demo_seed",
                        "validated",
                        "recommendation-demo-nvda",
                        "NVDA",
                        "advisory_only",
                        "accumulate",
                        "medium_term",
                        {"combined_score": "0.74"},
                        ["evidence-demo-ai-infra-nvda"],
                        ["model-run-demo-local-review"],
                        ["valuation", "supply chain"],
                        ["capacity normalization"],
                        {"summary": "Accumulate advisory-only."},
                        "recommendation-audit-demo-nvda",
                        {"checks_passed": True},
                        {"status": "deterministic_seed"},
                        True,
                        "evaluation-demo-ai-infra",
                        "strategy-demo-ai-infra",
                        ["dataset-snapshot-demo-ai-infra"],
                        {"benchmark_version": "demo-benchmark-v1"},
                        {"slippage_bps": "5"},
                        "succeeded",
                        "run-demo-advisory-chain",
                        "evaluation",
                        "artifact://demo/advisory-chain",
                        "succeeded",
                    )
                ],
                CHAIN_COLUMNS,
            )
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
    def __init__(self, result_set: ResultSet) -> None:
        self._result_set = result_set
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.description: tuple[tuple[str], ...] = ()
        self.rows: list[tuple[object, ...]] = []

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params if params is not None else ()))
        self.rows = self._result_set.rows
        self.description = tuple((column,) for column in self._result_set.columns)

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self, result_set: ResultSet) -> None:
        self.cursor_instance = FakeCursor(result_set)

    def cursor(self) -> FakeCursor:
        return self.cursor_instance


if __name__ == "__main__":
    unittest.main()
