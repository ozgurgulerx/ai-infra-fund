from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import stat
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, API_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_core.equity_intelligence.capture import LocalCaptureStore  # noqa: E402
from ai_infra_fund_core.equity_intelligence.fetcher import FetchResult  # noqa: E402
from ai_infra_fund_core.equity_intelligence.frontier import FrontierPolicy  # noqa: E402
from ai_infra_fund_core.equity_intelligence.research_extractor import (  # noqa: E402
    StubLLMClaimExtractor,
)
from ai_infra_fund_worker.crawl.worker_loop import _process_one  # noqa: E402


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class CrawlMaterializationLoopTests(unittest.TestCase):
    def test_successful_public_capture_materializes_evidence_signal_and_market_event(
        self,
    ) -> None:
        repo = FakeWorkerRepository(
            metadata={
                "source_kind": "company_investor_relations",
                "source_type": "company_ir",
                "license_label": "public",
                "data_class": "public_evidence",
                "company_name": "NVIDIA Corporation",
                "themes": ["ai_accelerators", "datacenter_capex"],
            }
        )
        evidence_repo = FakeEvidenceRepository()
        crawl_log_repo = FakeCrawlLogRepository()

        with tempfile.TemporaryDirectory() as tmp:
            outcome = _process_one(
                repo=repo,
                crawl_log_repo=crawl_log_repo,
                row={
                    "frontier_url_id": "frontier-nvda-live",
                    "ticker": "NVDA",
                    "source_id": "source-nvidia-ir",
                    "url": "https://nvidia.example/news",
                    "attempt_count": 0,
                    "max_attempts": 3,
                    "metadata": {
                        "source_kind": "company_investor_relations",
                        "license_label": "public",
                    },
                },
                policy=FrontierPolicy(batch_size=1, domain_cap=1),
                fetcher=FakeSuccessFetcher(),
                capture_store=LocalCaptureStore(Path(tmp)),
                research_extractor=StubLLMClaimExtractor(),
                now=NOW,
                evidence_repo=evidence_repo,
            )

        self.assertEqual("succeeded", outcome)
        self.assertEqual(1, len(evidence_repo.items))
        evidence_item = evidence_repo.items[0]
        self.assertEqual("https://nvidia.example/news", evidence_item.source_uri)
        self.assertEqual("company_investor_relations", evidence_item.source_type)
        self.assertEqual("public", evidence_item.license_label)
        self.assertEqual("public_evidence", evidence_item.data_class.value)
        self.assertEqual(("NVDA",), evidence_item.tickers)
        self.assertEqual(("ai_accelerators", "datacenter_capex"), evidence_item.themes)
        self.assertTrue(evidence_item.evidence_id.startswith("evidence-capture-"))

        self.assertEqual(1, len(repo.saved))
        saved = repo.saved[0]
        self.assertEqual(1, len(saved["equity_events"]))
        self.assertEqual(1, len(saved["source_signals"]))
        self.assertEqual(1, len(saved["market_events"]))

        event = saved["equity_events"][0]
        signal = saved["source_signals"][0]
        market_event = saved["market_events"][0]
        self.assertEqual([evidence_item.evidence_id], event.evidence_ids)
        self.assertEqual((evidence_item.evidence_id,), signal.evidence_ids)
        self.assertEqual((evidence_item.evidence_id,), market_event.evidence_ids)
        self.assertEqual((signal.signal_id,), market_event.source_signal_ids)
        self.assertEqual(1, len(crawl_log_repo.records))
        self.assertEqual("frontier-nvda-live", repo.recrawls[0]["frontier_url_id"])

    def test_duplicate_capture_content_uses_stable_evidence_id(self) -> None:
        first = _run_success("frontier-nvda-a", "https://nvidia.example/a")
        second = _run_success("frontier-nvda-b", "https://nvidia.example/b")

        self.assertEqual(
            first["evidence_repo"].items[0].evidence_id,
            second["evidence_repo"].items[0].evidence_id,
        )
        self.assertEqual(
            first["evidence_repo"].items[0].content_hash,
            second["evidence_repo"].items[0].content_hash,
        )

    def test_failed_fetch_writes_log_without_evidence_materialization(self) -> None:
        repo = FakeWorkerRepository()
        evidence_repo = FakeEvidenceRepository()
        crawl_log_repo = FakeCrawlLogRepository()

        with tempfile.TemporaryDirectory() as tmp:
            outcome = _process_one(
                repo=repo,
                crawl_log_repo=crawl_log_repo,
                row={
                    "frontier_url_id": "frontier-nvda-fail",
                    "ticker": "NVDA",
                    "source_id": "source-nvidia-ir",
                    "url": "https://nvidia.example/fail",
                    "attempt_count": 0,
                    "max_attempts": 3,
                },
                policy=FrontierPolicy(batch_size=1, domain_cap=1),
                fetcher=FakeFailureFetcher(),
                capture_store=LocalCaptureStore(Path(tmp)),
                research_extractor=StubLLMClaimExtractor(),
                now=NOW,
                evidence_repo=evidence_repo,
            )

        self.assertEqual("failed", outcome)
        self.assertEqual([], evidence_repo.items)
        self.assertEqual([], repo.saved)
        self.assertEqual(1, len(crawl_log_repo.records))
        self.assertEqual("http_get", crawl_log_repo.records[0].fetch_method)
        self.assertEqual("server_error", crawl_log_repo.records[0].error_summary)


