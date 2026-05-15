from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))


NOW = datetime(2026, 5, 14, 21, 30, tzinfo=timezone.utc)
AS_OF = datetime(2026, 5, 14, tzinfo=timezone.utc)


def _snapshot(source: str, close: str, *, ticker: str = "NVDA"):
    from ai_infra_fund_core.equity_intelligence.connectors import MarketPriceSnapshot

    return MarketPriceSnapshot(
        ticker=ticker,
        as_of=AS_OF,
        close_price=Decimal(close),
        volume=47823200,
        source=source,
        content_hash=f"hash-{source}-{ticker}-{close}",
    )


class PriceDisagreementTests(unittest.TestCase):
    def test_no_event_when_within_threshold(self) -> None:
        from ai_infra_fund_worker.reconcile.prices import detect_price_disagreement

        event = detect_price_disagreement(
            yfinance=_snapshot("yfinance", "950.00"),
            stooq=_snapshot("stooq", "951.00"),
            occurred_at=NOW,
        )
        self.assertIsNone(event)

    def test_event_emitted_when_diff_exceeds_threshold(self) -> None:
        from ai_infra_fund_worker.reconcile.prices import detect_price_disagreement

        event = detect_price_disagreement(
            yfinance=_snapshot("yfinance", "950.00"),
            stooq=_snapshot("stooq", "960.00"),
            occurred_at=NOW,
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual("price_disagreement", event.kind)
        self.assertEqual("warn", event.severity)
        self.assertEqual(NOW, event.occurred_at)
        self.assertEqual("NVDA", event.payload["ticker"])
        self.assertEqual("950.00", event.payload["yfinance_close"])
        self.assertEqual("960.00", event.payload["stooq_close"])
        self.assertIn("diff_fraction", event.payload)

    def test_payload_includes_as_of(self) -> None:
        from ai_infra_fund_worker.reconcile.prices import detect_price_disagreement

        event = detect_price_disagreement(
            yfinance=_snapshot("yfinance", "100.00"),
            stooq=_snapshot("stooq", "200.00"),
            occurred_at=NOW,
        )
        assert event is not None
        self.assertEqual(AS_OF.isoformat(), event.payload["as_of"])

    def test_event_id_is_deterministic(self) -> None:
        from ai_infra_fund_worker.reconcile.prices import detect_price_disagreement

        a = detect_price_disagreement(
            yfinance=_snapshot("yfinance", "950.00"),
            stooq=_snapshot("stooq", "960.00"),
            occurred_at=NOW,
        )
        b = detect_price_disagreement(
            yfinance=_snapshot("yfinance", "950.00"),
            stooq=_snapshot("stooq", "960.00"),
            occurred_at=NOW,
        )
        assert a is not None and b is not None
        self.assertEqual(a.event_id, b.event_id)

    def test_custom_threshold_applies(self) -> None:
        from ai_infra_fund_worker.reconcile.prices import detect_price_disagreement

        event = detect_price_disagreement(
            yfinance=_snapshot("yfinance", "950.00"),
            stooq=_snapshot("stooq", "955.00"),
            occurred_at=NOW,
            threshold=Decimal("0.01"),
        )
        self.assertIsNone(event)

    def test_mismatched_tickers_rejected(self) -> None:
        from ai_infra_fund_worker.reconcile.prices import detect_price_disagreement

        with self.assertRaisesRegex(ValueError, "ticker"):
            detect_price_disagreement(
                yfinance=_snapshot("yfinance", "100", ticker="NVDA"),
                stooq=_snapshot("stooq", "100", ticker="AMD"),
                occurred_at=NOW,
            )

    def test_mismatched_trading_day_rejected(self) -> None:
        from ai_infra_fund_core.equity_intelligence.connectors import (
            MarketPriceSnapshot,
        )
        from ai_infra_fund_worker.reconcile.prices import detect_price_disagreement

        yfinance = MarketPriceSnapshot(
            ticker="NVDA",
            as_of=datetime(2026, 5, 14, 20, 0, tzinfo=timezone.utc),
            close_price=Decimal("950.00"),
            volume=1,
            source="yfinance",
            content_hash="hash-yf",
        )
        stooq = MarketPriceSnapshot(
            ticker="NVDA",
            as_of=datetime(2026, 5, 9, tzinfo=timezone.utc),
            close_price=Decimal("950.00"),
            volume=1,
            source="stooq",
            content_hash="hash-stooq",
        )
        with self.assertRaisesRegex(ValueError, "trading day"):
            detect_price_disagreement(yfinance=yfinance, stooq=stooq, occurred_at=NOW)

    def test_intraday_yfinance_matches_midnight_stooq_same_date(self) -> None:
        from ai_infra_fund_core.equity_intelligence.connectors import (
            MarketPriceSnapshot,
        )
        from ai_infra_fund_worker.reconcile.prices import detect_price_disagreement

        yfinance = MarketPriceSnapshot(
            ticker="NVDA",
            as_of=datetime(2026, 5, 14, 20, 0, tzinfo=timezone.utc),
            close_price=Decimal("950.00"),
            volume=1,
            source="yfinance",
            content_hash="hash-yf",
        )
        stooq = MarketPriceSnapshot(
            ticker="NVDA",
            as_of=datetime(2026, 5, 14, tzinfo=timezone.utc),
            close_price=Decimal("951.00"),
            volume=1,
            source="stooq",
            content_hash="hash-stooq",
        )
        event = detect_price_disagreement(
            yfinance=yfinance, stooq=stooq, occurred_at=NOW
        )
        self.assertIsNone(event)


class ReconcileSourcesTests(unittest.TestCase):
    def test_emits_events_to_sink(self) -> None:
        from ai_infra_fund_worker.reconcile.prices import reconcile_prices

        captured = []

        def sink(event) -> None:
            captured.append(event)

        reconcile_prices(
            yfinance_snapshots=[
                _snapshot("yfinance", "950.00", ticker="NVDA"),
                _snapshot("yfinance", "200.00", ticker="AMD"),
            ],
            stooq_snapshots=[
                _snapshot("stooq", "960.00", ticker="NVDA"),
                _snapshot("stooq", "200.50", ticker="AMD"),
            ],
            event_sink=sink,
            now=NOW,
        )

        self.assertEqual(1, len(captured))
        self.assertEqual("NVDA", captured[0].payload["ticker"])

    def test_no_emission_when_only_one_source_for_ticker(self) -> None:
        from ai_infra_fund_worker.reconcile.prices import reconcile_prices

        captured = []
        reconcile_prices(
            yfinance_snapshots=[_snapshot("yfinance", "950.00", ticker="NVDA")],
            stooq_snapshots=[],
            event_sink=captured.append,
            now=NOW,
        )
        self.assertEqual([], captured)


if __name__ == "__main__":
    unittest.main()
