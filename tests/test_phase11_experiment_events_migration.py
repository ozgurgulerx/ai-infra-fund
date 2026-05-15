from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Phase11ExperimentEventsMigrationTests(unittest.TestCase):
    def test_migration_file_creates_audit_experiment_events_table(self) -> None:
        migration_path = (
            ROOT
            / "services"
            / "api"
            / "migrations"
            / "0006_phase11_experiment_events.sql"
        )
        self.assertTrue(
            migration_path.is_file(), f"missing migration: {migration_path}"
        )
        sql = migration_path.read_text(encoding="utf-8")

        required_snippets = [
            "CREATE TABLE IF NOT EXISTS audit.experiment_events",
            "event_id TEXT PRIMARY KEY CHECK (event_id LIKE 'audit-evt-%')",
            "kind TEXT NOT NULL",
            "severity TEXT NOT NULL CHECK (severity IN ('info','warn','error'))",
            "payload JSONB NOT NULL",
            "occurred_at TIMESTAMPTZ NOT NULL",
            "experiment_events_occurred_at_idx",
            "experiment_events_run_id_idx",
            "experiment_events_kind_idx",
        ]
        missing = [snippet for snippet in required_snippets if snippet not in sql]
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
