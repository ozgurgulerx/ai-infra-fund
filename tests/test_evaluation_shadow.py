from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.evaluation.shadow import (  # noqa: E402
    ShadowModeEvaluationRecord,
    create_shadow_mode_record,
)


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class Phase7ShadowModeEvaluationTests(unittest.TestCase):
    def test_records_shadow_output_without_changing_production_recommendation(self) -> None:
        metadata = {
            "output_hash": "b" * 64,
            "schema_version": "shadow-output-v1",
            "candidate_action": "accumulate",
        }
        metrics = {
            "schema_pass_rate": Decimal("1.0"),
            "citation_accuracy": Decimal("0.8"),
            "numeric_correctness": Decimal("0.75"),
            "contradiction_detection": Decimal("1.0"),
            "latency_ms": 250,
            "cost_estimate": Decimal("0.12"),
            "recommendation_usefulness": Decimal("0.7"),
        }

        record = create_shadow_mode_record(
            production_recommendation_id="recommendation-prod-1",
            strategy_id="strategy-ai-infra-core",
            data_snapshot_ids=("market-snapshot-1", "evidence-snapshot-1"),
            run_artifact_ids=("shadow-eval-run-1",),
            model_run_id="model-run-shadow-1",
            shadow_output_id="shadow-output-1",
            formula_version="shadow-eval-v1",
            benchmark_version="model-benchmark-v1",
            model_output_metadata=metadata,
            metrics=metrics,
            created_at=NOW,
        )

        self.assertIsInstance(record, ShadowModeEvaluationRecord)
        self.assertTrue(record.evaluation_id.startswith("shadow-eval-"))
        self.assertEqual("recommendation-prod-1", record.production_recommendation_id)
        self.assertEqual("strategy-ai-infra-core", record.strategy_id)
        self.assertEqual(("market-snapshot-1", "evidence-snapshot-1"), record.data_snapshot_ids)
        self.assertEqual(("shadow-eval-run-1",), record.run_artifact_ids)
        self.assertEqual("model-run-shadow-1", record.model_run_id)
        self.assertEqual("shadow-output-1", record.shadow_output_id)
        self.assertEqual("shadow-eval-v1", record.formula_version)
        self.assertEqual("model-benchmark-v1", record.benchmark_version)
        self.assertEqual(metadata, record.model_output_metadata)
        self.assertEqual(metrics, record.metrics)
        self.assertFalse(record.affects_production)

    def test_shadow_records_copy_input_metadata_and_metrics(self) -> None:
        metadata = {"output_hash": "b" * 64, "schema_version": "shadow-output-v1"}
        metrics = {"schema_pass_rate": Decimal("1.0")}

        record = create_shadow_mode_record(
            production_recommendation_id="recommendation-prod-1",
            strategy_id="strategy-ai-infra-core",
            data_snapshot_ids=("market-snapshot-1",),
            run_artifact_ids=("shadow-eval-run-1",),
            model_run_id="model-run-shadow-1",
            shadow_output_id="shadow-output-1",
            formula_version="shadow-eval-v1",
            benchmark_version="model-benchmark-v1",
            model_output_metadata=metadata,
            metrics=metrics,
            created_at=NOW,
        )
        metadata["candidate_action"] = "trim"
        metrics["schema_pass_rate"] = Decimal("0.0")

        self.assertNotIn("candidate_action", record.model_output_metadata)
        self.assertEqual(Decimal("1.0"), record.metrics["schema_pass_rate"])

    def test_shadow_record_rejects_missing_audit_links(self) -> None:
        with self.assertRaisesRegex(ValueError, "data_snapshot_ids must not be empty"):
            create_shadow_mode_record(
                production_recommendation_id="recommendation-prod-1",
                strategy_id="strategy-ai-infra-core",
                data_snapshot_ids=(),
                run_artifact_ids=("shadow-eval-run-1",),
                model_run_id="model-run-shadow-1",
                shadow_output_id="shadow-output-1",
                formula_version="shadow-eval-v1",
                benchmark_version="model-benchmark-v1",
                model_output_metadata={"output_hash": "b" * 64},
                metrics={"schema_pass_rate": Decimal("1.0")},
                created_at=NOW,
            )

        with self.assertRaisesRegex(ValueError, "model_output_metadata must not be empty"):
            create_shadow_mode_record(
                production_recommendation_id="recommendation-prod-1",
                strategy_id="strategy-ai-infra-core",
                data_snapshot_ids=("market-snapshot-1",),
                run_artifact_ids=("shadow-eval-run-1",),
                model_run_id="model-run-shadow-1",
                shadow_output_id="shadow-output-1",
                formula_version="shadow-eval-v1",
                benchmark_version="model-benchmark-v1",
                model_output_metadata={},
                metrics={"schema_pass_rate": Decimal("1.0")},
                created_at=NOW,
            )

    def test_evaluation_modules_do_not_import_model_clients_or_order_execution(self) -> None:
        forbidden = (
            "from azure",
            "import azure",
            "from openai",
            "import openai",
            "from anthropic",
            "import anthropic",
            "place_order",
            "submit_order",
            "broker_client",
            "live_order",
            "order_execution",
        )
        offenders: list[str] = []
        package_root = CORE_SRC / "ai_infra_fund_core" / "evaluation"
        for path in package_root.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                if pattern in text:
                    offenders.append(f"{path.relative_to(ROOT)} contains {pattern}")

        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
