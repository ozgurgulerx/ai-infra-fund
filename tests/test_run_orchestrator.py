from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.common import AdvisoryLabel  # noqa: E402
from ai_infra_fund_core.contracts.evaluation import RunArtifact  # noqa: E402
from ai_infra_fund_core.runs import AdvisoryRunInputs, orchestrate_advisory_run  # noqa: E402


STARTED_AT = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
COMPLETED_AT = datetime(2026, 5, 14, 12, 1, tzinfo=timezone.utc)
CREATED_AT = datetime(2026, 5, 14, 12, 2, tzinfo=timezone.utc)


class AdvisoryRunOrchestratorTests(unittest.TestCase):
    def test_stable_input_hash_and_run_id_are_derived_from_inputs(self) -> None:
        first = orchestrate_advisory_run(
            advisory_run_inputs(),
            started_at=STARTED_AT,
            completed_at=COMPLETED_AT,
            created_at=CREATED_AT,
        )
        second = orchestrate_advisory_run(
            advisory_run_inputs(),
            started_at=STARTED_AT,
            completed_at=COMPLETED_AT,
            created_at=CREATED_AT,
        )
        changed = orchestrate_advisory_run(
            advisory_run_inputs(evidence_ids=("evidence-1", "evidence-2")),
            started_at=STARTED_AT,
            completed_at=COMPLETED_AT,
            created_at=CREATED_AT,
        )

        self.assertEqual(first.artifact.inputs_hash, second.artifact.inputs_hash)
        self.assertEqual(first.artifact.run_id, second.artifact.run_id)
        self.assertNotEqual(first.artifact.inputs_hash, changed.artifact.inputs_hash)
        self.assertNotEqual(first.artifact.run_id, changed.artifact.run_id)

    def test_run_inputs_snapshot_mutable_sequences_for_stable_hashing(self) -> None:
        evidence_ids = ["evidence-1"]
        inputs = advisory_run_inputs(evidence_ids=evidence_ids)
        before = orchestrate_advisory_run(
            inputs,
            started_at=STARTED_AT,
            completed_at=COMPLETED_AT,
            created_at=CREATED_AT,
        )

        evidence_ids.append("evidence-2")
        after = orchestrate_advisory_run(
            inputs,
            started_at=STARTED_AT,
            completed_at=COMPLETED_AT,
            created_at=CREATED_AT,
        )

        self.assertEqual(before.artifact.inputs_hash, after.artifact.inputs_hash)
        self.assertEqual(before.artifact.run_id, after.artifact.run_id)

    def test_successful_run_returns_run_artifact_and_preserves_traceability(self) -> None:
        result = orchestrate_advisory_run(
            advisory_run_inputs(),
            started_at=STARTED_AT,
            completed_at=COMPLETED_AT,
            created_at=CREATED_AT,
        )

        self.assertIsInstance(result.artifact, RunArtifact)
        self.assertEqual("succeeded", result.artifact.status)
        self.assertEqual("controlled_advisory_run", result.artifact.run_type)
        self.assertEqual(STARTED_AT, result.artifact.started_at)
        self.assertEqual(COMPLETED_AT, result.artifact.completed_at)
        self.assertEqual(CREATED_AT, result.artifact.created_at)
        self.assertTrue(result.artifact.run_id.startswith("advisory-run-"))
        self.assertTrue(result.artifact.artifact_uri.endswith(result.artifact.run_id))
        self.assertIsNone(result.artifact.error_summary)
        self.assertIsNotNone(result.artifact.output_hash)

        self.assertIsNotNone(result.traceability)
        self.assertEqual(("evidence-1",), result.traceability.evidence_ids)
        self.assertEqual(("claim-1", "claim-2"), result.traceability.claim_ids)
        self.assertEqual(("model-run-summary", "model-run-review"), result.traceability.model_run_ids)
        self.assertEqual("signal-bundle-1", result.traceability.signal_bundle_id)
        self.assertEqual("target-weights-1", result.traceability.target_weights_id)
        self.assertEqual("recommendation-1", result.traceability.recommendation_id)
        self.assertEqual("audit-1", result.traceability.audit_id)
        self.assertEqual("evaluation-1", result.traceability.evaluation_id)
        self.assertEqual("backtest-1", result.traceability.backtest_run_id)
        self.assertEqual(AdvisoryLabel.ADVISORY_ONLY, result.traceability.advisory_label)

    def test_missing_provenance_or_audit_inputs_fail_closed(self) -> None:
        result = orchestrate_advisory_run(
            advisory_run_inputs(
                evidence_ids=(),
                claim_ids=(),
                model_run_ids=(),
                signal_bundle_id="",
                target_weights_id="",
                recommendation_id="",
                audit_id="",
                evaluation_id=None,
                backtest_run_id=None,
            ),
            started_at=STARTED_AT,
            completed_at=COMPLETED_AT,
            created_at=CREATED_AT,
        )

        self.assertEqual("failed", result.artifact.status)
        self.assertIsNone(result.traceability)
        self.assertIsNone(result.artifact.output_hash)
        self.assertIsNone(result.artifact.artifact_uri)
        self.assertIsNotNone(result.artifact.error_summary)
        self.assertIn("evidence_ids", result.artifact.error_summary)
        self.assertIn("claim_ids", result.artifact.error_summary)
        self.assertIn("model_run_ids", result.artifact.error_summary)
        self.assertIn("signal_bundle_id", result.artifact.error_summary)
        self.assertIn("target_weights_id", result.artifact.error_summary)
        self.assertIn("recommendation_id", result.artifact.error_summary)
        self.assertIn("audit_id", result.artifact.error_summary)
        self.assertIn("evaluation_id or backtest_run_id", result.artifact.error_summary)

    def test_non_advisory_label_fails_closed(self) -> None:
        result = orchestrate_advisory_run(
            advisory_run_inputs(advisory_label="execution_ready"),
            started_at=STARTED_AT,
            completed_at=COMPLETED_AT,
            created_at=CREATED_AT,
        )

        self.assertEqual("failed", result.artifact.status)
        self.assertIsNone(result.artifact.output_hash)
        self.assertIsNone(result.traceability)
        self.assertIsNotNone(result.artifact.error_summary)
        self.assertIn("advisory_label", result.artifact.error_summary)

    def test_run_modules_do_not_import_models_cloud_clients_or_execution_surface(self) -> None:
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
            "model_routing",
        )
        offenders: list[str] = []
        package_root = CORE_SRC / "ai_infra_fund_core" / "runs"
        for path in package_root.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                if pattern in text:
                    offenders.append(f"{path.relative_to(ROOT)} contains {pattern}")

        self.assertEqual([], offenders)


def advisory_run_inputs(**overrides: object) -> AdvisoryRunInputs:
    data = {
        "evidence_ids": ("evidence-1",),
        "claim_ids": ("claim-1", "claim-2"),
        "model_run_ids": ("model-run-summary", "model-run-review"),
        "signal_bundle_id": "signal-bundle-1",
        "target_weights_id": "target-weights-1",
        "recommendation_id": "recommendation-1",
        "audit_id": "audit-1",
        "evaluation_id": "evaluation-1",
        "backtest_run_id": "backtest-1",
        "advisory_label": AdvisoryLabel.ADVISORY_ONLY,
    }
    data.update(overrides)
    return AdvisoryRunInputs(**data)


if __name__ == "__main__":
    unittest.main()
