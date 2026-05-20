from __future__ import annotations

import os
import stat
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKER_SRC = ROOT / "services" / "worker" / "src"
sys.path.insert(0, str(WORKER_SRC))


class CrawlRuntimeOperationsTests(unittest.TestCase):
    def test_local_one_shot_script_runs_crawl_frontier_once(self) -> None:
        script = ROOT / "scripts" / "run_crawl_frontier_once.sh"
        self.assertTrue(script.exists(), "scripts/run_crawl_frontier_once.sh missing")
        self.assertTrue(os.stat(script).st_mode & stat.S_IXUSR)
        text = script.read_text(encoding="utf-8")
        self.assertIn("python -m ai_infra_fund_worker.crawl run --once", text)
        self.assertIn("SEC_EDGAR_USER_AGENT", text)
        self.assertIn("AI_INFRA_FUND_SOURCE_REGISTRY_PATH", text)

    def test_cloud_one_shot_script_runs_from_cronjob_template(self) -> None:
        script = ROOT / "scripts" / "cloud_crawl_frontier_once.sh"
        self.assertTrue(script.exists(), "scripts/cloud_crawl_frontier_once.sh missing")
        self.assertTrue(os.stat(script).st_mode & stat.S_IXUSR)
        text = script.read_text(encoding="utf-8")
        self.assertIn("ai-infra-fund-crawl-frontier", text)
        self.assertIn("--from=cronjob/", text)
        self.assertIn("kubectl -n", text)
        self.assertIn("wait --for=condition=complete", text)

    def test_runtime_smoke_script_checks_recrawl_lifecycle(self) -> None:
        script = ROOT / "scripts" / "crawl_runtime_smoke.sh"
        self.assertTrue(script.exists(), "scripts/crawl_runtime_smoke.sh missing")
        self.assertTrue(os.stat(script).st_mode & stat.S_IXUSR)
        text = script.read_text(encoding="utf-8")
        for expected in (
            "source_frontier_urls",
            "crawl_frontier_queue",
            "crawl_logs",
            "next_due_at exists after success",
            "failed source does not spin hot",
            "frontier seeded but not leased",
        ):
            self.assertIn(expected, text)

    def test_aks_manifest_defines_crawl_frontier_cronjob(self) -> None:
        manifest = (ROOT / "deploy" / "aks-ai-infra-fund.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("kind: CronJob", manifest)
        self.assertIn("name: ai-infra-fund-crawl-frontier", manifest)
        self.assertIn('schedule: "*/30 * * * *"', manifest)
        self.assertIn("python", manifest)
        self.assertIn("ai_infra_fund_worker.crawl", manifest)
        self.assertIn("--once", manifest)
        self.assertIn("concurrencyPolicy: Forbid", manifest)


if __name__ == "__main__":
    unittest.main()
