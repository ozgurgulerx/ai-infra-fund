from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.equity_intelligence.seeder import (  # noqa: E402
    PRIORITY_SCORES,
    build_crawl_queue_items,
    build_frontier_url_records,
    build_source_records,
    build_watched_equity_records,
)
from ai_infra_fund_core.local_inputs.watchlist import (  # noqa: E402
    AIEquityWatchlist,
    AIEquityWatchlistEntry,
)


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


def _watchlist() -> AIEquityWatchlist:
    return AIEquityWatchlist(
        version=1,
        entries=(
            AIEquityWatchlistEntry(
                ticker="NVDA",
                company_name="NVIDIA",
                themes=("ai_accelerators",),
                sector_tags=("semiconductors",),
                source_urls=(
                    "https://www.nvidia.com/en-us/data-center/",
                    "https://investor.nvidia.com/",
                ),
                priority="critical",
            ),
            AIEquityWatchlistEntry(
                ticker="MSFT",
                company_name="Microsoft",
                themes=("ai_cloud",),
                sector_tags=("cloud_platforms",),
                source_urls=("https://www.microsoft.com/en-us/investor",),
                priority="high",
            ),
            AIEquityWatchlistEntry(
                ticker="IONQ",
                company_name="IonQ",
                themes=("quantum_compute",),
                sector_tags=("quantum_technology",),
                source_urls=("https://investors.ionq.com/",),
                priority="low",
            ),
        ),
    )


class BuildWatchedEquityRecordsTests(unittest.TestCase):
    def test_maps_priority_string_to_numeric_score(self) -> None:
        self.assertEqual(
            {"critical": 100, "high": 75, "medium": 50, "low": 25}, PRIORITY_SCORES
        )

    def test_returns_one_record_per_watchlist_entry_with_priority_score(self) -> None:
        records = build_watched_equity_records(_watchlist(), now=NOW)

        tickers = [r.ticker for r in records]
        priorities = {r.ticker: r.priority for r in records}
        self.assertEqual(["NVDA", "MSFT", "IONQ"], tickers)
        self.assertEqual({"NVDA": 100, "MSFT": 75, "IONQ": 25}, priorities)
        for record in records:
            self.assertEqual("equity", record.asset_type)
            self.assertTrue(record.active)
            self.assertEqual(NOW, record.created_at)
            self.assertEqual(NOW, record.updated_at)


class BuildSourceRecordsTests(unittest.TestCase):
    def test_creates_one_record_per_distinct_hostname(self) -> None:
        records = build_source_records(_watchlist(), now=NOW)
        hostnames = sorted({r.metadata["hostname"] for r in records})

        self.assertEqual(
            [
                "investor.nvidia.com",
                "investors.ionq.com",
                "www.microsoft.com",
                "www.nvidia.com",
            ],
            hostnames,
        )
        for record in records:
            self.assertEqual("company_ir_press", record.source_type)
            self.assertEqual("public_evidence", record.data_class)
            self.assertEqual("public", record.license_label)
            self.assertTrue(record.active)

    def test_source_id_is_stable_slug_of_hostname(self) -> None:
        records = {
            r.metadata["hostname"]: r
            for r in build_source_records(_watchlist(), now=NOW)
        }
        self.assertEqual(
            "source-host-investor-nvidia-com", records["investor.nvidia.com"].source_id
        )
        self.assertEqual(
            "source-host-www-nvidia-com", records["www.nvidia.com"].source_id
        )


class BuildFrontierUrlRecordsTests(unittest.TestCase):
    def test_creates_one_record_per_ticker_source_url(self) -> None:
        records = build_frontier_url_records(_watchlist(), now=NOW)
        self.assertEqual(4, len(records))
        tickers_by_url = {r.url: r.ticker for r in records}
        self.assertEqual(
            "NVDA", tickers_by_url["https://www.nvidia.com/en-us/data-center/"]
        )
        self.assertEqual("NVDA", tickers_by_url["https://investor.nvidia.com/"])
        self.assertEqual(
            "MSFT", tickers_by_url["https://www.microsoft.com/en-us/investor"]
        )
        self.assertEqual("IONQ", tickers_by_url["https://investors.ionq.com/"])

    def test_priority_inherits_from_watchlist_priority(self) -> None:
        records = build_frontier_url_records(_watchlist(), now=NOW)
        by_ticker = {r.ticker: r.priority for r in records}
        self.assertEqual(100, by_ticker["NVDA"])
        self.assertEqual(75, by_ticker["MSFT"])
        self.assertEqual(25, by_ticker["IONQ"])

    def test_url_hash_is_deterministic_and_url_specific(self) -> None:
        records = build_frontier_url_records(_watchlist(), now=NOW)
        hashes = {r.url: r.url_hash for r in records}
        self.assertEqual(len({h for h in hashes.values()}), len(hashes))
        for h in hashes.values():
            self.assertEqual(64, len(h))
            int(h, 16)

    def test_frontier_url_status_is_queued_initially_with_max_attempts(self) -> None:
        records = build_frontier_url_records(_watchlist(), now=NOW)
        for record in records:
            self.assertEqual("queued", record.status)
            self.assertEqual(0, record.attempt_count)
            self.assertEqual(3, record.max_attempts)
            self.assertEqual(NOW, record.discovered_at)
            self.assertEqual(NOW, record.next_attempt_at)

    def test_source_id_links_to_matching_source_record(self) -> None:
        source_ids = {r.source_id for r in build_source_records(_watchlist(), now=NOW)}
        for record in build_frontier_url_records(_watchlist(), now=NOW):
            self.assertIn(record.source_id, source_ids)


class BuildCrawlQueueItemsTests(unittest.TestCase):
    def test_one_queue_item_per_frontier_url(self) -> None:
        frontier_records = build_frontier_url_records(_watchlist(), now=NOW)
        queue_items = build_crawl_queue_items(frontier_records, now=NOW)
        self.assertEqual(len(frontier_records), len(queue_items))
        queue_frontier_ids = {q.frontier_url_id for q in queue_items}
        for record in frontier_records:
            self.assertIn(record.frontier_url_id, queue_frontier_ids)

    def test_queue_item_status_is_queued_and_priority_matches(self) -> None:
        frontier_records = build_frontier_url_records(_watchlist(), now=NOW)
        queue_items = {
            q.frontier_url_id: q
            for q in build_crawl_queue_items(frontier_records, now=NOW)
        }
        for record in frontier_records:
            queue = queue_items[record.frontier_url_id]
            self.assertEqual("queued", queue.status)
            self.assertEqual(record.priority, queue.priority)
            self.assertEqual(record.ticker, queue.ticker)
            self.assertEqual(NOW, queue.next_attempt_at)


if __name__ == "__main__":
    unittest.main()
