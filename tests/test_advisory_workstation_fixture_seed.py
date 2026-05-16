from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))


class AdvisoryWorkstationFixtureSeedTests(unittest.TestCase):
    def test_fixture_seed_persists_full_advisory_read_model(self) -> None:
        from ai_infra_fund_worker.fixture_advisory_run import seed_fixture_advisory_run

        connection = FakeConnection()
        fixture_path = (
            ROOT / "docs" / "mock_data" / "situational_awareness_brief.example.json"
        )

        result = seed_fixture_advisory_run(connection, fixture_path)

        self.assertEqual("succeeded", result["status"])
        self.assertEqual("fixture_advisory", result["run_type"])
        self.assertEqual("advisory_only", result["advisory_label"])
        self.assertGreater(result["source_signal_count"], 0)
        self.assertGreater(result["market_event_count"], 0)
        self.assertGreater(result["trading_advisory_count"], 0)
        self.assertTrue(str(result["run_id"]).startswith("run-fixture-advisory-"))

        statements = "\n".join(
            statement for statement, _params in connection.cursor_instance.executions
        )
        for table_name in (
            "audit.model_runs",
            "audit.run_artifacts",
            "evidence.evidence_items",
            "analyst.source_signals",
            "analyst.market_events",
            "analyst.segment_impacts",
            "analyst.equity_impact_assessments",
            "analyst.valuation_contexts",
            "analyst.macro_regime_snapshots",
            "analyst.trading_advisories",
            "analyst.analyst_briefs",
        ):
            self.assertIn(table_name, statements)

        self.assertEqual(1, connection.commit_count)
        for statement, params in connection.cursor_instance.executions:
            self.assertIsInstance(params, tuple)
            self.assertNotIn((), params)
            combined = f"{statement} {params}".lower()
            self.assertNotIn("place_order", combined)
            self.assertNotIn("submit_order", combined)
            self.assertNotIn("broker", combined)

    def test_seed_script_exists_and_invokes_fixture_worker_module(self) -> None:
        script = ROOT / "scripts" / "run_fixture_advisory_once.sh"

        self.assertTrue(script.is_file())
        text = script.read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", text)
        self.assertIn("python -m ai_infra_fund_worker.fixture_advisory_run", text)
        self.assertIn("situational_awareness_brief.example.json", text)
        self.assertNotIn("curl", text)

    def test_fixture_seed_accepts_documented_second_order_tickers_field(self) -> None:
        from ai_infra_fund_worker.fixture_advisory_run import seed_fixture_advisory_run

        fixture_path = (
            ROOT / "docs" / "mock_data" / "situational_awareness_brief.example.json"
        )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        segment = fixture["segment_impacts"][0]
        segment.pop("derivative_tickers", None)
        segment["second_order_tickers"] = ["DOC2"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            local_fixture_path = Path(tmp_dir) / "brief.json"
            local_fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
            connection = FakeConnection()

            seed_fixture_advisory_run(connection, local_fixture_path)

        segment_params = next(
            params
            for statement, params in connection.cursor_instance.executions
            if "INSERT INTO analyst.segment_impacts" in statement
        )
        self.assertEqual(["DOC2"], segment_params[3])


class FakeCursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params if params is not None else ()))

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


if __name__ == "__main__":
    unittest.main()