class CrawlMaterializationSmokeScriptTests(unittest.TestCase):
    def test_smoke_script_has_specific_materialization_failure_messages(self) -> None:
        script = ROOT / "scripts" / "crawl_materialization_smoke.sh"
        self.assertTrue(
            script.exists(), "scripts/crawl_materialization_smoke.sh missing"
        )
        mode = os.stat(script).st_mode
        self.assertTrue(
            mode & stat.S_IXUSR, "crawl materialization smoke script is not executable"
        )
        text = script.read_text(encoding="utf-8")
        for expected in (
            "frontier seeded but not leased",
            "leases acquired but fetch failed",
            "captures written but no evidence item",
            "evidence item written but no source signal",
            "source signal written but no MarketEvent",
        ):
            self.assertIn(expected, text)
        self.assertIn("evidence.source_frontier_urls", text)
        self.assertIn("evidence.crawl_frontier_queue", text)
        self.assertIn("evidence.crawl_logs", text)
        self.assertIn("evidence.evidence_items", text)
        self.assertIn("analyst.source_signals", text)
        self.assertIn("analyst.market_events", text)


def _run_success(frontier_url_id: str, url: str) -> dict[str, object]:
    repo = FakeWorkerRepository()
    evidence_repo = FakeEvidenceRepository()
    crawl_log_repo = FakeCrawlLogRepository()
    with tempfile.TemporaryDirectory() as tmp:
        outcome = _process_one(
            repo=repo,
            crawl_log_repo=crawl_log_repo,
            row={
                "frontier_url_id": frontier_url_id,
                "ticker": "NVDA",
                "source_id": "source-nvidia-ir",
                "url": url,
                "attempt_count": 0,
                "max_attempts": 3,
                "metadata": {"source_kind": "company_investor_relations"},
            },
            policy=FrontierPolicy(batch_size=1, domain_cap=1),
            fetcher=FakeSuccessFetcher(),
            capture_store=LocalCaptureStore(Path(tmp)),
            research_extractor=StubLLMClaimExtractor(),
            now=NOW,
            evidence_repo=evidence_repo,
        )
    assert outcome == "succeeded"
    return {"repo": repo, "evidence_repo": evidence_repo}


class FakeSuccessFetcher:
    def fetch(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        return FetchResult(
            final_url=url,
            http_status=200,
            content_type="text/html",
            body_bytes=(
                b"<html><head><title>NVIDIA Announces AI Infrastructure Update</title></head>"
                b"<body><article>NVIDIA announced an AI infrastructure platform update.</article></body></html>"
            ),
            etag='"abc"',
            last_modified="Wed, 14 May 2026 12:00:00 GMT",
            latency_ms=12,
            fetch_method="http_get",
            error_summary=None,
        )


class FakeFailureFetcher:
    def fetch(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        return FetchResult(
            final_url=url,
            http_status=503,
            content_type=None,
            body_bytes=b"",
            etag=None,
            last_modified=None,
            latency_ms=12,
            fetch_method="http_get",
            error_summary="server_error",
        )


class FakeWorkerRepository:
    def __init__(self, metadata: dict[str, object] | None = None) -> None:
        self._metadata = dict(metadata or {"source_kind": "company_investor_relations"})
        self.saved: list[dict[str, object]] = []
        self.recrawls: list[dict[str, object]] = []
        self.updated_metadata: list[dict[str, object]] = []
        self.failures: list[dict[str, object]] = []

    def get_frontier_metadata(self, *, frontier_url_id: str) -> dict[str, object]:
        return dict(self._metadata)

    def save_crawl_capture_advisory_materials_and_run(
        self,
        **kwargs: object,
    ) -> dict[str, object]:
        self.saved.append(dict(kwargs))
        return dict(kwargs)

    def update_frontier_metadata(
        self,
        *,
        frontier_url_id: str,
        metadata: dict[str, object],
        now: datetime,
    ) -> None:
        self.updated_metadata.append(metadata)

    def schedule_frontier_recrawl(
        self,
        *,
        frontier_url_id: str,
        next_attempt_at: datetime,
        now: datetime,
    ) -> None:
        self.recrawls.append(
            {
                "frontier_url_id": frontier_url_id,
                "next_attempt_at": next_attempt_at,
                "now": now,
            }
        )

    def record_frontier_failure(
        self,
        *,
        frontier_url_id: str,
        error_summary: str,
        next_attempt_at: datetime,
        now: datetime,
    ) -> None:
        self.failures.append(
            {
                "frontier_url_id": frontier_url_id,
                "error_summary": error_summary,
                "next_attempt_at": next_attempt_at,
                "now": now,
            }
        )


class FakeEvidenceRepository:
    def __init__(self) -> None:
        self.items: list[object] = []

    def save_item(self, item: object) -> object:
        self.items.append(item)
        return item


class FakeCrawlLogRepository:
    def __init__(self) -> None:
        self.records: list[object] = []

    def record_attempt(self, record: object) -> None:
        self.records.append(record)


if __name__ == "__main__":
    unittest.main()
