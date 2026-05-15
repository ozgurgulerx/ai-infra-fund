from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Phase11MacroSnapshotsMigrationTests(unittest.TestCase):
    def test_migration_defines_table_constraints_and_indexes(self) -> None:
        migration_path = (
            ROOT
            / "services"
            / "api"
            / "migrations"
            / "0008_phase11_macro_snapshots.sql"
        )
        self.assertTrue(
            migration_path.is_file(), f"missing migration: {migration_path}"
        )
        sql = migration_path.read_text(encoding="utf-8")

        required_snippets = [
            "CREATE TABLE IF NOT EXISTS signals.macro_snapshots",
            "snapshot_id TEXT PRIMARY KEY",
            "series_id TEXT NOT NULL",
            "source_id TEXT NOT NULL",
            "REFERENCES evidence.source_registry(source_id)",
            "as_of TIMESTAMPTZ NOT NULL",
            "value NUMERIC",
            "unit TEXT NOT NULL",
            "vintage_id TEXT NOT NULL",
            "content_hash TEXT NOT NULL UNIQUE",
            "ingested_at TIMESTAMPTZ NOT NULL",
            "UNIQUE (series_id, as_of, vintage_id)",
            "macro_snapshots_series_asof_idx",
        ]
        missing = [snippet for snippet in required_snippets if snippet not in sql]
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
