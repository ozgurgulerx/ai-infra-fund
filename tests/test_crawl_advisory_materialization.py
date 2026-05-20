from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, API_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_api.repositories.equity_intelligence import (  # noqa: E402
    EquityIntelligenceRepository,
)
from ai_infra_fund_core.equity_intelligence.advisory_materializer import (  # noqa: E402
    materialize_crawl_advisory_records,
)
from ai_infra_fund_core.equity_intelligence.capture import LocalCaptureStore  # noqa: E402
from ai_infra_fund_core.equity_intelligence.event_extractor import (  # noqa: E402
    EquityEventRecord,
)
from ai_infra_fund_core.equity_intelligence.fetcher import FetchResult  # noqa: E402
from ai_infra_fund_core.equity_intelligence.frontier import FrontierPolicy  # noqa: E402
from ai_infra_fund_core.equity_intelligence.research_extractor import (  # noqa: E402
    StubLLMClaimExtractor,
)
from ai_infra_fund_worker.crawl.worker_loop import _process_one  # noqa: E402


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class CrawlAdvisoryMaterializerTests(unittest.TestCase):
    def test_maps_legacy_event_and_capture_provenance_to_canonical_rows(self) -> None:
        event = equity_event()
        capture = capture_record()

        materialized = materialize_crawl_advisory_records(
            capture=capture,
            equity_events=(event,),
            frontier_metadata={
                "source_kind": "company_investor_relations",
                "company_name": "NVIDIA Corporation",
                "themes": ("ai_accelerators",),
            },
        )

        self.assertEqual(1, len(materialized.source_signals))
        self.assertEqual(1, len(materialized.market_events))
        signal = materialized.source_signals[0]
        market_event = materialized.market_events[0]

        self.assertEqual("company_investor_relations", signal.source_type)
        self.assertEqual("company_ir_press", signal.signal_category)
        self.assertEqual(("NVDA",), signal.tickers)
        self.assertEqual(("ai_accelerators",), signal.themes)
        self.assertEqual(("evidence-capture-1",), signal.evidence_ids)
        self.assertEqual((market_event.event_id,), signal.derived_market_event_ids)
        self.assertEqual("hash-capture-1", signal.content_hash)
        self.assertEqual(NOW, signal.observed_at)
        self.assertEqual(NOW, signal.available_at)
        self.assertEqual("deterministic", signal.review_status)
        self.assertEqual("https://example.test/nvda", signal.payload["source_url"])
        self.assertEqual("company_investor_relations", signal.payload["source_kind"])

        self.assertEqual("customer_adoption_signal", market_event.event_type)
        self.assertEqual((signal.signal_id,), market_event.source_signal_ids)
        self.assertEqual(("evidence-capture-1",), market_event.evidence_ids)
        self.assertEqual(("NVIDIA Corporation",), market_event.companies)
        self.assertEqual("NVIDIA announces AI infrastructure platform update", market_event.catalyst)
        self.assertEqual("hash-capture-1", market_event.content_hash)
        self.assertEqual("deterministic", market_event.review_status)
        self.assertEqual("https://example.test/nvda", market_event.payload["source_url"])
        self.assertNotIn("order", json.dumps(market_event.payload).lower())
        self.assertNotIn("execution", json.dumps(signal.payload).lower())


class EquityIntelligenceCanonicalSaveTests(unittest.TestCase):
    def test_atomic_crawl_save_includes_analyst_source_signals_and_market_events(self) -> None:
        connection = FakeConnection()
        repository = EquityIntelligenceRepository(connection)
        event = equity_event()
        capture = capture_record()
        materialized = materialize_crawl_advisory_records(
            capture=capture,
            equity_events=(event,),
            frontier_metadata={"source_kind": "company_investor_relations"},
        )

        repository.save_crawl_capture_advisory_materials_and_run(
            source_raw_capture=capture,
            equity_events=(event,),
            source_signals=materialized.source_signals,
            market_events=materialized.market_events,
            intelligence_run=run_record(),
        )

        statements = "\n".join(
            statement for statement, _params in connection.cursor_instance.executions
        )
        self.assertIn("INSERT INTO evidence.source_raw_captures", statements)
        self.assertIn("INSERT INTO signals.equity_events", statements)
        self.assertIn("INSERT INTO analyst.source_signals", statements)
        self.assertIn("INSERT INTO analyst.market_events", statements)
        self.assertIn("INSERT INTO audit.equity_intelligence_runs", statements)
        self.assertEqual(1, connection.commit_count)
        self.assertEqual(5, len(connection.cursor_instance.executions))


