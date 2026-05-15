from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


def _watchlist_yaml(extra: str = "") -> str:
    return (
        "version: 1\n"
        "entries:\n"
        "  - ticker: NVDA\n"
        "    company_name: NVIDIA\n"
        "    themes: [ai_accelerators]\n"
        "    sector_tags: [semiconductors]\n"
        "    source_urls: [https://www.nvidia.com/]\n"
        "    priority: critical\n"
        "  - ticker: MSFT\n"
        "    company_name: Microsoft\n"
        "    themes: [ai_cloud]\n"
        "    sector_tags: [cloud_platforms]\n"
        "    source_urls: [https://www.microsoft.com/]\n"
        "    priority: high\n"
        f"{extra}"
    )


class ProvidersYamlParseTests(unittest.TestCase):
    def test_providers_is_optional_and_defaults_to_empty(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import (
            validate_ai_equity_watchlist,
        )
        import yaml

        watchlist = validate_ai_equity_watchlist(yaml.safe_load(_watchlist_yaml()))
        self.assertEqual((), watchlist.providers)

    def test_parses_ticker_fanout_provider(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import (
            validate_ai_equity_watchlist,
        )
        import yaml

        providers_yaml = (
            "providers:\n"
            "  - source_id: source-api-sec-edgar\n"
            "    source_name: SEC EDGAR\n"
            "    source_type: filings_api\n"
            "    base_url: https://data.sec.gov\n"
            "    license_label: public\n"
            "    data_class: public_evidence\n"
            "    reliability_score: 0.98\n"
            "    requires_secret: false\n"
            "    ticker_fanout: true\n"
            "    url_templates:\n"
            "      - https://data.sec.gov/submissions/?frontier_ticker={ticker}\n"
        )
        watchlist = validate_ai_equity_watchlist(
            yaml.safe_load(_watchlist_yaml(providers_yaml))
        )
        self.assertEqual(1, len(watchlist.providers))
        provider = watchlist.providers[0]
        self.assertEqual("source-api-sec-edgar", provider.source_id)
        self.assertEqual("filings_api", provider.source_type)
        self.assertEqual("public_evidence", provider.data_class)
        self.assertTrue(provider.ticker_fanout)
        self.assertEqual((), provider.series_fanout)
        self.assertFalse(provider.theme_fanout)
        self.assertEqual(
            ("https://data.sec.gov/submissions/?frontier_ticker={ticker}",),
            provider.url_templates,
        )

    def test_parses_series_fanout_provider(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import (
            validate_ai_equity_watchlist,
        )
        import yaml

        providers_yaml = (
            "providers:\n"
            "  - source_id: source-api-fred\n"
            "    source_name: FRED\n"
            "    source_type: macro_api\n"
            "    base_url: https://api.stlouisfed.org/fred\n"
            "    license_label: public\n"
            "    data_class: public_market_data\n"
            "    reliability_score: 0.99\n"
            "    requires_secret: true\n"
            "    secret_env_var: FRED_API_KEY\n"
            "    series_fanout: [DFF, DGS10]\n"
            "    url_templates:\n"
            "      - https://api.stlouisfed.org/fred/series/observations?series_id={series_id}\n"
        )
        watchlist = validate_ai_equity_watchlist(
            yaml.safe_load(_watchlist_yaml(providers_yaml))
        )
        provider = watchlist.providers[0]
        self.assertFalse(provider.ticker_fanout)
        self.assertEqual(("DFF", "DGS10"), provider.series_fanout)
        self.assertTrue(provider.requires_secret)

    def test_rejects_invalid_data_class(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import (
            validate_ai_equity_watchlist,
        )
        import yaml

        providers_yaml = (
            "providers:\n"
            "  - source_id: source-api-bad\n"
            "    source_name: Bad\n"
            "    source_type: bad\n"
            "    base_url: https://bad.example\n"
            "    license_label: public\n"
            "    data_class: rocket_telemetry\n"
            "    reliability_score: 0.5\n"
            "    requires_secret: false\n"
            "    ticker_fanout: true\n"
            "    url_templates:\n"
            "      - https://bad.example/?t={ticker}\n"
        )
        with self.assertRaisesRegex(ValueError, "data_class"):
            validate_ai_equity_watchlist(
                yaml.safe_load(_watchlist_yaml(providers_yaml))
            )

    def test_rejects_no_fanout_dimension(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import (
            validate_ai_equity_watchlist,
        )
        import yaml

        providers_yaml = (
            "providers:\n"
            "  - source_id: source-api-nofan\n"
            "    source_name: NoFan\n"
            "    source_type: api\n"
            "    base_url: https://nofan.example\n"
            "    license_label: public\n"
            "    data_class: public_evidence\n"
            "    reliability_score: 0.5\n"
            "    requires_secret: false\n"
            "    url_templates:\n"
            "      - https://nofan.example/static\n"
        )
        with self.assertRaisesRegex(ValueError, "fanout"):
            validate_ai_equity_watchlist(
                yaml.safe_load(_watchlist_yaml(providers_yaml))
            )

    def test_rejects_two_fanout_dimensions(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import (
            validate_ai_equity_watchlist,
        )
        import yaml

        providers_yaml = (
            "providers:\n"
            "  - source_id: source-api-multi\n"
            "    source_name: Multi\n"
            "    source_type: api\n"
            "    base_url: https://multi.example\n"
            "    license_label: public\n"
            "    data_class: public_evidence\n"
            "    reliability_score: 0.5\n"
            "    requires_secret: false\n"
            "    ticker_fanout: true\n"
            "    series_fanout: [X]\n"
            "    url_templates:\n"
            "      - https://multi.example/?t={ticker}\n"
        )
        with self.assertRaisesRegex(ValueError, "exactly one"):
            validate_ai_equity_watchlist(
                yaml.safe_load(_watchlist_yaml(providers_yaml))
            )

    def test_rejects_ticker_fanout_without_ticker_placeholder(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import (
            validate_ai_equity_watchlist,
        )
        import yaml

        providers_yaml = (
            "providers:\n"
            "  - source_id: source-api-mismatch\n"
            "    source_name: M\n"
            "    source_type: api\n"
            "    base_url: https://m.example\n"
            "    license_label: public\n"
            "    data_class: public_evidence\n"
            "    reliability_score: 0.5\n"
            "    requires_secret: false\n"
            "    ticker_fanout: true\n"
            "    url_templates:\n"
            "      - https://m.example/static\n"
        )
        with self.assertRaisesRegex(ValueError, "ticker"):
            validate_ai_equity_watchlist(
                yaml.safe_load(_watchlist_yaml(providers_yaml))
            )


class BuildProviderSourceRecordsTests(unittest.TestCase):
    def _watchlist_with_two_providers(self):
        from ai_infra_fund_core.local_inputs.watchlist import (
            validate_ai_equity_watchlist,
        )
        import yaml

        providers_yaml = (
            "providers:\n"
            "  - source_id: source-api-sec-edgar\n"
            "    source_name: SEC EDGAR\n"
            "    source_type: filings_api\n"
            "    base_url: https://data.sec.gov\n"
            "    license_label: public\n"
            "    data_class: public_evidence\n"
            "    reliability_score: 0.98\n"
            "    requires_secret: false\n"
            "    ticker_fanout: true\n"
            "    url_templates:\n"
            "      - https://data.sec.gov/submissions/?frontier_ticker={ticker}\n"
            "  - source_id: source-api-fred\n"
            "    source_name: FRED\n"
            "    source_type: macro_api\n"
            "    base_url: https://api.stlouisfed.org/fred\n"
            "    license_label: public\n"
            "    data_class: public_market_data\n"
            "    reliability_score: 0.99\n"
            "    requires_secret: true\n"
            "    secret_env_var: FRED_API_KEY\n"
            "    series_fanout: [DFF, DGS10]\n"
            "    url_templates:\n"
            "      - https://api.stlouisfed.org/fred/series/observations?series_id={series_id}\n"
        )
        return validate_ai_equity_watchlist(
            yaml.safe_load(_watchlist_yaml(providers_yaml))
        )

    def test_one_source_record_per_provider(self) -> None:
        from ai_infra_fund_core.equity_intelligence.seeder import (
            build_provider_source_records,
        )

        records = build_provider_source_records(
            self._watchlist_with_two_providers(), now=NOW
        )
        ids = {r.source_id for r in records}
        self.assertEqual({"source-api-sec-edgar", "source-api-fred"}, ids)

    def test_provider_metadata_carries_fanout_config(self) -> None:
        from ai_infra_fund_core.equity_intelligence.seeder import (
            build_provider_source_records,
        )

        records = {
            r.source_id: r
            for r in build_provider_source_records(
                self._watchlist_with_two_providers(), now=NOW
            )
        }
        fred = records["source-api-fred"]
        self.assertEqual("macro_api", fred.source_type)
        self.assertEqual("public_market_data", fred.data_class)
        self.assertIn("series_fanout", fred.metadata)
        self.assertEqual(["DFF", "DGS10"], list(fred.metadata["series_fanout"]))
        self.assertEqual("api_provider", fred.metadata["origin"])
        self.assertTrue(fred.metadata["requires_secret"])

        sec = records["source-api-sec-edgar"]
        self.assertTrue(sec.metadata["ticker_fanout"])
        self.assertEqual(
            ["https://data.sec.gov/submissions/?frontier_ticker={ticker}"],
            list(sec.metadata["url_templates"]),
        )

    def test_provider_records_use_now_for_timestamps(self) -> None:
        from ai_infra_fund_core.equity_intelligence.seeder import (
            build_provider_source_records,
        )

        for record in build_provider_source_records(
            self._watchlist_with_two_providers(), now=NOW
        ):
            self.assertEqual(NOW, record.created_at)
            self.assertEqual(NOW, record.updated_at)


class BuildProviderFrontierUrlsTests(unittest.TestCase):
    def _watchlist_with_providers(self):
        from ai_infra_fund_core.local_inputs.watchlist import (
            validate_ai_equity_watchlist,
        )
        import yaml

        providers_yaml = (
            "providers:\n"
            "  - source_id: source-api-sec-edgar\n"
            "    source_name: SEC EDGAR\n"
            "    source_type: filings_api\n"
            "    base_url: https://data.sec.gov\n"
            "    license_label: public\n"
            "    data_class: public_evidence\n"
            "    reliability_score: 0.98\n"
            "    requires_secret: false\n"
            "    ticker_fanout: true\n"
            "    url_templates:\n"
            "      - https://data.sec.gov/submissions/?frontier_ticker={ticker}\n"
            "      - https://data.sec.gov/api/xbrl/companyfacts/?frontier_ticker={ticker}\n"
            "  - source_id: source-api-fred\n"
            "    source_name: FRED\n"
            "    source_type: macro_api\n"
            "    base_url: https://api.stlouisfed.org/fred\n"
            "    license_label: public\n"
            "    data_class: public_market_data\n"
            "    reliability_score: 0.99\n"
            "    requires_secret: true\n"
            "    secret_env_var: FRED_API_KEY\n"
            "    series_fanout: [DFF, DGS10]\n"
            "    url_templates:\n"
            "      - https://api.stlouisfed.org/fred/series/observations?series_id={series_id}\n"
            "  - source_id: source-api-finnhub\n"
            "    source_name: Finnhub\n"
            "    source_type: news_event_api\n"
            "    base_url: https://finnhub.io/api/v1\n"
            "    license_label: public_free_tier\n"
            "    data_class: public_evidence\n"
            "    reliability_score: 0.85\n"
            "    requires_secret: true\n"
            "    secret_env_var: FINNHUB_API_KEY\n"
            "    ticker_fanout: true\n"
            "    url_templates:\n"
            "      - https://finnhub.io/api/v1/company-news?symbol={ticker}&token={api_token}\n"
        )
        return validate_ai_equity_watchlist(
            yaml.safe_load(_watchlist_yaml(providers_yaml))
        )

    def test_ticker_fanout_creates_one_url_per_ticker_template(self) -> None:
        from ai_infra_fund_core.equity_intelligence.seeder import (
            build_provider_frontier_urls,
        )

        records = build_provider_frontier_urls(
            self._watchlist_with_providers(), now=NOW
        )
        sec_records = [r for r in records if r.source_id == "source-api-sec-edgar"]
        self.assertEqual(4, len(sec_records))
        urls = sorted(r.url for r in sec_records)
        self.assertEqual(
            [
                "https://data.sec.gov/api/xbrl/companyfacts/?frontier_ticker=MSFT",
                "https://data.sec.gov/api/xbrl/companyfacts/?frontier_ticker=NVDA",
                "https://data.sec.gov/submissions/?frontier_ticker=MSFT",
                "https://data.sec.gov/submissions/?frontier_ticker=NVDA",
            ],
            urls,
        )

    def test_series_fanout_does_not_create_frontier_rows(self) -> None:
        from ai_infra_fund_core.equity_intelligence.seeder import (
            build_provider_frontier_urls,
        )

        records = build_provider_frontier_urls(
            self._watchlist_with_providers(), now=NOW
        )
        fred_records = [r for r in records if r.source_id == "source-api-fred"]
        self.assertEqual([], fred_records)

    def test_ticker_fanout_strips_secret_placeholders_from_frontier_urls(self) -> None:
        from ai_infra_fund_core.equity_intelligence.seeder import (
            build_provider_frontier_urls,
        )

        records = build_provider_frontier_urls(
            self._watchlist_with_providers(), now=NOW
        )
        finnhub_urls = sorted(
            r.url for r in records if r.source_id == "source-api-finnhub"
        )
        self.assertEqual(
            [
                "https://finnhub.io/api/v1/company-news?symbol=MSFT",
                "https://finnhub.io/api/v1/company-news?symbol=NVDA",
            ],
            finnhub_urls,
        )
        self.assertNotIn("api_token", "\n".join(finnhub_urls))
        self.assertNotIn("token=", "\n".join(finnhub_urls))

    def test_frontier_url_id_is_unique_and_deterministic(self) -> None:
        from ai_infra_fund_core.equity_intelligence.seeder import (
            build_provider_frontier_urls,
        )

        first = build_provider_frontier_urls(self._watchlist_with_providers(), now=NOW)
        second = build_provider_frontier_urls(self._watchlist_with_providers(), now=NOW)
        ids = [r.frontier_url_id for r in first]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            [r.frontier_url_id for r in first],
            [r.frontier_url_id for r in second],
        )

    def test_frontier_inherits_ticker_priority(self) -> None:
        from ai_infra_fund_core.equity_intelligence.seeder import (
            build_provider_frontier_urls,
        )

        records = build_provider_frontier_urls(
            self._watchlist_with_providers(), now=NOW
        )
        by_ticker_url = {(r.ticker, r.url): r.priority for r in records}
        nvda_priority = by_ticker_url[
            ("NVDA", "https://data.sec.gov/submissions/?frontier_ticker=NVDA")
        ]
        msft_priority = by_ticker_url[
            ("MSFT", "https://data.sec.gov/submissions/?frontier_ticker=MSFT")
        ]
        self.assertEqual(100, nvda_priority)
        self.assertEqual(75, msft_priority)


if __name__ == "__main__":
    unittest.main()
