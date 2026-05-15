from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Phase10CrawlLogsMigrationTests(unittest.TestCase):
    def test_crawl_logs_migration_defines_table_and_indexes(self) -> None:
        migration_path = (
            ROOT / "services" / "api" / "migrations" / "0004_phase10_crawl_logs.sql"
        )

        sql = migration_path.read_text(encoding="utf-8")

        required_snippets = [
            "CREATE TABLE IF NOT EXISTS evidence.crawl_logs",
            "attempt_id TEXT PRIMARY KEY",
            "frontier_url_id TEXT",
            "REFERENCES evidence.source_frontier_urls(frontier_url_id)",
            "ticker TEXT",
            "REFERENCES core.watched_equities(ticker)",
            "source_id TEXT",
            "REFERENCES evidence.source_registry(source_id)",
            "url TEXT NOT NULL",
            "attempted_at TIMESTAMPTZ NOT NULL",
            "fetch_method TEXT NOT NULL CHECK (fetch_method IN ('http_get', 'http_head', 'http_304', 'stub', 'error'))",
            "http_status INTEGER",
            "latency_ms INTEGER",
            "bytes_fetched INTEGER",
            "capture_id TEXT",
            "REFERENCES evidence.source_raw_captures(capture_id)",
            "error_summary TEXT",
            "created_at TIMESTAMPTZ NOT NULL DEFAULT now()",
            "crawl_logs_ticker_attempted_idx",
            "crawl_logs_attempted_idx",
        ]

        missing = [snippet for snippet in required_snippets if snippet not in sql]
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
