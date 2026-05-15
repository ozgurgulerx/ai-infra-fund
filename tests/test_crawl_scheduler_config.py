from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))


class SchedulerConfigUserAgentTests(unittest.TestCase):
    def _make(self, user_agent: str):
        from ai_infra_fund_core.equity_intelligence.frontier import FrontierPolicy
        from ai_infra_fund_worker.crawl.scheduler import SchedulerConfig

        return SchedulerConfig(
            worker_id="test-worker",
            policy=FrontierPolicy(batch_size=1, domain_cap=1),
            captures_root=Path("/tmp/captures"),
            user_agent=user_agent,
        )

    def test_rejects_empty_user_agent(self) -> None:
        with self.assertRaisesRegex(ValueError, "user_agent is required"):
            self._make("")

    def test_rejects_generic_user_agent_without_contact(self) -> None:
        with self.assertRaisesRegex(ValueError, "contact email or URL"):
            self._make("ai-infra-fund/0.1 (advisory)")

    def test_accepts_user_agent_with_email(self) -> None:
        config = self._make("AI Infra Fund Research <ozgur@example.com>")
        self.assertIn("@", config.user_agent)

    def test_accepts_user_agent_with_url(self) -> None:
        config = self._make("AI Infra Fund Research +https://example.com/contact")
        self.assertIn("http", config.user_agent)


class SchedulerLifecycleTests(unittest.TestCase):
    def test_default_fetcher_is_reused_and_closed_on_exit(self) -> None:
        from ai_infra_fund_core.equity_intelligence.frontier import FrontierPolicy
        from ai_infra_fund_worker.crawl import scheduler
        from ai_infra_fund_worker.crawl.worker_loop import CrawlBatchReport

        class CloseAwareFetcher:
            def __init__(self) -> None:
                self.closed = False

            def close(self) -> None:
                self.closed = True

        class FakeConnection:
            def close(self) -> None:
                pass

        fetcher = CloseAwareFetcher()
        build_calls = 0

        def fake_build(_config):
            nonlocal build_calls
            build_calls += 1
            return fetcher

        def fake_batch(*_args, **_kwargs):
            return CrawlBatchReport(leased=0, succeeded=0, failed=0, not_modified=0)

        config = scheduler.SchedulerConfig(
            worker_id="test-worker",
            policy=FrontierPolicy(batch_size=1, domain_cap=1),
            captures_root=Path("/tmp/captures"),
            user_agent="AI Infra Fund Research <ozgur@example.com>",
            idle_sleep_seconds=0,
        )

        original_build = scheduler.build_default_fetcher
        original_batch = scheduler.run_crawl_batch
        original_reclaim = scheduler._reclaim_stale
        try:
            scheduler.build_default_fetcher = fake_build
            scheduler.run_crawl_batch = fake_batch
            scheduler._reclaim_stale = lambda _connection_factory: 0
            scheduler.run_forever(
                lambda: FakeConnection(),
                config=config,
                fetcher=None,
                max_loops=1,
            )
        finally:
            scheduler.build_default_fetcher = original_build
            scheduler.run_crawl_batch = original_batch
            scheduler._reclaim_stale = original_reclaim

        self.assertEqual(1, build_calls)
        self.assertTrue(fetcher.closed)


if __name__ == "__main__":
    unittest.main()
