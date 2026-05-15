from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Phase11TickerExternalIdsMigrationTests(unittest.TestCase):
    def test_migration_defines_table_and_indexes(self) -> None:
        migration_path = (
            ROOT
            / "services"
            / "api"
            / "migrations"
            / "0007_phase11_ticker_external_ids.sql"
        )
        self.assertTrue(
            migration_path.is_file(), f"missing migration: {migration_path}"
        )
        sql = migration_path.read_text(encoding="utf-8")

        required_snippets = [
            "CREATE TABLE IF NOT EXISTS evidence.ticker_external_ids",
            "ticker TEXT NOT NULL",
            "REFERENCES core.watched_equities(ticker)",
            "system TEXT NOT NULL",
            "external_id TEXT NOT NULL",
            "PRIMARY KEY (ticker, system)",
            "updated_at TIMESTAMPTZ NOT NULL",
            "ticker_external_ids_system_external_idx",
        ]
        missing = [snippet for snippet in required_snippets if snippet not in sql]
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
