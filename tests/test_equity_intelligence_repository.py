from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_api.repositories.equity_intelligence import (  # noqa: E402
    EquityIntelligenceRepository,
)


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 5, 14, 12, 30, tzinfo=timezone.utc)
BACKOFF = NOW + timedelta(minutes=20)

WATCHED_EQUITY_FIELDS = (
    "ticker",
    "company_name",
    "exchange",
    "asset_type",
    "active",
    "priority",
    "tags",
    "thesis",
    "created_at",
    "updated_at",
)

SOURCE_FIELDS = (
    "source_id",
    "source_name",
    "source_type",
    "base_url",
    "license_label",
    "data_class",
    "reliability_score",
    "metadata",
    "active",
    "created_at",
    "updated_at",
)

FRONTIER_FIELDS = (
    "frontier_url_id",
    "source_id",
    "url",
    "url_hash",
    "ticker",
    "priority",
    "discovered_at",
    "next_attempt_at",
    "status",
    "attempt_count",
    "max_attempts",
    "metadata",
    "created_at",
    "updated_at",
)

CAPTURE_FIELDS = (
    "capture_id",
    "frontier_url_id",
    "source_id",
    "url",
    "captured_at",
    "http_status",
    "content_hash",
    "storage_uri",
    "content_type",
    "byte_size",
    "metadata",
    "created_at",
)

EVENT_FIELDS = (
    "event_id",
    "ticker",
    "event_type",
    "event_time",
    "source_capture_id",
    "summary",
    "severity",
    "evidence_ids",
    "metadata",
    "content_hash",
    "created_at",
)

SENTIMENT_FIELDS = (
    "snapshot_id",
    "ticker",
    "as_of",
    "source_capture_id",
    "sentiment_score",
    "confidence",
    "drivers",
    "content_hash",
    "created_at",
)

TECHNICAL_FIELDS = (
    "snapshot_id",
    "ticker",
    "as_of",
    "indicators",
    "trend_label",
    "content_hash",
    "created_at",
)

FUNDAMENTAL_FIELDS = (
    "snapshot_id",
    "ticker",
    "as_of",
    "metrics",
    "rating_label",
    "content_hash",
    "created_at",
)

RUN_FIELDS = (
    "run_id",
    "ticker",
    "started_at",
    "completed_at",
    "status",
    "source_refresh_job_ids",
    "frontier_url_ids",
    "capture_ids",
    "event_ids",
    "sentiment_snapshot_id",
    "technical_snapshot_id",
    "fundamental_snapshot_id",
    "summary",
    "model_run_ids",
    "error_summary",
    "created_at",
)

SUMMARY_COLUMNS = (
    "ticker",
    "latest_event_at",
    "latest_event_summary",
    "sentiment_snapshot_id",
    "sentiment_as_of",
    "sentiment_score",
    "technical_snapshot_id",
    "technical_as_of",
    "trend_label",
    "fundamental_snapshot_id",
    "fundamental_as_of",
    "rating_label",
    "latest_run_id",
    "latest_run_status",
)


