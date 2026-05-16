from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.events import (  # noqa: E402
    MarketEvent,
    MarketEventDirection,
    MarketEventReviewStatus,
    MarketEventType,
)


OCCURRED_AT = datetime(2026, 5, 14, 11, 0, tzinfo=timezone.utc)
AVAILABLE_AT = datetime(2026, 5, 14, 11, 5, tzinfo=timezone.utc)


class MarketEventContractTests(unittest.TestCase):
    def test_market_event_is_first_class_contract_with_required_fields(self) -> None:
        event = self.market_event()

        self.assertTrue(is_dataclass(event))
        self.assertEqual("market-event-1", event.event_id)
        self.assertEqual(MarketEventType.CAPEX_SIGNAL, event.event_type)
        self.assertEqual(("evidence-1",), event.source_evidence_ids)
        self.assertEqual(("NVDA", "SMCI"), event.tickers)
        self.assertEqual(("NVIDIA", "Super Micro Computer"), event.companies)
        self.assertEqual(("ai_infrastructure", "data_centers"), event.themes)
        self.assertEqual(MarketEventDirection.POSITIVE, event.direction)
        self.assertEqual(MarketEventReviewStatus.USABLE, event.review_status)
        self.assertEqual(Decimal("0.82"), event.confidence)

        required_fields = {
            "event_id",
            "event_type",
            "source_evidence_ids",
            "tickers",
            "companies",
            "themes",
            "catalyst",
            "ai_relevance",
            "direction",
            "time_horizon",
            "confidence",
            "occurred_at",
            "available_at",
            "content_hash",
            "extracted_by_model_run_id",
            "review_status",
        }
        self.assertEqual(required_fields, {field.name for field in fields(event)})

    def test_market_event_accepts_string_enums_and_normalizes_tickers(self) -> None:
        event = self.market_event(
            event_type="ai_product_launch",
            direction="mixed",
            review_status="pending_review",
            tickers=("nvda", "amd"),
        )

        self.assertEqual(MarketEventType.AI_PRODUCT_LAUNCH, event.event_type)
        self.assertEqual(MarketEventDirection.MIXED, event.direction)
        self.assertEqual(MarketEventReviewStatus.PENDING_REVIEW, event.review_status)
        self.assertEqual(("NVDA", "AMD"), event.tickers)

    def test_market_event_rejects_unknown_event_type(self) -> None:
        with self.assertRaises(ValueError):
            self.market_event(event_type="generic_web_mention")

    def test_market_event_requires_provenance_content_hash_and_available_at(self) -> None:
        invalid_overrides = [
            {"source_evidence_ids": ()},
            {"source_evidence_ids": None},
            {"content_hash": ""},
            {"available_at": None},
        ]

        for overrides in invalid_overrides:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.market_event(**overrides)

    def test_market_event_rejects_missing_ticker_theme_or_catalyst_context(self) -> None:
        invalid_overrides = [
            {"tickers": ()},
            {"companies": ()},
            {"themes": ()},
            {"catalyst": ""},
            {"ai_relevance": ""},
            {"time_horizon": ""},
        ]

        for overrides in invalid_overrides:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.market_event(**overrides)

    def test_market_event_bounds_confidence(self) -> None:
        with self.assertRaises(ValueError):
            self.market_event(confidence=Decimal("-0.01"))

        with self.assertRaises(ValueError):
            self.market_event(confidence=Decimal("1.01"))

        self.assertEqual(Decimal("0"), self.market_event(confidence=Decimal("0")).confidence)
        self.assertEqual(Decimal("1"), self.market_event(confidence=Decimal("1")).confidence)

    def test_market_event_requires_aware_point_in_time_datetimes(self) -> None:
        with self.assertRaises(ValueError):
            self.market_event(occurred_at=datetime(2026, 5, 14, 11, 0))

        with self.assertRaises(ValueError):
            self.market_event(available_at=datetime(2026, 5, 14, 11, 5))

        with self.assertRaises(ValueError):
            self.market_event(
                occurred_at=AVAILABLE_AT,
                available_at=OCCURRED_AT,
            )

    def test_usable_market_event_cannot_exist_without_evidence(self) -> None:
        with self.assertRaises(ValueError):
            self.market_event(
                source_evidence_ids=(),
                review_status=MarketEventReviewStatus.USABLE,
            )

    def test_deterministic_market_event_can_have_no_model_run_id(self) -> None:
        event = self.market_event(extracted_by_model_run_id=None)

        self.assertIsNone(event.extracted_by_model_run_id)

    def test_model_extracted_market_event_requires_non_empty_model_run_id(self) -> None:
        event = self.market_event(extracted_by_model_run_id="model-run-1")

        self.assertEqual("model-run-1", event.extracted_by_model_run_id)

        with self.assertRaises(ValueError):
            self.market_event(extracted_by_model_run_id="")

    def test_contract_has_no_model_client_or_execution_imports(self) -> None:
        text = (CORE_SRC / "ai_infra_fund_core" / "contracts" / "events.py").read_text(encoding="utf-8")
        forbidden = [
            "from azure",
            "import azure",
            "from openai",
            "import openai",
            "from anthropic",
            "import anthropic",
            "model_routing",
            "place_order",
            "submit_order",
            "broker_client",
            "live_order",
            "order_execution",
        ]

        offenders = [pattern for pattern in forbidden if pattern in text]
        self.assertEqual([], offenders)

    def market_event(self, **overrides: object) -> MarketEvent:
        data = {
            "event_id": "market-event-1",
            "event_type": MarketEventType.CAPEX_SIGNAL,
            "source_evidence_ids": ("evidence-1",),
            "tickers": ("nvda", "SMCI"),
            "companies": ("NVIDIA", "Super Micro Computer"),
            "themes": ("ai_infrastructure", "data_centers"),
            "catalyst": "Hyperscaler capex guidance increased for AI data centers.",
            "ai_relevance": "Higher AI capex can pull accelerator, server, and power-chain demand forward.",
            "direction": MarketEventDirection.POSITIVE,
            "time_horizon": "short_to_medium",
            "confidence": Decimal("0.82"),
            "occurred_at": OCCURRED_AT,
            "available_at": AVAILABLE_AT,
            "content_hash": "hash-market-event-1",
            "extracted_by_model_run_id": "model-run-1",
            "review_status": MarketEventReviewStatus.USABLE,
        }
        data.update(overrides)
        return MarketEvent(**data)


if __name__ == "__main__":
    unittest.main()
