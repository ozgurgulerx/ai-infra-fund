from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, API_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))


NOW = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)


WATCHLIST_YAML = """
version: 1
entries:
  - ticker: NVDA
    company_name: NVIDIA
    themes: [ai_accelerators]
    sector_tags: [semiconductors]
    source_urls: [https://investor.nvidia.com/]
    priority: critical
  - ticker: MSFT
    company_name: Microsoft
    themes: [ai_cloud]
    sector_tags: [cloud_platforms]
    source_urls: [https://www.microsoft.com/en-us/investor]
    priority: high
"""


SOURCE_REGISTRY_YAML = """
version: 1
sources:
  - source_id: source_sec_edgar
    source_name: SEC EDGAR
    tier: tier_0_primary
    source_kind: sec_filings
    base_url: https://www.sec.gov
    license_label: public
    data_class: public_evidence
    trust_weight: 0.98
    refresh_interval_minutes: 360
    fanout: ticker
    url_templates:
      - https://www.sec.gov/edgar/search/#/q={ticker}
  - source_id: source_finnhub_company_news
    source_name: Finnhub Company News
    tier: tier_2_news_api
    source_kind: public_sentiment_news_flow
    base_url: https://finnhub.io/api/v1
    license_label: public_free_tier
    data_class: public_evidence
    trust_weight: 0.82
    refresh_interval_minutes: 120
    requires_secret: true
    secret_env_var: FINNHUB_API_KEY
    fanout: ticker
    url_templates:
      - https://finnhub.io/api/v1/company-news?symbol={ticker}&token={api_token}
  - source_id: source_semianalysis_public
    source_name: SemiAnalysis Public Metadata
    tier: tier_1_specialist
    source_kind: semiconductor_supply_chain_news
    base_url: https://www.semianalysis.com
    license_label: public_metadata_only
    data_class: public_evidence
    trust_weight: 0.90
    refresh_interval_minutes: 720
    metadata_only: true
    fanout: ticker
    url_templates:
      - https://www.semianalysis.com/search?q={ticker}
"""


class RecordingRepository:
    instances: list["RecordingRepository"] = []

    def __init__(self, _connection: object) -> None:
        self.watched: dict[str, object] = {}
        self.sources: dict[str, object] = {}
        self.frontier: dict[str, object] = {}
        self.queue: dict[str, object] = {}
        self.synced_scope: dict[str, object] | None = None
        RecordingRepository.instances.append(self)

    def upsert_watched_equity(self, record: object) -> None:
        self.watched[getattr(record, "ticker")] = record

    def upsert_source(self, record: object) -> None:
        self.sources[getattr(record, "source_id")] = record

    def upsert_frontier_url(self, record: object) -> None:
        self.frontier[getattr(record, "frontier_url_id")] = record

    def upsert_crawl_queue_item(self, record: object) -> None:
        self.queue[getattr(record, "queue_id")] = record

    def sync_source_registry_scope(self, **kwargs: object) -> None:
        self.synced_scope = kwargs


class SeedSourceRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        RecordingRepository.instances.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.watchlist_path = self.root / "watchlist.yaml"
        self.registry_path = self.root / "source_registry.yaml"
        self.watchlist_path.write_text(WATCHLIST_YAML, encoding="utf-8")
        self.registry_path.write_text(SOURCE_REGISTRY_YAML, encoding="utf-8")

    def test_seed_watchlist_uses_source_registry_and_reports_skips(self) -> None:
        import ai_infra_fund_worker.crawl.seed as seed_module

        original = seed_module.EquityIntelligenceRepository
        seed_module.EquityIntelligenceRepository = RecordingRepository
        try:
            with self.assertLogs("ai_infra_fund.worker.crawl.seed", level="INFO") as logs:
                report = seed_module.seed_watchlist(
                    object(),
                    watchlist_path=self.watchlist_path,
                    source_registry_path=self.registry_path,
                    now=NOW,
                    environ={},
                )
        finally:
            seed_module.EquityIntelligenceRepository = original

        self.assertEqual(2, report.watched_equities)
        self.assertGreater(report.sources, 0)
        self.assertGreater(report.frontier_urls, 0)
        self.assertEqual(report.frontier_urls, report.queue_items)
        self.assertEqual(
            (("source_finnhub_company_news", "missing_secret:FINNHUB_API_KEY"),),
            report.skipped_sources,
        )
        self.assertIn("missing_secret:FINNHUB_API_KEY", "\n".join(logs.output))

        repo = RecordingRepository.instances[-1]
        self.assertIn("source_sec_edgar", repo.sources)
        self.assertIn("source_semianalysis_public", repo.sources)
        self.assertNotIn("source_finnhub_company_news", repo.frontier)

    def test_seed_report_is_stable_on_duplicate_run(self) -> None:
        import ai_infra_fund_worker.crawl.seed as seed_module

        original = seed_module.EquityIntelligenceRepository
        seed_module.EquityIntelligenceRepository = RecordingRepository
        try:
            first = seed_module.seed_watchlist(
                object(),
                watchlist_path=self.watchlist_path,
                source_registry_path=self.registry_path,
                now=NOW,
                environ={},
            )
            second = seed_module.seed_watchlist(
                object(),
                watchlist_path=self.watchlist_path,
                source_registry_path=self.registry_path,
                now=NOW,
                environ={},
            )
        finally:
            seed_module.EquityIntelligenceRepository = original

        self.assertEqual(first, second)

    def test_seed_watchlist_syncs_stale_registry_scope_after_upserts(self) -> None:
        import ai_infra_fund_worker.crawl.seed as seed_module

        original = seed_module.EquityIntelligenceRepository
        seed_module.EquityIntelligenceRepository = RecordingRepository
        try:
            seed_module.seed_watchlist(
                object(),
                watchlist_path=self.watchlist_path,
                source_registry_path=self.registry_path,
                now=NOW,
                environ={},
            )
        finally:
            seed_module.EquityIntelligenceRepository = original

        repo = RecordingRepository.instances[-1]
        self.assertIsNotNone(repo.synced_scope)
        synced = repo.synced_scope or {}
        self.assertIn("source_finnhub_company_news", synced["current_source_ids"])
        self.assertNotIn("source_finnhub_company_news", synced["active_source_ids"])
        self.assertIn("source_sec_edgar", synced["active_source_ids"])
        self.assertTrue(synced["current_frontier_keys"])
        self.assertTrue(all(len(key) == 2 for key in synced["current_frontier_keys"]))
        self.assertNotIn(
            "source_finnhub_company_news",
            {key[0] for key in synced["current_frontier_keys"]},
        )


if __name__ == "__main__":
    unittest.main()