class EquityIntelligenceRepositoryTests(unittest.TestCase):
    def test_upserts_watched_equity_source_and_frontier_url_with_parameterized_sql(self) -> None:
        connection = FakeConnection()
        repository = EquityIntelligenceRepository(connection)

        repository.upsert_watched_equity(record_from(watched_equity(), WATCHED_EQUITY_FIELDS))
        repository.upsert_source(record_from(source(), SOURCE_FIELDS))
        repository.upsert_frontier_url(record_from(frontier_url(), FRONTIER_FIELDS))

        self.assertEqual(3, connection.commit_count)
        watched_statement, watched_params = connection.cursor_instance.executions[0]
        source_statement, source_params = connection.cursor_instance.executions[1]
        frontier_statement, frontier_params = connection.cursor_instance.executions[2]
        self.assertIn("INSERT INTO core.watched_equities", watched_statement)
        self.assertIn("ON CONFLICT (ticker) DO UPDATE SET", watched_statement)
        self.assertIn("INSERT INTO evidence.source_registry", source_statement)
        self.assertIn("ON CONFLICT (source_id) DO UPDATE SET", source_statement)
        self.assertIn("INSERT INTO evidence.source_frontier_urls", frontier_statement)
        self.assertIn("ON CONFLICT (source_id, url_hash) DO UPDATE SET", frontier_statement)
        for statement in (watched_statement, source_statement, frontier_statement):
            self.assertNotIn("NVDA", statement)
            self.assertNotIn("https://example.test/nvda", statement)
        self.assertEqual("NVDA", watched_params[0])
        self.assertEqual("source-sec", source_params[0])
        self.assertEqual("frontier-1", frontier_params[0])

    def test_leases_due_frontier_urls_with_skip_locked_and_bound_limit(self) -> None:
        row = frontier_url_row()
        connection = FakeConnection(rows=[row], columns=FRONTIER_FIELDS)

        leased = EquityIntelligenceRepository(connection).lease_due_frontier_urls(
            worker_id="worker-a",
            lease_expires_at=LATER,
            limit=10,
            now=NOW,
        )

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FOR UPDATE SKIP LOCKED", statement)
        self.assertIn("LIMIT %s", statement)
        self.assertIn("UPDATE evidence.source_frontier_urls", statement)
        self.assertNotIn("worker-a", statement)
        self.assertEqual(("worker-a", LATER, NOW, 10), params)
        self.assertEqual([dict(zip(FRONTIER_FIELDS, row, strict=True))], leased)
        self.assertEqual(0, connection.commit_count)

    def test_records_retry_backoff_without_interpolating_error_summary(self) -> None:
        connection = FakeConnection()

        EquityIntelligenceRepository(connection).record_frontier_failure(
            frontier_url_id="frontier-1",
            error_summary="HTTP 429 from source",
            next_attempt_at=BACKOFF,
            now=NOW,
        )

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("attempt_count = attempt_count + 1", statement)
        self.assertIn("next_attempt_at = %s", statement)
        self.assertIn("CASE WHEN attempt_count + 1 >= max_attempts THEN 'failed' ELSE 'retry' END", statement)
        self.assertNotIn("HTTP 429", statement)
        self.assertEqual(("HTTP 429 from source", BACKOFF, NOW, "frontier-1"), params)
        self.assertEqual(1, connection.commit_count)

    def test_refresh_priority_boost_records_job_and_updates_due_frontier_urls(self) -> None:
        connection = FakeConnection()
        job = SimpleNamespace(
            refresh_job_id="refresh-nvda-1",
            ticker="NVDA",
            reason="earnings acceleration",
            priority_boost=25,
            requested_at=NOW,
            status="queued",
        )

        EquityIntelligenceRepository(connection).boost_refresh_priority(job)

        self.assertEqual(1, connection.commit_count)
        insert_statement, insert_params = connection.cursor_instance.executions[0]
        update_statement, update_params = connection.cursor_instance.executions[1]
        self.assertIn("INSERT INTO evidence.source_refresh_jobs", insert_statement)
        self.assertIn("ON CONFLICT (refresh_job_id) DO UPDATE SET", insert_statement)
        self.assertIn("UPDATE evidence.source_frontier_urls", update_statement)
        self.assertIn("priority = priority + %s", update_statement)
        self.assertNotIn("earnings acceleration", insert_statement)
        self.assertEqual(("refresh-nvda-1", "NVDA", "earnings acceleration", 25, NOW, "queued"), insert_params)
        self.assertEqual((25, NOW, "NVDA"), update_params)

    def test_persists_raw_capture_events_snapshots_and_run_in_one_parameterized_transaction(self) -> None:
        connection = FakeConnection()
        repository = EquityIntelligenceRepository(connection)

        saved = repository.save_capture_event_snapshots_and_run(
            source_raw_capture=record_from(raw_capture(), CAPTURE_FIELDS),
            equity_event=record_from(equity_event(), EVENT_FIELDS),
            sentiment_snapshot=record_from(sentiment_snapshot(), SENTIMENT_FIELDS),
            technical_snapshot=record_from(technical_snapshot(), TECHNICAL_FIELDS),
            fundamental_snapshot=record_from(fundamental_snapshot(), FUNDAMENTAL_FIELDS),
            intelligence_run=record_from(equity_intelligence_run(), RUN_FIELDS),
        )

        self.assertEqual("capture-1", saved["source_raw_capture"].capture_id)
        self.assertEqual("run-1", saved["intelligence_run"].run_id)
        self.assertEqual(1, connection.commit_count)
        self.assertEqual(6, len(connection.cursor_instance.executions))
        joined_statements = "\n".join(statement for statement, _params in connection.cursor_instance.executions)
        for table_name in (
            "evidence.source_raw_captures",
            "signals.equity_events",
            "signals.sentiment_snapshots",
            "signals.technical_snapshots",
            "signals.fundamental_snapshots",
            "audit.equity_intelligence_runs",
        ):
            self.assertIn(f"INSERT INTO {table_name}", joined_statements)
        self.assertNotIn("NVIDIA demand remains strong", joined_statements)
        self.assertNotIn("supply improving", joined_statements)

    def test_latest_summary_read_uses_bound_ticker_and_returns_json_safe_payload(self) -> None:
        row = (
            "NVDA",
            NOW,
            "NVIDIA demand remains strong",
            "sentiment-1",
            LATER,
            0.72,
            "technical-1",
            LATER,
            "uptrend",
            "fundamental-1",
            LATER,
            "compounder",
            "run-1",
            "succeeded",
        )
        connection = FakeConnection(rows=[row], columns=SUMMARY_COLUMNS)

        summary = EquityIntelligenceRepository(connection).get_latest_equity_summary("NVDA")

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM core.watched_equities", statement)
        self.assertIn("LEFT JOIN LATERAL", statement)
        self.assertNotIn("NVDA", statement)
        self.assertEqual(("NVDA",), params)
        self.assertEqual("2026-05-14T12:00:00+00:00", summary["latest_event_at"])
        self.assertEqual("2026-05-14T12:30:00+00:00", summary["sentiment_as_of"])
        json.dumps(summary)
        self.assertEqual(0, connection.commit_count)


