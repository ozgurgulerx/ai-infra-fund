from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_api.repositories.crawl_logs import (  # noqa: E402
    CrawlLogRecord,
    CrawlLogRepository,
)


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class FakeCursor:
    def __init__(
        self, rows: list[tuple[object, ...]], columns: tuple[str, ...]
    ) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.rows = rows
        self.description = tuple((column,) for column in columns)

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params or ()))

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def fetchone(self) -> tuple[object, ...] | None:
        return self.rows[0] if self.rows else None

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(
        self,
        *,
        rows: list[tuple[object, ...]] | None = None,
        columns: tuple[str, ...] = (),
    ) -> None:
        self.cursor_instance = FakeCursor(rows or [], columns)
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


class CrawlLogRepositoryTests(unittest.TestCase):
    def test_record_attempt_inserts_with_parameterized_sql(self) -> None:
        connection = FakeConnection()
        record = CrawlLogRecord(
            attempt_id="attempt-1",
            frontier_url_id="frontier-1",
            ticker="NVDA",
            source_id="source-nvidia-ir",
            url="https://investor.nvidia.com/",
            attempted_at=NOW,
            fetch_method="http_get",
            http_status=200,
            latency_ms=312,
            bytes_fetched=10_240,
            capture_id="capture-1",
            error_summary=None,
        )

        CrawlLogRepository(connection).record_attempt(record)

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("INSERT INTO evidence.crawl_logs", statement)
        self.assertIn("attempt_id", statement)
        self.assertIn("fetch_method", statement)
        self.assertNotIn("NVDA", statement)
        self.assertNotIn("https://investor.nvidia.com/", statement)
        self.assertEqual(
            (
                "attempt-1",
                "frontier-1",
                "NVDA",
                "source-nvidia-ir",
                "https://investor.nvidia.com/",
                NOW,
                "http_get",
                200,
                312,
                10_240,
                "capture-1",
                None,
            ),
            params,
        )
        self.assertEqual(1, connection.commit_count)

    def test_record_attempt_accepts_failure_without_capture(self) -> None:
        connection = FakeConnection()
        record = CrawlLogRecord(
            attempt_id="attempt-err",
            frontier_url_id="frontier-2",
            ticker="MSFT",
            source_id="source-microsoft-ir",
            url="https://www.microsoft.com/en-us/investor",
            attempted_at=NOW,
            fetch_method="error",
            http_status=None,
            latency_ms=950,
            bytes_fetched=None,
            capture_id=None,
            error_summary="connection_timeout",
        )

        CrawlLogRepository(connection).record_attempt(record)

        _statement, params = connection.cursor_instance.executions[0]
        self.assertEqual("error", params[6])
        self.assertIsNone(params[7])
        self.assertIsNone(params[9])
        self.assertIsNone(params[10])
        self.assertEqual("connection_timeout", params[11])

    def test_summarize_recent_counts_by_fetch_method_and_status_bucket(self) -> None:
        rows = [
            ("http_get", 200, 12),
            ("http_get", 404, 1),
            ("http_304", None, 3),
            ("error", None, 2),
        ]
        connection = FakeConnection(
            rows=rows, columns=("fetch_method", "http_status", "count")
        )

        summary = CrawlLogRepository(connection).summarize_recent(
            window=timedelta(hours=24),
            now=NOW,
        )

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM evidence.crawl_logs", statement)
        self.assertIn("attempted_at >= %s", statement)
        self.assertIn("GROUP BY", statement)
        self.assertEqual((NOW - timedelta(hours=24),), params)
        self.assertEqual(18, summary["total"])
        self.assertEqual(12, summary["succeeded"])
        self.assertEqual(3, summary["not_modified"])
        self.assertEqual(1, summary["client_error"])
        self.assertEqual(2, summary["failed"])

    def test_summarize_recent_returns_zeroes_when_empty(self) -> None:
        connection = FakeConnection(
            rows=[], columns=("fetch_method", "http_status", "count")
        )

        summary = CrawlLogRepository(connection).summarize_recent(
            window=timedelta(hours=24),
            now=NOW,
        )

        self.assertEqual(
            {
                "total": 0,
                "succeeded": 0,
                "not_modified": 0,
                "client_error": 0,
                "server_error": 0,
                "failed": 0,
            },
            summary,
        )


if __name__ == "__main__":
    unittest.main()
