from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Phase11BacktestRequestsMigrationTests(unittest.TestCase):
    def test_migration_file_creates_audit_backtest_requests_table(self) -> None:
        migration_path = (
            ROOT
            / "services"
            / "api"
            / "migrations"
            / "0005_phase11_backtest_requests.sql"
        )
        self.assertTrue(
            migration_path.is_file(), f"missing migration: {migration_path}"
        )
        sql = migration_path.read_text(encoding="utf-8")

        required_snippets = [
            "CREATE TABLE IF NOT EXISTS audit.backtest_requests",
            "request_id TEXT PRIMARY KEY CHECK (request_id LIKE 'backtest-req-%')",
            "strategy_id TEXT NOT NULL",
            "dataset_snapshot_ids TEXT[] NOT NULL",
            "validation_protocol TEXT NOT NULL",
            "cost_assumptions JSONB NOT NULL",
            "pipeline_inputs JSONB NOT NULL",
            "formula_version TEXT NOT NULL",
            "model_run_id TEXT NOT NULL",
            "git_sha TEXT NOT NULL",
            "as_of TIMESTAMPTZ NOT NULL",
            "status TEXT NOT NULL CHECK (status IN ('queued','leased','running','succeeded','failed'))",
            "backtest_run_id TEXT",
            "backtest_requests_status_idx",
            "backtest_requests_strategy_idx",
        ]
        missing = [snippet for snippet in required_snippets if snippet not in sql]
        self.assertEqual([], missing)

    def test_followup_migration_repairs_existing_backtest_request_tables(self) -> None:
        migration_path = (
            ROOT
            / "services"
            / "api"
            / "migrations"
            / "0009_phase11_backtest_request_compatibility.sql"
        )
        self.assertTrue(
            migration_path.is_file(), f"missing migration: {migration_path}"
        )
        sql = migration_path.read_text(encoding="utf-8")

        required_snippets = [
            "ALTER TABLE audit.backtest_requests ADD COLUMN IF NOT EXISTS formula_version TEXT",
            "ALTER TABLE audit.backtest_requests ADD COLUMN IF NOT EXISTS model_run_id TEXT",
            "ALTER TABLE audit.backtest_requests ADD COLUMN IF NOT EXISTS git_sha TEXT",
            "ALTER COLUMN formula_version SET NOT NULL",
            "ALTER COLUMN model_run_id SET NOT NULL",
            "ALTER COLUMN git_sha SET NOT NULL",
        ]
        missing = [snippet for snippet in required_snippets if snippet not in sql]
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
