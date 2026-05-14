from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Phase10EquityIntelligenceMigrationTests(unittest.TestCase):
    def test_phase10_migration_defines_equity_source_and_snapshot_tables(self) -> None:
        migration_path = ROOT / "services" / "api" / "migrations" / "0002_phase10_equity_intelligence.sql"
        lineage_migration_path = ROOT / "services" / "api" / "migrations" / "0003_phase10_event_lineage.sql"

        sql = migration_path.read_text(encoding="utf-8")
        lineage_sql = lineage_migration_path.read_text(encoding="utf-8")

        required_snippets = [
            "CREATE TABLE IF NOT EXISTS core.watched_equities",
            "CREATE TABLE IF NOT EXISTS evidence.source_registry",
            "CREATE TABLE IF NOT EXISTS evidence.source_frontier_urls",
            "CREATE TABLE IF NOT EXISTS evidence.source_refresh_jobs",
            "CREATE TABLE IF NOT EXISTS evidence.crawl_frontier_queue",
            "CREATE TABLE IF NOT EXISTS evidence.source_raw_captures",
            "CREATE TABLE IF NOT EXISTS signals.equity_events",
            "CREATE TABLE IF NOT EXISTS signals.sentiment_snapshots",
            "CREATE TABLE IF NOT EXISTS signals.technical_snapshots",
            "CREATE TABLE IF NOT EXISTS signals.fundamental_snapshots",
            "CREATE TABLE IF NOT EXISTS audit.equity_intelligence_runs",
            "status TEXT NOT NULL CHECK (status IN ('queued', 'leased', 'captured', 'retry', 'failed', 'skipped'))",
            "lease_expires_at TIMESTAMPTZ",
            "next_attempt_at TIMESTAMPTZ",
            "priority INTEGER NOT NULL DEFAULT 0",
            "embedding vector(1024)",
            "UNIQUE (source_id, url_hash)",
        ]

        missing = [snippet for snippet in required_snippets if snippet not in sql]
        self.assertEqual([], missing)

        lineage_snippets = [
            "ALTER TABLE signals.equity_events",
            "ADD COLUMN IF NOT EXISTS available_at TIMESTAMPTZ",
            "ADD COLUMN IF NOT EXISTS evidence_claim_ids TEXT[] NOT NULL DEFAULT '{}'",
            "ADD COLUMN IF NOT EXISTS model_run_ids TEXT[] NOT NULL DEFAULT '{}'",
            "ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'deterministic'",
            "equity_events_evidence_claim_ids_idx",
            "equity_events_model_run_ids_idx",
        ]
        missing_lineage = [snippet for snippet in lineage_snippets if snippet not in lineage_sql]
        self.assertEqual([], missing_lineage)


if __name__ == "__main__":
    unittest.main()