class FakeCursor:
    def __init__(self, rows: list[tuple[object, ...]], columns: tuple[str, ...]) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.rows = rows
        self.description = tuple((column,) for column in columns)

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params or ()))

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def fetchone(self) -> tuple[object, ...] | None:
        return self.rows[0] if self.rows else None

    def __enter__(self) -> FakeCursor:
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


def watched_equity(**overrides: object) -> dict[str, object]:
    data = {
        "ticker": "NVDA",
        "company_name": "NVIDIA",
        "exchange": "NASDAQ",
        "asset_type": "equity",
        "active": True,
        "priority": 50,
        "tags": ("ai_accelerators", "semis"),
        "thesis": "AI infrastructure bellwether",
        "created_at": NOW,
        "updated_at": NOW,
    }
    data.update(overrides)
    return data


def source(**overrides: object) -> dict[str, object]:
    data = {
        "source_id": "source-sec",
        "source_name": "SEC EDGAR",
        "source_type": "filing",
        "base_url": "https://www.sec.gov",
        "license_label": "public",
        "data_class": "public_evidence",
        "reliability_score": 0.95,
        "metadata": {"cadence": "daily"},
        "active": True,
        "created_at": NOW,
        "updated_at": NOW,
    }
    data.update(overrides)
    return data


def frontier_url(**overrides: object) -> dict[str, object]:
    data = {
        "frontier_url_id": "frontier-1",
        "source_id": "source-sec",
        "url": "https://example.test/nvda",
        "url_hash": "hash-url-1",
        "ticker": "NVDA",
        "priority": 100,
        "discovered_at": NOW,
        "next_attempt_at": NOW,
        "status": "queued",
        "attempt_count": 0,
        "max_attempts": 3,
        "metadata": {"kind": "10-q"},
        "created_at": NOW,
        "updated_at": NOW,
    }
    data.update(overrides)
    return data


