from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import stat
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)

PREREQUISITE_COLUMNS = (
    "evidence_id",
    "evidence_content_hash",
    "claim_id",
    "extracted_by_model_run_id",
    "signal_bundle_id",
    "signal_input_snapshot_hash",
    "target_weights_id",
    "target_weights_generated_by",
    "target_weights_validation_status",
    "recommendation_id",
    "advisory_label",
    "recommendation_evidence_ids",
    "recommendation_model_run_ids",
    "recommendation_score_breakdown",
    "recommendation_final_payload",
    "audit_id",
    "audit_schema_valid",
    "audit_deterministic_checks",
    "backtest_run_id",
    "backtest_status",
    "backtest_summary_metrics",
    "evaluation_run_artifact_id",
    "evaluation_run_status",
    "evaluation_inputs_hash",
    "evaluation_output_hash",
)


class WorkerAdvisoryRunTests(unittest.TestCase):
    def test_complete_demo_prerequisites_write_succeeded_advisory_demo_artifact(self) -> None:
        from ai_infra_fund_worker.advisory_run import run_advisory_demo

        connection = FakeConnection(complete_prerequisite_row())

        first = run_advisory_demo(connection)
        second = run_advisory_demo(connection)

        self.assertEqual("succeeded", first["status"])
        self.assertEqual(0, first["exit_code"])
        self.assertEqual("advisory_demo", first["run_type"])
        self.assertEqual(first["run_id"], second["run_id"])
        self.assertEqual(first["inputs_hash"], second["inputs_hash"])
        self.assertEqual(first["output_hash"], second["output_hash"])
        self.assertEqual([], first["missing_prerequisites"])
        self.assertEqual(2, connection.commit_count)

        select_statement, select_params = connection.cursor_instance.executions[0]
        self.assertIn("FROM expected", select_statement)
        self.assertIn("evidence.evidence_items", select_statement)
        self.assertIn("evidence.evidence_claims", select_statement)
        self.assertIn("signals.signal_bundles", select_statement)
        self.assertIn("recommendations.target_weights", select_statement)
        self.assertIn("recommendations.recommendation_artifacts", select_statement)
        self.assertIn("recommendations.recommendation_audits", select_statement)
        self.assertIn("audit.backtest_runs", select_statement)
        self.assertIn("audit.run_artifacts", select_statement)
        self.assertEqual(
            (
                "evidence-demo-ai-infra-nvda",
                "claim-demo-ai-infra-nvda-demand",
                "signal-bundle-demo-nvda",
                "target-weights-demo-ai-infra",
                "recommendation-demo-nvda",
                "recommendation-audit-demo-nvda",
                "evaluation-demo-ai-infra",
            ),
            select_params,
        )

        insert_statement, insert_params = connection.cursor_instance.insertions[0]
        self.assertIn("INSERT INTO audit.run_artifacts", insert_statement)
        self.assertIn("ON CONFLICT (run_id)", insert_statement)
        self.assertEqual(first["run_id"], insert_params[0])
        self.assertEqual("advisory_demo", insert_params[1])
        self.assertEqual(first["inputs_hash"], insert_params[4])
        self.assertEqual(first["output_hash"], insert_params[5])
        self.assertEqual(first["artifact_uri"], insert_params[6])
        self.assertIn("recommendation_id=recommendation-demo-nvda", first["artifact_uri"])
        self.assertIn("audit_id=recommendation-audit-demo-nvda", first["artifact_uri"])
        self.assertIn("evaluation_id=evaluation-demo-ai-infra", first["artifact_uri"])
        self.assertIn("backtest_run_id=evaluation-demo-ai-infra", first["artifact_uri"])
        self.assertIn("advisory_label=advisory_only", first["artifact_uri"])
        self.assertEqual("succeeded", insert_params[7])
        self.assertIsNone(insert_params[8])

        for statement, params in connection.cursor_instance.executions:
            self.assertIsInstance(params, tuple)
            upper_statement = statement.upper()
            self.assertNotIn("PLACE_ORDER", upper_statement)
            self.assertNotIn("BROKER", upper_statement)
            self.assertNotIn("EXECUTION", upper_statement)

    def test_missing_prerequisite_writes_failed_artifact_and_returns_nonzero(self) -> None:
        from ai_infra_fund_worker.advisory_run import run_advisory_demo

        row = dict(zip(PREREQUISITE_COLUMNS, complete_prerequisite_row(), strict=True))
        row["claim_id"] = None
        row["backtest_status"] = "failed"
        connection = FakeConnection(tuple(row[column] for column in PREREQUISITE_COLUMNS))

        result = run_advisory_demo(connection)

        self.assertEqual("failed", result["status"])
        self.assertEqual(1, result["exit_code"])
        self.assertEqual("advisory_demo", result["run_type"])
        self.assertEqual(["claim", "evaluation/backtest"], result["missing_prerequisites"])
        self.assertIsNone(result["output_hash"])
        self.assertEqual(1, connection.commit_count)

        _statement, insert_params = connection.cursor_instance.insertions[0]
        self.assertEqual(result["run_id"], insert_params[0])
        self.assertEqual("advisory_demo", insert_params[1])
        self.assertEqual("failed", insert_params[7])
        self.assertIn("claim", insert_params[8])
        self.assertIn("evaluation/backtest", insert_params[8])

    def test_worker_script_invokes_worker_module_only(self) -> None:
        script = ROOT / "scripts" / "run_advisory_demo.sh"

        self.assertTrue(script.is_file())
        self.assertTrue(script.stat().st_mode & stat.S_IXUSR)

        text = script.read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", text)
        self.assertIn("docker compose build worker", text)
        self.assertIn("docker compose run --rm worker", text)
        self.assertIn("python -m ai_infra_fund_worker.advisory_run", text)
        self.assertNotIn("ai_infra_fund_api", text)
        self.assertNotIn("curl", text)

    def test_advisory_run_module_stays_local_deterministic_and_advisory_only(self) -> None:
        module = ROOT / "services" / "worker" / "src" / "ai_infra_fund_worker" / "advisory_run.py"
        text = module.read_text(encoding="utf-8").lower()

        forbidden = [
            "openai",
            "azure",
            "requests",
            "httpx",
            "marketdata",
            "place_order",
            "submit_order",
            "broker",
            "order_execution",
            "ai_infra_fund_api",
        ]
        offenders = [word for word in forbidden if word in text]
        self.assertEqual([], offenders)


