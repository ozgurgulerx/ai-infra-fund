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


class TradeJournalApiTests(unittest.TestCase):
    def test_post_trade_journal_entry_creates_local_manual_record(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeTradeJournalRepository()
        client = TestClient(main.create_app(trade_journal_repository=repository))

        response = client.post(
            "/internal/trade-journal/entries",
            json={
                "ticker": "nvda",
                "side": "buy",
                "quantity": "2",
                "price": "900.00",
                "fees": "1.25",
                "trade_date": "2026-05-14",
                "settlement_date": "2026-05-15",
                "account_label": "local",
                "status": "completed",
                "notes": "manual local journal entry",
            },
        )

        self.assertEqual(201, response.status_code)
        payload = response.json()["data"]
        self.assertEqual("NVDA", payload["ticker"])
        self.assertEqual("buy", payload["side"])
        self.assertEqual("completed", payload["status"])
        self.assertEqual("manual_ui", payload["source"])
        self.assertTrue(payload["journal_only"])
        self.assertEqual(1, len(repository.created))
        self.assertEqual("manual_ui", repository.created[0].source)

    def test_post_trade_journal_entry_rejects_invalid_payload(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeTradeJournalRepository()
        client = TestClient(main.create_app(trade_journal_repository=repository))

        response = client.post(
            "/internal/trade-journal/entries",
            json={
                "ticker": "",
                "side": "buy",
                "quantity": "-1",
                "trade_date": "2026-05-14",
                "account_label": "local",
                "status": "completed",
            },
        )

        self.assertEqual(422, response.status_code)
        self.assertEqual("invalid_trade_entry", response.json()["error"]["code"])
        self.assertEqual([], repository.created)

    def test_get_trade_journal_entries_returns_data_envelope(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeTradeJournalRepository()
        repository.created.append(make_trade_entry())
        client = TestClient(main.create_app(trade_journal_repository=repository))

        response = client.get("/internal/trade-journal/entries")

        self.assertEqual(200, response.status_code)
        payload = response.json()["data"]
        self.assertEqual(1, payload["total_entries"])
        self.assertEqual("NVDA", payload["entries"][0]["ticker"])
        self.assertTrue(payload["journal_only"])

    def test_trade_journal_route_has_no_broker_order_or_execution_surface(self) -> None:
        from ai_infra_fund_api import main

        app = main.create_app(trade_journal_repository=FakeTradeJournalRepository())
        paths = sorted({route.path for route in app.routes if route.path.startswith("/internal/trade-journal")})
        offenders = [
            f"{path} contains {word}"
            for path in paths
            for word in ("broker", "order", "execution", "execute")
            if word in path.lower()
        ]

        self.assertEqual(["/internal/trade-journal/entries"], paths)
        self.assertEqual([], offenders)

    def test_trade_journal_entry_rejects_delete_put_and_patch(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        client = TestClient(main.create_app(trade_journal_repository=FakeTradeJournalRepository()))
        for request in (client.put, client.patch, client.delete):
            with self.subTest(method=request.__name__):
                response = request("/internal/trade-journal/entries")
                self.assertEqual(405, response.status_code)


class FakeTradeJournalRepository:
    def __init__(self) -> None:
        self.created: list[TradeEntry] = []

    def create_trade_entry(self, trade_entry: TradeEntry) -> TradeEntry:
        self.created.append(trade_entry)
        return trade_entry

    def list_trade_entries(self, limit: int = 25) -> tuple[TradeEntry, ...]:
        return tuple(self.created[:limit])


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


if __name__ == "__main__":
    unittest.main()