def raw_capture(**overrides: object) -> dict[str, object]:
    data = {
        "capture_id": "capture-1",
        "frontier_url_id": "frontier-1",
        "source_id": "source-sec",
        "url": "https://example.test/nvda",
        "captured_at": NOW,
        "http_status": 200,
        "content_hash": "hash-capture-1",
        "storage_uri": "local://data/raw/nvda.html",
        "content_type": "text/html",
        "byte_size": 1200,
        "metadata": {"encoding": "utf-8"},
        "created_at": NOW,
    }
    data.update(overrides)
    return data


def equity_event(**overrides: object) -> dict[str, object]:
    data = {
        "event_id": "event-1",
        "ticker": "NVDA",
        "event_type": "earnings",
        "event_time": NOW,
        "source_capture_id": "capture-1",
        "summary": "NVIDIA demand remains strong",
        "severity": "medium",
        "evidence_ids": ("evidence-1",),
        "metadata": {"quarter": "q1"},
        "content_hash": "hash-event-1",
        "created_at": NOW,
    }
    data.update(overrides)
    return data


def sentiment_snapshot(**overrides: object) -> dict[str, object]:
    data = {
        "snapshot_id": "sentiment-1",
        "ticker": "NVDA",
        "as_of": LATER,
        "source_capture_id": "capture-1",
        "sentiment_score": 0.72,
        "confidence": 0.81,
        "drivers": {"positive": ["demand"], "negative": ["margin risk"]},
        "content_hash": "hash-sentiment-1",
        "created_at": NOW,
    }
    data.update(overrides)
    return data


def technical_snapshot(**overrides: object) -> dict[str, object]:
    data = {
        "snapshot_id": "technical-1",
        "ticker": "NVDA",
        "as_of": LATER,
        "indicators": {"rsi": 61, "ema_50": "above"},
        "trend_label": "uptrend",
        "content_hash": "hash-technical-1",
        "created_at": NOW,
    }
    data.update(overrides)
    return data


def fundamental_snapshot(**overrides: object) -> dict[str, object]:
    data = {
        "snapshot_id": "fundamental-1",
        "ticker": "NVDA",
        "as_of": LATER,
        "metrics": {"revenue_growth": "strong", "gross_margin": 0.74},
        "rating_label": "compounder",
        "content_hash": "hash-fundamental-1",
        "created_at": NOW,
    }
    data.update(overrides)
    return data


def equity_intelligence_run(**overrides: object) -> dict[str, object]:
    data = {
        "run_id": "run-1",
        "ticker": "NVDA",
        "started_at": NOW,
        "completed_at": LATER,
        "status": "succeeded",
        "source_refresh_job_ids": ("refresh-nvda-1",),
        "frontier_url_ids": ("frontier-1",),
        "capture_ids": ("capture-1",),
        "event_ids": ("event-1",),
        "sentiment_snapshot_id": "sentiment-1",
        "technical_snapshot_id": "technical-1",
        "fundamental_snapshot_id": "fundamental-1",
        "summary": {"headline": "supply improving"},
        "model_run_ids": ("model-run-1",),
        "error_summary": None,
        "created_at": NOW,
    }
    data.update(overrides)
    return data


def frontier_url_row(**overrides: object) -> tuple[object, ...]:
    data = frontier_url(**overrides)
    return tuple(data[field] for field in FRONTIER_FIELDS)


def record_from(data: dict[str, object], fields: tuple[str, ...]) -> SimpleNamespace:
    return SimpleNamespace(**{field: data[field] for field in fields})


if __name__ == "__main__":
    unittest.main()