def complete_prerequisite_row() -> tuple[object, ...]:
    return (
        "evidence-demo-ai-infra-nvda",
        "a" * 64,
        "claim-demo-ai-infra-nvda-demand",
        "model-run-demo-local-review",
        "signal-bundle-demo-nvda",
        "b" * 64,
        "target-weights-demo-ai-infra",
        "deterministic_demo_seed",
        "validated",
        "recommendation-demo-nvda",
        "advisory_only",
        ["evidence-demo-ai-infra-nvda"],
        ["model-run-demo-local-review"],
        {"combined_score": "0.74"},
        {"summary": "Accumulate NVDA as an advisory-only demo chain."},
        "recommendation-audit-demo-nvda",
        True,
        {
            "advisory_label_present": True,
            "target_weights_generated_by_deterministic_code": True,
        },
        "evaluation-demo-ai-infra",
        "succeeded",
        {"recommendation_id": "recommendation-demo-nvda"},
        "run-demo-advisory-chain",
        "succeeded",
        "c" * 64,
        "d" * 64,
    )


class FakeCursor:
    def __init__(self, prerequisite_row: tuple[object, ...]) -> None:
        self._prerequisite_row = prerequisite_row
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.insertions: list[tuple[str, tuple[object, ...]]] = []
        self.description: tuple[tuple[str], ...] = ()
        self.row: tuple[object, ...] | None = None

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        normalized_params = params if params is not None else ()
        self.executions.append((statement, normalized_params))
        if "INSERT INTO audit.run_artifacts" in statement:
            self.insertions.append((statement, normalized_params))
            return

        self.description = tuple((column,) for column in PREREQUISITE_COLUMNS)
        self.row = self._prerequisite_row

    def fetchone(self) -> tuple[object, ...] | None:
        return self.row

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self, prerequisite_row: tuple[object, ...]) -> None:
        self.cursor_instance = FakeCursor(prerequisite_row)
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


if __name__ == "__main__":
    unittest.main()
