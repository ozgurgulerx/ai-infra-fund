from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))


class SourceAccessDecisionTests(unittest.TestCase):
    def test_project_access_decisions_track_optional_public_api_keys(self) -> None:
        from ai_infra_fund_core.equity_intelligence.source_access_decisions import (
            load_source_access_decisions,
        )
        from ai_infra_fund_core.equity_intelligence.source_registry import (
            load_source_registry,
        )

        registry = load_source_access_decisions(
            ROOT / "config" / "source_access_decisions.yaml"
        )
        source_registry = load_source_registry(ROOT / "config" / "source_registry.yaml")
        active_sources = {source.source_id: source for source in source_registry.sources}

        by_env = {decision.env_var: decision for decision in registry.optional_public_api_keys}
        self.assertEqual(
            {"EIA_API_KEY", "FRED_API_KEY", "FINNHUB_API_KEY"},
            set(by_env),
        )
        for decision in by_env.values():
            self.assertEqual(
                "approve_to_activate_when_secret_configured",
                decision.decision,
            )
            self.assertTrue(decision.source_ids)
            for source_id in decision.source_ids:
                self.assertIn(source_id, active_sources)
                self.assertTrue(active_sources[source_id].requires_secret)
                self.assertEqual(decision.env_var, active_sources[source_id].secret_env_var)

    def test_project_access_decisions_are_saved_but_not_crawl_enabled(self) -> None:
        from ai_infra_fund_core.equity_intelligence.source_access_decisions import (
            DECISION_STATUSES,
            load_source_access_decisions,
        )

        registry = load_source_access_decisions(
            ROOT / "config" / "source_access_decisions.yaml"
        )

        self.assertGreaterEqual(len(registry.source_decisions), 60)
        by_id = {decision.source_id: decision for decision in registry.source_decisions}
        for expected in (
            "access_micron_investor_relations",
            "access_lbnl_interconnection_queues",
            "access_openai_stargate_uae",
            "access_eia_open_data_api",
            "access_finnhub_company_news",
            "access_intel_ai_newsroom",
            "access_eetimes_ai_accelerator",
            "access_eaton_news",
            "access_vertiv_news",
            "access_semi_press",
            "access_the_register_ai_ml",
        ):
            self.assertIn(expected, by_id)

        for decision in registry.source_decisions:
            self.assertFalse(decision.crawl_enabled)
            self.assertIn(decision.decision, DECISION_STATUSES)
            self.assertTrue(decision.required_action)

    def test_deferred_access_decisions_are_not_active_source_registry_urls(self) -> None:
        from ai_infra_fund_core.equity_intelligence.source_access_decisions import (
            load_source_access_decisions,
        )
        from ai_infra_fund_core.equity_intelligence.source_registry import (
            load_source_registry,
        )

        decisions = load_source_access_decisions(
            ROOT / "config" / "source_access_decisions.yaml"
        )
        active = load_source_registry(ROOT / "config" / "source_registry.yaml")
        active_crawl_sources = [source for source in active.sources if source.crawl_enabled]
        active_identity_text = "\n".join(
            [source.source_id for source in active_crawl_sources]
            + [source.source_name for source in active_crawl_sources]
        )
        active_url_templates = {
            template for source in active_crawl_sources for template in source.url_templates
        }

        for decision in decisions.source_decisions:
            if decision.decision == "needs_optional_api_key":
                continue
            self.assertNotIn(decision.source_id, active_identity_text)
            self.assertNotIn(decision.url, active_url_templates)

    def test_resolved_deferred_sources_are_removed_from_access_decisions(self) -> None:
        from ai_infra_fund_core.equity_intelligence.source_access_decisions import (
            load_source_access_decisions,
        )

        decisions = load_source_access_decisions(
            ROOT / "config" / "source_access_decisions.yaml"
        )
        decision_ids = {decision.source_id for decision in decisions.source_decisions}

        self.assertNotIn("access_bis_press_releases", decision_ids)
        self.assertNotIn("access_micron_quarterly_results", decision_ids)

    def test_validator_rejects_enabled_decisions_and_bad_env_names(self) -> None:
        from ai_infra_fund_core.equity_intelligence.source_access_decisions import (
            validate_source_access_decisions,
        )

        valid = {
            "version": 1,
            "optional_public_api_keys": [
                {
                    "env_var": "EXAMPLE_API_KEY",
                    "provider": "Example",
                    "source_ids": ["source_example"],
                    "decision": "approve_to_activate_when_secret_configured",
                    "notes": "Example optional key.",
                }
            ],
            "source_decisions": [
                {
                    "source_id": "access_example",
                    "source_name": "Example",
                    "url": "https://example.com/",
                    "source_family": "example",
                    "decision": "deferred_provider_design",
                    "crawl_enabled": False,
                    "required_action": "Build a provider.",
                    "notes": "Not active.",
                }
            ],
        }

        validate_source_access_decisions(valid)

        enabled = {
            **valid,
            "source_decisions": [{**valid["source_decisions"][0], "crawl_enabled": True}],
        }
        with self.assertRaisesRegex(ValueError, "crawl_enabled"):
            validate_source_access_decisions(enabled)

        bad_key = {
            **valid,
            "optional_public_api_keys": [
                {**valid["optional_public_api_keys"][0], "env_var": "not-valid"}
            ],
        }
        with self.assertRaisesRegex(ValueError, "environment variable"):
            validate_source_access_decisions(bad_key)

    def test_validator_rejects_key_required_decision_without_secret_env_var(self) -> None:
        from ai_infra_fund_core.equity_intelligence.source_access_decisions import (
            validate_source_access_decisions,
        )

        raw = {
            "version": 1,
            "optional_public_api_keys": [
                {
                    "env_var": "EXAMPLE_API_KEY",
                    "provider": "Example",
                    "source_ids": ["source_example"],
                    "decision": "approve_to_activate_when_secret_configured",
                    "notes": "Example optional key.",
                }
            ],
            "source_decisions": [
                {
                    "source_id": "access_example_api",
                    "source_name": "Example API",
                    "url": "https://example.com/api",
                    "source_family": "example",
                    "decision": "needs_optional_api_key",
                    "crawl_enabled": False,
                    "required_action": "Configure EXAMPLE_API_KEY before activation.",
                    "notes": "Key-gated public API.",
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "secret_env_var"):
            validate_source_access_decisions(raw)


if __name__ == "__main__":
    unittest.main()
