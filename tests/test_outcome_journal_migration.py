from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT
    / "services"
    / "api"
    / "migrations"
    / "0011_outcome_journal_read_model.sql"
)


class OutcomeJournalMigrationTests(unittest.TestCase):
    def test_migration_defines_advisory_only_outcome_journal_read_model(self) -> None:
        self.assertTrue(MIGRATION.is_file())
        sql = MIGRATION.read_text(encoding="utf-8")

        required_snippets = [
            "CREATE SCHEMA IF NOT EXISTS analyst",
            "CREATE TABLE IF NOT EXISTS analyst.outcome_journal_entries",
            "outcome_id TEXT PRIMARY KEY",
            "manual_journal_entry_id UUID NOT NULL",
            "advisory_id TEXT NOT NULL",
            "market_event_ids TEXT[] NOT NULL",
            "evidence_ids TEXT[] NOT NULL",
            "invalidation_flags TEXT[] NOT NULL DEFAULT '{}'",
            "risk_flags TEXT[] NOT NULL DEFAULT '{}'",
            "gross_pnl_amount NUMERIC",
            "net_pnl_amount NUMERIC",
            "pnl_percent NUMERIC",
            "pnl_attribution_method TEXT NOT NULL",
            "advisory_label TEXT NOT NULL DEFAULT 'advisory_only'",
            "CHECK (advisory_label = 'advisory_only')",
            "CHECK (cardinality(evidence_ids) > 0)",
            "CREATE INDEX IF NOT EXISTS outcome_journal_entries_advisory_id_idx",
            "CREATE INDEX IF NOT EXISTS outcome_journal_entries_market_event_ids_idx",
        ]

        missing = [snippet for snippet in required_snippets if snippet not in sql]
        self.assertEqual([], missing)

    def test_outcome_journal_schema_has_no_broker_order_or_execution_columns(self) -> None:
        sql = MIGRATION.read_text(encoding="utf-8")
        table_match = re.search(
            r"CREATE TABLE IF NOT EXISTS analyst\.outcome_journal_entries \((?P<body>.*?)\);",
            sql,
            re.DOTALL,
        )
        self.assertIsNotNone(table_match)
        table_body = table_match.group("body") if table_match else ""
        column_names = []
        for line in table_body.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("CHECK"):
                continue
            column_names.append(stripped.split()[0].lower())

        offenders = [
            column_name
            for column_name in column_names
            for forbidden in ("broker", "order", "execution", "execute")
            if forbidden in column_name
        ]
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
