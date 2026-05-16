from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "services" / "api" / "src"
sys.path.insert(0, str(API_SRC))


NOW = datetime(2026, 5, 16, 8, 0, tzinfo=timezone.utc)


class OutcomeJournalRepositoryTests(unittest.TestCase):
    def test_upserts_deterministic_outcome_review_record(self) -> None:
        from ai_infra_fund_api.repositories.outcome_journal import (
            OutcomeJournalEntry,
            OutcomeJournalRepository,
        )

        entry = make_entry(OutcomeJournalEntry)
        connection = FakeConnection(return_rows=[entry_row(entry)])

        saved = OutcomeJournalRepository(connection).upsert_outcome(entry)

        self.assertEqual(entry, saved)
        self.assertEqual(1, connection.commit_count)
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("INSERT INTO analyst.outcome_journal_entries", statement)
        self.assertIn("ON CONFLICT (outcome_id) DO UPDATE", statement)
        self.assertNotIn("broker", statement.lower())
        self.assertNotIn("execution", statement.lower())
        self.assertNotIn("order_id", statement.lower())
        self.assertIn("advisory_only", params)
        self.assertIn("manual-trade-1", params)
        self.assertIn(Decimal("120.50"), params)

    def test_reads_latest_outcome_reviews_with_trace_links(self) -> None:
        from ai_infra_fund_api.repositories.outcome_journal import (
            OutcomeJournalEntry,
            OutcomeJournalRepository,
        )

        entry = make_entry(OutcomeJournalEntry)
        connection = FakeConnection(return_rows=[entry_row(entry)])

        payload = OutcomeJournalRepository(connection).get_latest_outcomes(limit=10)

        self.assertEqual("available", payload["status"])
        self.assertEqual("advisory_only", payload["advisory_label"])
        self.assertEqual(1, payload["total_entries"])
        self.assertEqual("outcome-1", payload["items"][0]["outcome_id"])
        self.assertEqual(["market-event-1"], payload["items"][0]["market_event_ids"])
        self.assertEqual(["evidence-1"], payload["items"][0]["evidence_ids"])
        self.assertEqual("120.50", payload["items"][0]["net_pnl_amount"])
        self.assertEqual(0, connection.commit_count)
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM analyst.outcome_journal_entries", statement)
        self.assertEqual((10,), params)

    def test_empty_latest_outcome_reviews_returns_empty_state(self) -> None:
        from ai_infra_fund_api.repositories.outcome_journal import (
            OutcomeJournalRepository,
        )

        payload = OutcomeJournalRepository(FakeConnection(return_rows=[])).get_latest_outcomes()

        self.assertEqual("empty", payload["status"])
        self.assertEqual("advisory_only", payload["advisory_label"])
        self.assertEqual(0, payload["total_entries"])
        self.assertEqual([], payload["items"])


OUTCOME_COLUMNS = (
    "outcome_id",
    "manual_journal_entry_id",
    "advisory_id",
    "ticker",
    "market_event_ids",
    "evidence_ids",
    "review_status",
    "outcome_label",
    "invalidation_flags",
    "risk_flags",
    "gross_pnl_amount",
    "net_pnl_amount",
    "pnl_percent",
    "benchmark_pnl_percent",
    "excess_pnl_percent",
    "pnl_attribution_method",
    "pnl_attribution_note",
    "reviewed_at",
    "available_at",
    "advisory_label",
    "payload_json",
    "created_at",
    "updated_at",
)


class FakeCursor:
    description = tuple((column,) for column in OUTCOME_COLUMNS)

    def __init__(self, return_rows: list[tuple[object, ...]]) -> None:
        self.return_rows = return_rows
        self.executions: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params or ()))

    def fetchone(self) -> tuple[object, ...] | None:
        return self.return_rows[0] if self.return_rows else None

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.return_rows

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self, return_rows: list[tuple[object, ...]]) -> None:
        self.cursor_instance = FakeCursor(return_rows)
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


def make_entry(entry_type: type) -> object:
    return entry_type(
        outcome_id="outcome-1",
        manual_journal_entry_id="manual-trade-1",
        advisory_id="advisory-1",
        ticker="NVDA",
        market_event_ids=("market-event-1",),
        evidence_ids=("evidence-1",),
        review_status="reviewed",
        outcome_label="thesis_confirmed",
        invalidation_flags=("none",),
        risk_flags=("valuation",),
        gross_pnl_amount=Decimal("125.00"),
        net_pnl_amount=Decimal("120.50"),
        pnl_percent=Decimal("0.052"),
        benchmark_pnl_percent=Decimal("0.018"),
        excess_pnl_percent=Decimal("0.034"),
        pnl_attribution_method="deterministic_manual_journal",
        pnl_attribution_note="Manual local journal attribution only.",
        reviewed_at=NOW,
        available_at=NOW,
        advisory_label="advisory_only",
        payload={"source": "unit-test"},
        created_at=NOW,
        updated_at=NOW,
    )


def entry_row(entry: object) -> tuple[object, ...]:
    return tuple(
        getattr(entry, "payload") if column == "payload_json" else getattr(entry, column)
        for column in OUTCOME_COLUMNS
    )


if __name__ == "__main__":
    unittest.main()
