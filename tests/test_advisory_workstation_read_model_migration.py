from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AdvisoryWorkstationReadModelMigrationTests(unittest.TestCase):
    def test_migration_defines_fixture_backed_read_model_tables(self) -> None:
        migration_dir = ROOT / "services" / "api" / "migrations"
        sql = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(migration_dir.glob("*.sql"))
        )

        required_snippets = [
            "CREATE SCHEMA IF NOT EXISTS analyst",
            "CREATE TABLE IF NOT EXISTS analyst.source_signals",
            "CREATE TABLE IF NOT EXISTS analyst.market_events",
            "CREATE TABLE IF NOT EXISTS analyst.segment_impacts",
            "CREATE TABLE IF NOT EXISTS analyst.equity_impact_assessments",
            "CREATE TABLE IF NOT EXISTS analyst.valuation_contexts",
            "CREATE TABLE IF NOT EXISTS analyst.macro_regime_snapshots",
            "CREATE TABLE IF NOT EXISTS analyst.risk_regime_updates",
            "CREATE TABLE IF NOT EXISTS analyst.trading_advisories",
            "CREATE TABLE IF NOT EXISTS analyst.trade_plans",
            "CREATE TABLE IF NOT EXISTS analyst.portfolio_exposure_snapshots",
            "CREATE TABLE IF NOT EXISTS analyst.llm_analyst_notes",
            "CREATE TABLE IF NOT EXISTS analyst.shadow_analyst_drafts",
            "CREATE TABLE IF NOT EXISTS analyst.shadow_analyst_draft_reviews",
            "CREATE TABLE IF NOT EXISTS analyst.analyst_briefs",
            "evidence_ids TEXT[] NOT NULL",
            "model_run_ids TEXT[] NOT NULL DEFAULT '{}'",
            "advisory_label TEXT NOT NULL DEFAULT 'advisory_only'",
            "manual_journal_only BOOLEAN NOT NULL DEFAULT true CHECK (manual_journal_only = true)",
            "positions_json JSONB NOT NULL DEFAULT '[]'",
            "payload_json JSONB NOT NULL DEFAULT '{}'",
            "CHECK (advisory_label = 'advisory_only')",
            "source_model_run_id TEXT NOT NULL REFERENCES audit.model_runs(model_run_id)",
            "scope TEXT NOT NULL CHECK (scope IN ('daily', 'ticker'))",
            "status TEXT NOT NULL CHECK (status IN ('review_required', 'rejected', 'fallback', 'accepted_for_publication', 'denied'))",
            "decision TEXT NOT NULL CHECK (decision IN ('accepted_for_publication', 'rejected', 'keep_review_required'))",
            "draft_quality_score NUMERIC NOT NULL CHECK (draft_quality_score >= 0 AND draft_quality_score <= 100)",
            "CHECK (decision <> 'accepted_for_publication' OR accepted_payload_json ->> 'advisory_label' = 'advisory_only')",
        ]
        missing = [snippet for snippet in required_snippets if snippet not in sql]

        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
