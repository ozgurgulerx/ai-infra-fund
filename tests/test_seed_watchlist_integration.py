from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, API_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_worker.crawl.seed import seed_watchlist  # noqa: E402


DATABASE_URL = os.getenv(
    "AI_INFRA_FUND_DATABASE_URL",
    "postgresql://ai_infra_fund:ai_infra_fund@localhost:5432/ai_infra_fund",
)


@unittest.skipUnless(
    os.getenv("AI_INFRA_FUND_DATABASE_URL"),
    "set AI_INFRA_FUND_DATABASE_URL to enable integration tests",
)
class SeedWatchlistIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = psycopg.connect(DATABASE_URL)
        self.addCleanup(self.connection.close)

    def test_seeds_watched_equities_sources_frontier_and_queue_idempotently(
        self,
    ) -> None:
        now = datetime.now(tz=timezone.utc).replace(microsecond=0)
        watchlist_path = ROOT / "config" / "ai_equity_watchlist.yaml"

        report_one = seed_watchlist(
            self.connection, watchlist_path=watchlist_path, now=now
        )
        report_two = seed_watchlist(
            self.connection, watchlist_path=watchlist_path, now=now
        )

        # Idempotent: same record counts both runs.
        self.assertEqual(report_one, report_two)
        self.assertGreaterEqual(report_one.watched_equities, 10)
        self.assertGreaterEqual(report_one.sources, 1)
        self.assertGreaterEqual(report_one.frontier_urls, report_one.watched_equities)
        self.assertEqual(report_one.queue_items, report_one.frontier_urls)

        # DB now reflects the seeded watchlist.
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM core.watched_equities WHERE active = TRUE;"
            )
            row = cursor.fetchone()
            assert row is not None
            (active_count,) = row
            self.assertGreaterEqual(int(active_count), report_one.watched_equities)

            cursor.execute(
                "SELECT COUNT(*) FROM evidence.source_registry "
                "WHERE source_id LIKE 'source-host-%' OR source_id LIKE 'source-api-%';"
            )
            row = cursor.fetchone()
            assert row is not None
            (seeded_sources,) = row
            self.assertGreaterEqual(int(seeded_sources), report_one.sources)

            cursor.execute("SELECT COUNT(*) FROM evidence.source_frontier_urls;")
            row = cursor.fetchone()
            assert row is not None
            (frontier_count,) = row
            self.assertGreaterEqual(int(frontier_count), report_one.frontier_urls)

            cursor.execute("SELECT COUNT(*) FROM evidence.crawl_frontier_queue;")
            row = cursor.fetchone()
            assert row is not None
            (queue_count,) = row
            self.assertGreaterEqual(int(queue_count), report_one.queue_items)


if __name__ == "__main__":
    unittest.main()
