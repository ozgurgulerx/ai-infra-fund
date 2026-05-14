from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.common import DataClass  # noqa: E402
from ai_infra_fund_core.equity_intelligence import (  # noqa: E402
    ConnectorFetchResult,
    CrawlQueueItem,
    EquityEvent,
    EquityEventType,
    FreshnessPolicy,
    FreshnessStatus,
    FrontierPolicy,
    PriorityBoost,
    SourcePolicy,
    StubSourceConnector,
    apply_priority_boosts,
    assess_freshness,
    canonicalize_url,
    claim_due_targets,
    record_crawl_failure,
    record_crawl_success,
    seed_crawl_target,
)


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class EquityIntelligenceFrontierTests(unittest.TestCase):
    def test_canonicalize_url_is_deterministic_and_rejects_non_public_schemes(self) -> None:
        canonical = canonicalize_url(
            "HTTPS://Example.com:443/docs/?utm_source=newsletter&b=2&a=1#section"
        )

        self.assertEqual("https://example.com/docs?a=1&b=2", canonical.canonical_url)
        self.assertEqual("example.com", canonical.domain)
        self.assertEqual("/docs", canonical.path)

        with self.assertRaisesRegex(ValueError, "http or https"):
            canonicalize_url("file:///tmp/report.html")

    def test_source_policy_carries_license_metadata_without_trade_surface(self) -> None:
        policy = SourcePolicy(
            source_id="company-ir",
            publisher="Company investor relations",
            license_label="public-web-research-use",
            data_class=DataClass.PUBLIC_EVIDENCE,
            allowed_uses=("crawl", "quote", "feature_extraction"),
            requires_attribution=True,
            local_only=False,
        )

        self.assertEqual("public-web-research-use", policy.license_label)
        self.assertEqual(("crawl", "quote", "feature_extraction"), policy.allowed_uses)
        self.assertEqual(DataClass.PUBLIC_EVIDENCE, policy.data_class)

        source_text = (
            CORE_SRC / "ai_infra_fund_core" / "equity_intelligence" / "frontier.py"
        ).read_text(encoding="utf-8")
        forbidden = [
            "from openai",
            "import openai",
            "from anthropic",
            "import anthropic",
            "broker",
            "submit_order",
            "place_order",
            "execute_trade",
        ]
        self.assertEqual([], [pattern for pattern in forbidden if pattern in source_text])

    def test_freshness_status_uses_available_at_and_last_crawl_age(self) -> None:
        policy = FreshnessPolicy(max_age=timedelta(hours=24), stale_after=timedelta(hours=72))

        self.assertEqual(
            FreshnessStatus.NEW,
            assess_freshness(last_crawled_at=None, next_crawl_at=None, as_of=NOW, policy=policy).status,
        )
        self.assertEqual(
            FreshnessStatus.FRESH,
            assess_freshness(
                last_crawled_at=NOW - timedelta(hours=2),
                next_crawl_at=NOW + timedelta(hours=22),
                as_of=NOW,
                policy=policy,
            ).status,
        )
        self.assertEqual(
            FreshnessStatus.DUE,
            assess_freshness(
                last_crawled_at=NOW - timedelta(hours=25),
                next_crawl_at=NOW - timedelta(minutes=1),
                as_of=NOW,
                policy=policy,
            ).status,
        )
        self.assertEqual(
            FreshnessStatus.STALE,
            assess_freshness(
                last_crawled_at=NOW - timedelta(days=7),
                next_crawl_at=NOW - timedelta(days=1),
                as_of=NOW,
                policy=policy,
            ).status,
        )

    def test_seed_boost_claim_and_success_cycle_are_immutable_and_domain_capped(self) -> None:
        source_policy = SourcePolicy(
            source_id="sec",
            publisher="SEC",
            license_label="public",
            data_class="public_evidence",
            allowed_uses=("crawl",),
        )
        target = seed_crawl_target(
            "https://nvidia.com/?utm_campaign=x",
            source_policy=source_policy,
            page_type="investor_relations",
            base_priority=30,
            discovered_at=NOW,
        )
        other = seed_crawl_target(
            "https://nvidia.com/docs",
            source_policy=source_policy,
            page_type="docs",
            base_priority=20,
            discovered_at=NOW,
        )
        amd = seed_crawl_target(
            "https://amd.com/security",
            source_policy=source_policy,
            page_type="security",
            base_priority=10,
            discovered_at=NOW,
        )

        boosted = apply_priority_boosts(
            (target, other, amd),
            (
                PriorityBoost(
                    reason="earnings-event",
                    ticker="NVDA",
                    url_prefix="https://nvidia.com/",
                    priority_delta=25,
                    available_at=NOW,
                ),
            ),
        )

        self.assertEqual(30, target.priority_score)
        self.assertEqual(55, boosted[0].priority_score)
        self.assertEqual(45, boosted[1].priority_score)
        self.assertEqual(10, boosted[2].priority_score)

        queue = tuple(CrawlQueueItem.from_target(item, available_at=NOW) for item in boosted)
        claimed = claim_due_targets(
            queue,
            as_of=NOW,
            lease_owner="worker-c",
            policy=FrontierPolicy(batch_size=3, domain_cap=1, lease_duration=timedelta(minutes=10)),
        )

        self.assertEqual(("https://nvidia.com/", "https://amd.com/security"), tuple(item.canonical_url for item in claimed.items))
        self.assertEqual(2, sum(1 for item in claimed.queue if item.lease_owner == "worker-c"))
        self.assertIsNone(queue[0].lease_owner)

        succeeded_target, released_row = record_crawl_success(
            boosted[0],
            claimed.items[0],
            fetched_at=NOW + timedelta(seconds=5),
            content_hash="abc123",
            status_code=200,
            recrawl_after=timedelta(hours=12),
        )

        self.assertEqual("abc123", succeeded_target.content_hash)
        self.assertEqual(NOW + timedelta(hours=12, seconds=5), succeeded_target.next_crawl_at)
        self.assertIsNone(released_row.lease_owner)

    def test_failure_backoff_requeues_until_retry_limit_then_blocks(self) -> None:
        source_policy = SourcePolicy(
            source_id="company-site",
            publisher="Company site",
            license_label="public",
            data_class="public_evidence",
            allowed_uses=("crawl",),
        )
        target = seed_crawl_target(
            "https://example.com/pricing",
            source_policy=source_policy,
            page_type="pricing",
            base_priority=50,
            discovered_at=NOW,
        )
        queue_item = CrawlQueueItem.from_target(target, available_at=NOW).lease(
            owner="worker-c",
            leased_at=NOW,
            lease_duration=timedelta(minutes=10),
        )

        retry_target, retry_row = record_crawl_failure(
            target,
            queue_item,
            failed_at=NOW + timedelta(minutes=1),
            status_code=429,
            error_code="rate_limited",
            policy=FrontierPolicy(max_retries=2, backoff_base=timedelta(minutes=5)),
        )

        self.assertEqual(1, retry_target.failure_count)
        self.assertEqual(NOW + timedelta(minutes=6), retry_row.available_at)
        self.assertIsNone(retry_row.lease_owner)

        blocked_target, blocked_row = record_crawl_failure(
            retry_target,
            retry_row.lease(
                owner="worker-c",
                leased_at=NOW + timedelta(minutes=6),
                lease_duration=timedelta(minutes=10),
            ),
            failed_at=NOW + timedelta(minutes=7),
            status_code=429,
            error_code="rate_limited",
            policy=FrontierPolicy(max_retries=2, backoff_base=timedelta(minutes=5)),
        )

        self.assertTrue(blocked_target.blocked)
        self.assertEqual(datetime.max.replace(tzinfo=timezone.utc), blocked_row.available_at)

    def test_typed_equity_event_creates_deterministic_boost(self) -> None:
        event = EquityEvent(
            event_id="evt-nvda-earnings",
            event_type=EquityEventType.EARNINGS,
            ticker="nvda",
            source_uri="https://nvidia.com/news/earnings",
            observed_at=NOW,
            confidence=0.9,
            summary="Earnings release",
        )

        boost = event.to_priority_boost(
            url_prefix="https://nvidia.com/",
            priority_delta=40,
            available_at=NOW - timedelta(minutes=5),
        )

        self.assertEqual("NVDA", event.ticker)
        self.assertEqual("event:earnings:evt-nvda-earnings", boost.reason)
        self.assertEqual(40, boost.priority_delta)

    def test_stub_connector_returns_registered_results_without_network(self) -> None:
        connector = StubSourceConnector(
            connector_id="fixture",
            results={
                "https://example.com/docs": ConnectorFetchResult(
                    canonical_url="https://example.com/docs",
                    status_code=200,
                    fetched_at=NOW,
                    content="docs content",
                    content_hash="hash-docs",
                    discovered_urls=("https://example.com/pricing",),
                )
            },
        )

        result = connector.fetch("HTTPS://example.com/docs?utm_source=x")

        self.assertEqual("https://example.com/docs", result.canonical_url)
        self.assertEqual(("https://example.com/pricing",), result.discovered_urls)

        with self.assertRaisesRegex(KeyError, "no stub result"):
            connector.fetch("https://example.com/missing")


if __name__ == "__main__":
    unittest.main()
