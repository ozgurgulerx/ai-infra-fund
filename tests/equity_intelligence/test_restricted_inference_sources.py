from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

NOW = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)


class RestrictedInferenceSourceTests(unittest.TestCase):
    def test_project_restricted_sources_are_saved_but_not_crawl_enabled(self) -> None:
        from ai_infra_fund_core.equity_intelligence.restricted_sources import (
            load_restricted_inference_sources,
        )

        registry = load_restricted_inference_sources(
            ROOT / "config" / "restricted_inference_sources.yaml"
        )

        self.assertGreaterEqual(len(registry.sources), 35)
        by_id = {source.source_id: source for source in registry.sources}
        for expected in (
            "restricted_pitchbook",
            "restricted_sp_capital_iq_pro",
            "restricted_planet_apis",
            "restricted_linkedin_talent_insights",
            "restricted_sam_gov_opportunities_api",
        ):
            self.assertIn(expected, by_id)

        for source in registry.sources:
            self.assertFalse(source.crawl_enabled)
            self.assertEqual("do_not_crawl", source.default_action)
            self.assertIn(
                source.restriction_type,
                {
                    "api_key_required",
                    "account_required",
                    "paid_subscription",
                    "licensed_data",
                    "login_gated",
                    "terms_review_required",
                    "uncertain_verify_first",
                },
            )

    def test_restricted_sources_are_not_in_active_source_registry(self) -> None:
        from ai_infra_fund_core.equity_intelligence.restricted_sources import (
            load_restricted_inference_sources,
        )
        from ai_infra_fund_core.equity_intelligence.source_registry import (
            load_source_registry,
        )

        restricted = load_restricted_inference_sources(
            ROOT / "config" / "restricted_inference_sources.yaml"
        )
        active = load_source_registry(ROOT / "config" / "source_registry.yaml")
        active_text = "\n".join(
            [source.source_id for source in active.sources]
            + [source.source_name for source in active.sources]
            + [source.base_url for source in active.sources]
            + [template for source in active.sources for template in source.url_templates]
        )

        for source in restricted.sources:
            self.assertNotIn(source.source_id, active_text)
            self.assertNotIn(source.url, active_text)

    def test_restricted_sources_do_not_seed_frontier_urls(self) -> None:
        from ai_infra_fund_core.equity_intelligence.restricted_sources import (
            load_restricted_inference_sources,
        )
        from ai_infra_fund_core.equity_intelligence.seeder import (
            build_source_registry_seed_plan,
        )
        from ai_infra_fund_core.equity_intelligence.source_registry import (
            load_source_registry,
        )
        from ai_infra_fund_core.local_inputs.watchlist import load_ai_equity_watchlist

        restricted = load_restricted_inference_sources(
            ROOT / "config" / "restricted_inference_sources.yaml"
        )
        watchlist = load_ai_equity_watchlist(ROOT / "config" / "ai_equity_watchlist.yaml")
        active = load_source_registry(ROOT / "config" / "source_registry.yaml")
        plan = build_source_registry_seed_plan(watchlist, active, now=NOW, environ={})

        frontier_urls = "\n".join(record.url for record in plan.frontier_url_records)
        source_ids = {record.source_id for record in plan.source_records}

        for source in restricted.sources:
            self.assertNotIn(source.source_id, source_ids)
            self.assertNotIn(source.url, frontier_urls)

    def test_validator_rejects_enabled_or_secret_bearing_sources(self) -> None:
        from ai_infra_fund_core.equity_intelligence.restricted_sources import (
            validate_restricted_inference_sources,
        )

        valid = {
            "version": 1,
            "sources": [
                {
                    "source_id": "restricted_example",
                    "source_name": "Example",
                    "url": "https://example.com/api",
                    "source_family": "example",
                    "restriction_type": "api_key_required",
                    "default_action": "do_not_crawl",
                    "crawl_enabled": False,
                    "notes": "Requires future approval.",
                    "secret_env_var": "EXAMPLE_API_KEY",
                }
            ],
        }

        enabled = {**valid, "sources": [{**valid["sources"][0], "crawl_enabled": True}]}
        with self.assertRaisesRegex(ValueError, "crawl_enabled"):
            validate_restricted_inference_sources(enabled)

        bad_action = {
            **valid,
            "sources": [{**valid["sources"][0], "default_action": "crawl"}],
        }
        with self.assertRaisesRegex(ValueError, "default_action"):
            validate_restricted_inference_sources(bad_action)

        secret_field = {
            **valid,
            "sources": [{**valid["sources"][0], "api_key": "sk-secret"}],
        }
        with self.assertRaisesRegex(ValueError, "secret"):
            validate_restricted_inference_sources(secret_field)


if __name__ == "__main__":
    unittest.main()
