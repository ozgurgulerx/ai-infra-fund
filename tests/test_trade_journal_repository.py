from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_core.contracts.common import TradeSide, TradeStatus  # noqa: E402
from ai_infra_fund_core.contracts.portfolio import TradeEntry  # noqa: E402


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class TradeJournalRepositoryTests(unittest.TestCase):
    def test_creates_manual_trade_entry_with_parameterized_insert(self) -> None:
        from ai_infra_fund_api.repositories.trade_journal import TradeJournalRepository

        trade_entry = make_trade_entry()
        connection = FakeConnection(return_rows=[trade_row(trade_entry)])

        saved = TradeJournalRepository(connection).create_trade_entry(trade_entry)

        self.assertEqual(trade_entry, saved)
        self.assertEqual(1, connection.commit_count)
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("INSERT INTO core.trade_entries", statement)
        self.assertNotIn(trade_entry.ticker, statement)
        self.assertNotIn("broker", statement.lower())
        self.assertNotIn("execute", statement.lower())
        self.assertIn(trade_entry.ticker, params)
        self.assertIn(TradeSide.BUY.value, params)
        self.assertIn(TradeStatus.COMPLETED.value, params)
        self.assertIn("manual_ui", params)

    def test_lists_recent_trade_entries_without_mutating(self) -> None:
        from ai_infra_fund_api.repositories.trade_journal import TradeJournalRepository

        trade_entry = make_trade_entry()
        connection = FakeConnection(return_rows=[trade_row(trade_entry)])

        entries = TradeJournalRepository(connection).list_trade_entries(limit=10)

        self.assertEqual((trade_entry,), entries)
        self.assertEqual(0, connection.commit_count)
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("SELECT", statement)
        self.assertIn("FROM core.trade_entries", statement)
        self.assertEqual((10,), params)


class FakeCursor:
    description = (
        ("trade_id",),
        ("ticker",),
        ("side",),
        ("quantity",),
        ("price",),
        ("fees",),
        ("trade_date",),
        ("settlement_date",),
        ("account_label",),
        ("status",),
        ("source",),
        ("notes",),
        ("created_at",),
    )

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


def make_trade_entry(**overrides: object) -> TradeEntry:
    data = {
        "trade_id": "trade-ui-nvda-1",
        "ticker": "NVDA",
        "side": TradeSide.BUY,
        "quantity": Decimal("2"),
        "price": Decimal("900"),
        "fees": Decimal("1.25"),
        "trade_date": date(2026, 5, 14),
        "settlement_date": date(2026, 5, 15),
        "account_label": "local",
        "status": TradeStatus.COMPLETED,
        "source": "manual_ui",
        "notes": "manual local journal entry",
        "created_at": NOW,
    }
    data.update(overrides)
    return TradeEntry(**data)


def trade_row(trade_entry: TradeEntry) -> tuple[object, ...]:
    return (
        trade_entry.trade_id,
        trade_entry.ticker,
        trade_entry.side.value,
        trade_entry.quantity,
        trade_entry.price,
        trade_entry.fees,
        trade_entry.trade_date,
        trade_entry.settlement_date,
        trade_entry.account_label,
        trade_entry.status.value,
        trade_entry.source,
        trade_entry.notes,
        trade_entry.created_at,
    )


if __name__ == "__main__":
    unittest.main()
