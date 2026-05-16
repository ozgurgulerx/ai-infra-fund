from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))


NOW = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)


def _watchlist():
    from ai_infra_fund_core.local_inputs.watchlist import (
        AIEquityWatchlist,
        AIEquityWatchlistEntry,
    )

    return AIEquityWatchlist(
        version=1,
        entries=(
            AIEquityWatchlistEntry(
                ticker="NVDA",
                company_name="NVIDIA",
                themes=("ai_accelerators", "hbm_memory"),
                sector_tags=("semiconductors",),
                source_urls=("https://investor.nvidia.com/",),
                priority="critical",
            ),
            AIEquityWatchlistEntry(
                ticker="MSFT",
                company_name="Microsoft",
                themes=("ai_cloud", "hyperscaler_capex"),
                sector_tags=("cloud_platforms",),
                source_urls=("https://www.microsoft.com/en-us/investor",),
                priority="high",
            ),
        ),
    )


def _registry_yaml() -> str:
    return """
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
  - source_id: source_fred_macro
    source_name: FRED Macro Series
    tier: tier_0_primary
    source_kind: macro_rates_liquidity_commentary
    base_url: https://api.stlouisfed.org/fred
    license_label: public
    data_class: public_market_data
    trust_weight: 0.99
    refresh_interval_minutes: 1440
    requires_secret: true
    secret_env_var: FRED_API_KEY
    fanout: series
    series_ids: [DFF, DGS10]
    url_templates:
      - https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}
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
  - source_id: source_stooq_market_data
    source_name: Stooq Market Data
    tier: tier_2_news_api
    source_kind: market_price_snapshot
    base_url: https://stooq.com
    license_label: public
    data_class: public_market_data
    trust_weight: 0.80
    refresh_interval_minutes: 1440
    fanout: ticker
    url_templates:
      - https://stooq.com/q/d/l/?s={ticker}.us&i=d&utm_source=ignored
"""


class SourceRegistryValidationTests(unittest.TestCase):
    def test_project_registry_declares_required_source_tiers(self) -> None:
        from ai_infra_fund_core.equity_intelligence.source_registry import (
            load_source_registry,
        )

        registry = load_source_registry(ROOT / "config" / "source_registry.yaml")
        tiers = {source.tier for source in registry.sources}

        self.assertEqual(
            {
                "tier_0_primary",
                "tier_1_specialist",
                "tier_2_news_api",
                "tier_3_social_attention",
            },
            tiers,
        )

    def test_project_registry_contains_required_public_sources(self) -> None:
        from ai_infra_fund_core.equity_intelligence.source_registry import (
            load_source_registry,
        )

        registry = load_source_registry(ROOT / "config" / "source_registry.yaml")
        names = {source.source_name for source in registry.sources}

        for expected in (
            "SEC EDGAR",
            "NVIDIA Official Feeds",
            "TSMC IR Monthly Revenue",
            "SemiAnalysis Public Metadata",
            "Semiconductor Engineering",
            "SemiWiki",
            "Data Center Dynamics",
            "Data Center Knowledge",
            "IEEE Spectrum AI/Energy/Computing",
            "DeepLearning.AI The Batch",
            "Epoch AI",
            "METR",
            "EIA Electricity Data",
            "FRED Macro Series",
            "GDELT DOC 2.0",
            "Finnhub Company News",
            "Stooq Market Data",
        ):
            self.assertIn(expected, names)

    def test_rejects_invalid_tier_and_private_source(self) -> None:
        from ai_infra_fund_core.equity_intelligence.source_registry import (
            validate_source_registry,
        )

        invalid_tier = yaml.safe_load(_registry_yaml())
        invalid_tier["sources"][0]["tier"] = "tier_9_random"
        with self.assertRaisesRegex(ValueError, "tier"):
            validate_source_registry(invalid_tier)

        private_source = yaml.safe_load(_registry_yaml())
        private_source["sources"][0]["data_class"] = "private_research"
        with self.assertRaisesRegex(ValueError, "private"):
            validate_source_registry(private_source)