class CrawlWorkerCanonicalSuccessUnitTests(unittest.TestCase):
    def test_success_path_materializes_canonical_objects_from_fake_capture(self) -> None:
        repo = FakeWorkerRepository()
        crawl_log_repo = FakeCrawlLogRepository()
        now = NOW
        with tempfile.TemporaryDirectory() as tmp:
            outcome = _process_one(
                repo=repo,
                crawl_log_repo=crawl_log_repo,
                row={
                    "frontier_url_id": "frontier-nvda-unit",
                    "ticker": "NVDA",
                    "source_id": "source-nvidia-ir",
                    "url": "https://example.test/nvda",
                    "attempt_count": 0,
                    "max_attempts": 3,
                    "metadata": {"source_kind": "company_investor_relations"},
                },
                policy=FrontierPolicy(batch_size=1, domain_cap=1),
                fetcher=FakeSuccessFetcher(),
                capture_store=LocalCaptureStore(Path(tmp)),
                research_extractor=StubLLMClaimExtractor(),
                now=now,
            )

        self.assertEqual("succeeded", outcome)
        self.assertEqual(1, len(repo.saved))
        saved = repo.saved[0]
        self.assertEqual(1, len(saved["source_signals"]))
        self.assertEqual(1, len(saved["market_events"]))
        signal = saved["source_signals"][0]
        market_event = saved["market_events"][0]
        self.assertEqual("company_investor_relations", signal.source_type)
        self.assertEqual("https://example.test/nvda", signal.payload["source_url"])
        self.assertEqual((signal.signal_id,), market_event.source_signal_ids)
        self.assertEqual(signal.evidence_ids, market_event.evidence_ids)
        self.assertEqual(1, len(crawl_log_repo.records))
        self.assertEqual("frontier-nvda-unit", repo.recrawls[0]["frontier_url_id"])


def equity_event(**overrides: object) -> EquityEventRecord:
    data = {
        "event_id": "event-nvda-1",
        "ticker": "NVDA",
        "event_type": "company_ir_press",
        "event_time": NOW,
        "available_at": NOW,
        "source_capture_id": "capture-1",
        "summary": "NVIDIA announces AI infrastructure platform update",
        "severity": "low",
        "evidence_ids": [],
        "evidence_claim_ids": [],
        "model_run_ids": [],
        "review_status": "deterministic",
        "metadata": {"origin": "html_capture", "source_id": "source-nvidia-ir"},
        "content_hash": "hash-event-1",
        "created_at": NOW,
    }
    data.update(overrides)
    return EquityEventRecord(**data)


def capture_record(**overrides: object) -> SimpleNamespace:
    data = {
        "capture_id": "capture-1",
        "frontier_url_id": "frontier-1",
        "source_id": "source-nvidia-ir",
        "url": "https://example.test/nvda",
        "captured_at": NOW,
        "http_status": 200,
        "content_hash": "hash-capture-1",
        "storage_uri": "file://captures/hash.body",
        "content_type": "text/html",
        "byte_size": 100,
        "metadata": {"fetch_method": "http_get"},
        "created_at": NOW,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def run_record() -> SimpleNamespace:
    return SimpleNamespace(
        run_id="run-1",
        ticker="NVDA",
        started_at=NOW,
        completed_at=NOW,
        status="succeeded",
        source_refresh_job_ids=[],
        frontier_url_ids=["frontier-1"],
        capture_ids=["capture-1"],
        event_ids=["event-nvda-1"],
        sentiment_snapshot_id=None,
        technical_snapshot_id=None,
        fundamental_snapshot_id=None,
        summary={"events_emitted": 1},
        model_run_ids=[],
        error_summary=None,
        created_at=NOW,
    )


class FakeCursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params or ()))

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


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
                b"<html><head><title>NVIDIA Announces Platform Update</title></head>"
                b"<body>AI infrastructure update.</body></html>"
            ),
            etag='"abc"',
            last_modified="Wed, 14 May 2026 12:00:00 GMT",
            latency_ms=7,
            fetch_method="http_get",
            error_summary=None,
        )


class FakeWorkerRepository:
    def __init__(self) -> None:
        self.saved: list[dict[str, object]] = []
        self.recrawls: list[dict[str, object]] = []
        self.updated_metadata: list[dict[str, object]] = []

    def get_frontier_metadata(self, *, frontier_url_id: str) -> dict[str, object]:
        return {"source_kind": "company_investor_relations"}

    def save_crawl_capture_advisory_materials_and_run(self, **kwargs: object) -> dict[str, object]:
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


class FakeCrawlLogRepository:
    def __init__(self) -> None:
        self.records: list[object] = []

    def record_attempt(self, record: object) -> None:
        self.records.append(record)


if __name__ == "__main__":
    unittest.main()
