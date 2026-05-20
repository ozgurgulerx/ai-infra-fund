from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
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
from ai_infra_fund_worker.crawl.seed import seed_watchlist  # noqa: E402
from ai_infra_fund_worker.crawl.worker_loop import (  # noqa: E402
    CrawlBatchReport,
    run_crawl_batch,
)


DATABASE_URL = os.getenv(
    "AI_INFRA_FUND_DATABASE_URL",
    "postgresql://ai_infra_fund:ai_infra_fund@localhost:5432/ai_infra_fund",
)


class FakeFetcher:
    """Records calls and returns canned responses keyed by URL."""

    def __init__(self, responses: dict[str, FetchResult]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, str | None, str | None]] = []

    def fetch(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        self.calls.append((url, etag, last_modified))
        if url in self._responses:
            return self._responses[url]
        # Default to 200 success with a small HTML body.
        return FetchResult(
            final_url=url,
            http_status=200,
            content_type="text/html",
            body_bytes=b"<html><title>Default</title><body>hello</body></html>",
            etag=None,
            last_modified=None,
            latency_ms=10,
            fetch_method="http_get",
            error_summary=None,
        )


class ExplodingFetcher:
    def fetch(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        raise TimeoutError("request failed with provider credentials in URL")


class FakeFrontierRepository:
    def __init__(self, metadata: dict[str, object] | None = None) -> None:
        self.metadata = dict(metadata or {})
        self.failures: list[dict[str, object]] = []
        self.recrawls: list[dict[str, object]] = []
        self.updated_metadata: list[dict[str, object]] = []

    def get_frontier_metadata(self, *, frontier_url_id: str) -> dict[str, object]:
        return dict(self.metadata)

    def update_frontier_metadata(
        self,
        *,
        frontier_url_id: str,
        metadata: dict[str, object],
        now: datetime,
    ) -> None:
        self.updated_metadata.append(
            {
                "frontier_url_id": frontier_url_id,
                "metadata": metadata,
                "now": now,
            }
        )

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


class FakeCrawlLogRepository:
    def __init__(self) -> None:
        self.records: list[object] = []

    def record_attempt(self, record: object) -> None:
        self.records.append(record)


def _reset_one_queued(connection, ticker: str) -> tuple[str, str]:
    """Mark all frontier URLs for the ticker as 'skipped', then re-queue one.

    Returns (frontier_url_id, url) of the single queued URL so the test can
    inject a canned response keyed by that exact URL. Required because
    `seed_watchlist` creates several URLs per ticker and the worker leases by
    priority — pre-picking one with `fetchone()` doesn't guarantee it'll be
    the one leased.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE evidence.source_frontier_urls "
            "SET status = 'skipped', leased_by = NULL, lease_expires_at = NULL "
            "WHERE status IN ('queued', 'retry', 'leased');"
        )
        cursor.execute(
            "UPDATE evidence.crawl_frontier_queue "
            "SET status = 'skipped', leased_by = NULL, lease_expires_at = NULL "
            "WHERE status IN ('queued', 'retry', 'leased');"
        )
        cursor.execute(
            "SELECT frontier_url_id, url FROM evidence.source_frontier_urls "
            "WHERE ticker = %s ORDER BY frontier_url_id LIMIT 1;",
            (ticker,),
        )
        row = cursor.fetchone()
        assert row is not None, f"no frontier URL seeded for {ticker}"
        frontier_url_id, url = str(row[0]), str(row[1])
        cursor.execute(
            "UPDATE evidence.source_frontier_urls "
            "SET status = 'queued', leased_by = NULL, lease_expires_at = NULL, "
            "attempt_count = 0, last_error_summary = NULL, "
            "next_attempt_at = now() - interval '1 minute' "
            "WHERE frontier_url_id = %s;",
            (frontier_url_id,),
        )
        cursor.execute(
            "UPDATE evidence.crawl_frontier_queue "
            "SET status = 'queued', leased_by = NULL, lease_expires_at = NULL, "
            "next_attempt_at = now() - interval '1 minute' "
            "WHERE frontier_url_id = %s;",
            (frontier_url_id,),
        )
    connection.commit()
    return frontier_url_id, url


@unittest.skipUnless(
    os.getenv("AI_INFRA_FUND_DATABASE_URL"),
    "set AI_INFRA_FUND_DATABASE_URL to enable integration tests",
)
class CrawlBatchSuccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = psycopg.connect(DATABASE_URL)
        self.addCleanup(self.connection.close)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.capture_root = Path(self._tmp.name)

        # Ensure watchlist is seeded.
        now = datetime.now(tz=timezone.utc).replace(microsecond=0)
        watchlist_path = ROOT / "config" / "ai_equity_watchlist.yaml"
        seed_watchlist(self.connection, watchlist_path=watchlist_path, now=now)

        self.frontier_url_id, self.target_url = _reset_one_queued(
            self.connection, "NVDA"
        )

    def test_success_path_writes_capture_event_run_log_and_schedules_recrawl(
        self,
    ) -> None:
        now = datetime.now(tz=timezone.utc).replace(microsecond=0)
        canned = {
            self.target_url: FetchResult(
                final_url=self.target_url,
                http_status=200,
                content_type="text/html",
                body_bytes=(
                    b"<html><head><title>NVIDIA Announces Q1 Press Release</title></head>"
                    b"<body><article><p>NVIDIA today reported record results.</p></article></body></html>"
                ),
                etag='"abc123"',
                last_modified="Wed, 14 May 2026 12:00:00 GMT",
                latency_ms=42,
                fetch_method="http_get",
                error_summary=None,
            )
        }
        fetcher = FakeFetcher(canned)

        report = run_crawl_batch(
            self.connection,
            worker_id=f"worker-test-{now.timestamp()}",
            policy=FrontierPolicy(batch_size=1, domain_cap=1),
            fetcher=fetcher,
            capture_store=LocalCaptureStore(self.capture_root),
            research_extractor=StubLLMClaimExtractor(),
            now=now,
        )

        self.assertIsInstance(report, CrawlBatchReport)
        self.assertEqual(1, report.leased)
        self.assertEqual(1, report.succeeded)
        self.assertEqual(0, report.failed)
        self.assertEqual(0, report.not_modified)

        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT status, next_attempt_at FROM evidence.source_frontier_urls "
                "WHERE frontier_url_id = %s;",
                (self.frontier_url_id,),
            )
            row = cursor.fetchone()
            assert row is not None
            self.assertEqual("queued", row[0])
            self.assertGreater(row[1], now)

            cursor.execute(
                "SELECT COUNT(*) FROM evidence.source_raw_captures WHERE frontier_url_id = %s;",
                (self.frontier_url_id,),
            )
            row = cursor.fetchone()
            assert row is not None
            self.assertEqual(1, int(row[0]))

            cursor.execute(
                "SELECT COUNT(*) FROM signals.equity_events WHERE ticker = 'NVDA' "
                "AND created_at >= %s;",
                (now - timedelta(seconds=5),),
            )
            row = cursor.fetchone()
            assert row is not None
            self.assertGreaterEqual(int(row[0]), 1)

            cursor.execute(
                "SELECT COUNT(*) FROM evidence.crawl_logs WHERE frontier_url_id = %s "
                "AND attempted_at >= %s;",
                (self.frontier_url_id, now - timedelta(seconds=5)),
            )
            row = cursor.fetchone()
            assert row is not None
            self.assertEqual(1, int(row[0]))

            cursor.execute(
                "SELECT COUNT(*) FROM audit.equity_intelligence_runs "
                "WHERE ticker = 'NVDA' AND created_at >= %s;",
                (now - timedelta(seconds=5),),
            )
            row = cursor.fetchone()
            assert row is not None
            self.assertGreaterEqual(int(row[0]), 1)

        # On-disk capture exists.
        captures = list(self.capture_root.glob("captures/*/*.body"))
        self.assertGreaterEqual(len(captures), 1)


@unittest.skipUnless(
    os.getenv("AI_INFRA_FUND_DATABASE_URL"),
    "set AI_INFRA_FUND_DATABASE_URL to enable integration tests",
)
class CrawlBatchFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = psycopg.connect(DATABASE_URL)
        self.addCleanup(self.connection.close)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.capture_root = Path(self._tmp.name)
        now = datetime.now(tz=timezone.utc).replace(microsecond=0)
        watchlist_path = ROOT / "config" / "ai_equity_watchlist.yaml"
        seed_watchlist(self.connection, watchlist_path=watchlist_path, now=now)

        self.frontier_url_id, self.target_url = _reset_one_queued(
            self.connection, "MSFT"
        )

    def test_5xx_records_failure_and_writes_crawl_log_with_error_summary(self) -> None:
        now = datetime.now(tz=timezone.utc).replace(microsecond=0)
        canned = {
            self.target_url: FetchResult(
                final_url=self.target_url,
                http_status=503,
                content_type=None,
                body_bytes=b"",
                etag=None,
                last_modified=None,
                latency_ms=5,
                fetch_method="http_get",
                error_summary="server_error",
            )
        }
        fetcher = FakeFetcher(canned)

        report = run_crawl_batch(
            self.connection,
            worker_id=f"worker-test-{now.timestamp()}",
            policy=FrontierPolicy(batch_size=1, domain_cap=1),
            fetcher=fetcher,
            capture_store=LocalCaptureStore(self.capture_root),
            research_extractor=StubLLMClaimExtractor(),
            now=now,
        )

        self.assertEqual(1, report.failed)

        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT status, attempt_count, last_error_summary "
                "FROM evidence.source_frontier_urls WHERE frontier_url_id = %s;",
                (self.frontier_url_id,),
            )
            row = cursor.fetchone()
            assert row is not None
            self.assertIn(row[0], ("retry", "failed"))
            self.assertEqual(1, int(row[1]))
            self.assertEqual("server_error", row[2])

            cursor.execute(
                "SELECT fetch_method, error_summary FROM evidence.crawl_logs "
                "WHERE frontier_url_id = %s AND attempted_at >= %s "
                "ORDER BY attempted_at DESC LIMIT 1;",
                (self.frontier_url_id, now - timedelta(seconds=5)),
            )
            row = cursor.fetchone()
            assert row is not None
            # HTTP 5xx — server gave us a real response, so fetch_method is
            # 'http_get' and error_summary captures the category.
            self.assertEqual("http_get", row[0])
        self.assertEqual("server_error", row[1])


class CrawlProcessOneUnitTests(unittest.TestCase):
    def test_unexpected_fetch_exception_records_failure_and_audit_log(self) -> None:
        from ai_infra_fund_worker.crawl.worker_loop import _process_one

        repo = FakeFrontierRepository()
        crawl_log_repo = FakeCrawlLogRepository()
        now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            result = _process_one(
                repo=repo,
                row={
                    "frontier_url_id": "frontier-nvda-unit",
                    "ticker": "NVDA",
                    "source_id": "source-api-finnhub",
                    "url": "https://finnhub.io/api/v1/company-news?symbol=NVDA",
                    "attempt_count": 0,
                    "max_attempts": 3,
                },
                crawl_log_repo=crawl_log_repo,
                policy=FrontierPolicy(batch_size=1, domain_cap=1),
                fetcher=ExplodingFetcher(),
                capture_store=LocalCaptureStore(Path(tmp)),
                research_extractor=StubLLMClaimExtractor(),
                now=now,
            )

        self.assertEqual("failed", result)
        self.assertEqual(1, len(repo.failures))
        self.assertEqual("unexpected_exception:TimeoutError", repo.failures[0]["error_summary"])
        self.assertEqual(1, len(crawl_log_repo.records))
        record = crawl_log_repo.records[0]
        self.assertEqual("error", record.fetch_method)
        self.assertEqual("unexpected_exception:TimeoutError", record.error_summary)
        self.assertNotIn("credentials", record.error_summary)

    def test_rate_limit_response_uses_longer_backoff_than_generic_failure(self) -> None:
        from ai_infra_fund_worker.crawl.worker_loop import _process_one

        repo = FakeFrontierRepository()
        crawl_log_repo = FakeCrawlLogRepository()
        now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
        target_url = "https://api.gdeltproject.org/api/v2/doc/doc?query=AI&maxrecords=25"
        fetcher = FakeFetcher(
            {
                target_url: FetchResult(
                    final_url=target_url,
                    http_status=429,
                    content_type="text/plain",
                    body_bytes=b"rate limit",
                    etag=None,
                    last_modified=None,
                    latency_ms=7,
                    fetch_method="http_get",
                    error_summary=None,
                )
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            result = _process_one(
                repo=repo,
                row={
                    "frontier_url_id": "frontier-nvda-gdelt",
                    "ticker": "NVDA",
                    "source_id": "source_gdelt_doc",
                    "url": target_url,
                    "attempt_count": 0,
                    "max_attempts": 3,
                },
                crawl_log_repo=crawl_log_repo,
                policy=FrontierPolicy(
                    batch_size=1,
                    domain_cap=1,
                    backoff_base=timedelta(minutes=5),
                ),
                fetcher=fetcher,
                capture_store=LocalCaptureStore(Path(tmp)),
                research_extractor=StubLLMClaimExtractor(),
                now=now,
            )

        self.assertEqual("failed", result)
        self.assertEqual(1, len(repo.failures))
        self.assertEqual("http_429", repo.failures[0]["error_summary"])
        self.assertEqual(now + timedelta(hours=1), repo.failures[0]["next_attempt_at"])
        self.assertEqual(1, len(crawl_log_repo.records))
        self.assertEqual(429, crawl_log_repo.records[0].http_status)

    def test_not_modified_schedules_recrawl_from_refresh_interval(self) -> None:
        from ai_infra_fund_worker.crawl.worker_loop import _process_one

        repo = FakeFrontierRepository(
            metadata={
                "etag": '"old"',
                "refresh_interval_minutes": 45,
                "source_kind": "company_investor_relations",
            }
        )
        crawl_log_repo = FakeCrawlLogRepository()
        now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
        target_url = "https://nvidia.example/news"
        fetcher = FakeFetcher(
            {
                target_url: FetchResult(
                    final_url=target_url,
                    http_status=304,
                    content_type=None,
                    body_bytes=b"",
                    etag='"old"',
                    last_modified="Wed, 14 May 2026 11:00:00 GMT",
                    latency_ms=9,
                    fetch_method="http_304",
                    error_summary=None,
                )
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            result = _process_one(
                repo=repo,
                row={
                    "frontier_url_id": "frontier-nvda-recrawl",
                    "ticker": "NVDA",
                    "source_id": "source-nvidia-ir",
                    "url": target_url,
                    "attempt_count": 0,
                    "max_attempts": 3,
                    "metadata": {"refresh_interval_minutes": 45},
                },
                crawl_log_repo=crawl_log_repo,
                policy=FrontierPolicy(batch_size=1, domain_cap=1),
                fetcher=fetcher,
                capture_store=LocalCaptureStore(Path(tmp)),
                research_extractor=StubLLMClaimExtractor(),
                now=now,
            )

        self.assertEqual("not_modified", result)
        self.assertEqual(1, len(repo.recrawls))
        self.assertEqual(
            now + timedelta(minutes=45),
            repo.recrawls[0]["next_attempt_at"],
        )
        self.assertEqual(1, len(crawl_log_repo.records))
        self.assertEqual("http_304", crawl_log_repo.records[0].fetch_method)

    def test_forbidden_response_uses_blocked_backoff(self) -> None:
        from ai_infra_fund_worker.crawl.worker_loop import _process_one

        repo = FakeFrontierRepository()
        crawl_log_repo = FakeCrawlLogRepository()
        now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
        target_url = "https://restricted.example/report"
        fetcher = FakeFetcher(
            {
                target_url: FetchResult(
                    final_url=target_url,
                    http_status=403,
                    content_type="text/html",
                    body_bytes=b"forbidden",
                    etag=None,
                    last_modified=None,
                    latency_ms=14,
                    fetch_method="http_get",
                    error_summary=None,
                )
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            result = _process_one(
                repo=repo,
                row={
                    "frontier_url_id": "frontier-nvda-forbidden",
                    "ticker": "NVDA",
                    "source_id": "source-restricted",
                    "url": target_url,
                    "attempt_count": 0,
                    "max_attempts": 3,
                },
                crawl_log_repo=crawl_log_repo,
                policy=FrontierPolicy(batch_size=1, domain_cap=1),
                fetcher=fetcher,
                capture_store=LocalCaptureStore(Path(tmp)),
                research_extractor=StubLLMClaimExtractor(),
                now=now,
            )

        self.assertEqual("failed", result)
        self.assertEqual(1, len(repo.failures))
        self.assertEqual("http_403", repo.failures[0]["error_summary"])
        self.assertEqual(now + timedelta(hours=24), repo.failures[0]["next_attempt_at"])
        self.assertEqual(1, len(crawl_log_repo.records))
        self.assertEqual(403, crawl_log_repo.records[0].http_status)


if __name__ == "__main__":
    unittest.main()