class SourceRegistrySeedPlanTests(unittest.TestCase):
    def test_builds_public_frontier_urls_and_skips_missing_optional_secrets(self) -> None:
        from ai_infra_fund_core.equity_intelligence.seeder import (
            build_source_registry_seed_plan,
        )
        from ai_infra_fund_core.equity_intelligence.source_registry import (
            validate_source_registry,
        )

        registry = validate_source_registry(yaml.safe_load(_registry_yaml()))
        plan = build_source_registry_seed_plan(
            _watchlist(),
            registry,
            now=NOW,
            environ={},
        )

        self.assertGreater(len(plan.source_records), 0)
        self.assertGreater(len(plan.frontier_url_records), 0)
        self.assertEqual(plan.skipped_sources_by_id["source_fred_macro"], "missing_secret:FRED_API_KEY")
        self.assertEqual(
            plan.skipped_sources_by_id["source_finnhub_company_news"],
            "missing_secret:FINNHUB_API_KEY",
        )
        urls = "\n".join(record.url for record in plan.frontier_url_records)
        self.assertIn("sec.gov", urls)
        self.assertIn("stooq.com", urls)
        self.assertIn("semianalysis.com", urls)
        self.assertNotIn("api_key", urls)
        self.assertNotIn("token=", urls)

    def test_preserves_source_quality_metadata_on_sources_and_frontier_urls(self) -> None:
        from ai_infra_fund_core.equity_intelligence.seeder import (
            build_source_registry_seed_plan,
        )
        from ai_infra_fund_core.equity_intelligence.source_registry import (
            validate_source_registry,
        )

        registry = validate_source_registry(yaml.safe_load(_registry_yaml()))
        plan = build_source_registry_seed_plan(
            _watchlist(),
            registry,
            now=NOW,
            environ={},
        )
        semianalysis_source = {
            record.source_id: record for record in plan.source_records
        }["source_semianalysis_public"]
        self.assertEqual("semiconductor_supply_chain_news", semianalysis_source.source_type)
        self.assertEqual("public_metadata_only", semianalysis_source.license_label)
        self.assertEqual(0.90, semianalysis_source.reliability_score)
        self.assertEqual("tier_1_specialist", semianalysis_source.metadata["tier"])
        self.assertEqual(720, semianalysis_source.metadata["refresh_interval_minutes"])
        self.assertTrue(semianalysis_source.metadata["metadata_only"])

        frontier = next(
            record
            for record in plan.frontier_url_records
            if record.source_id == "source_semianalysis_public"
        )
        self.assertEqual("metadata_excerpt_only", frontier.metadata["access_mode"])
        self.assertEqual("tier_1_specialist", frontier.metadata["tier"])
        self.assertEqual(720, frontier.metadata["refresh_interval_minutes"])

    def test_registry_seed_plan_is_idempotent_and_canonicalizes_urls(self) -> None:
        from ai_infra_fund_core.equity_intelligence.seeder import (
            build_source_registry_seed_plan,
        )
        from ai_infra_fund_core.equity_intelligence.source_registry import (
            validate_source_registry,
        )

        registry = validate_source_registry(yaml.safe_load(_registry_yaml()))
        first = build_source_registry_seed_plan(_watchlist(), registry, now=NOW, environ={})
        second = build_source_registry_seed_plan(_watchlist(), registry, now=NOW, environ={})

        self.assertEqual(
            [record.frontier_url_id for record in first.frontier_url_records],
            [record.frontier_url_id for record in second.frontier_url_records],
        )
        stooq_urls = [
            record.url
            for record in first.frontier_url_records
            if record.source_id == "source_stooq_market_data"
        ]
        self.assertTrue(stooq_urls)
        self.assertNotIn("utm_source", "\n".join(stooq_urls))
        unique_keys = {
            (record.source_id, record.url_hash) for record in first.frontier_url_records
        }
        self.assertEqual(len(first.frontier_url_records), len(unique_keys))


if __name__ == "__main__":
    unittest.main()
