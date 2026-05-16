from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.events import (  # noqa: E402
    EquityImpactAssessment,
    MarketEvent,
    MarketEventDirection,
    MarketEventReviewStatus,
    MarketEventType,
    SegmentImpact,
)
from ai_infra_fund_core.contracts.segments import (  # noqa: E402
    CORE_AI_INFRASTRUCTURE_SEGMENTS,
    Segment,
    normalize_segment,
    segments_from_themes,
)


OCCURRED_AT = datetime(2026, 5, 14, 11, 0, tzinfo=timezone.utc)
AVAILABLE_AT = datetime(2026, 5, 14, 11, 5, tzinfo=timezone.utc)


class SegmentMarketEventContractTests(unittest.TestCase):
    def test_segment_enum_covers_situational_awareness_segments(self) -> None:
        required = {
            Segment.AI_MODEL_PROGRESS,
            Segment.HYPERSCALER_CAPEX,
            Segment.AI_HARDWARE_ACCELERATORS,
            Segment.MEMORY_HBM,
            Segment.ADVANCED_PACKAGING_COWOS,
            Segment.FOUNDRY_SEMICONDUCTOR_EQUIPMENT,
            Segment.NETWORKING_INTERCONNECT,
            Segment.DATACENTER_PROVIDERS,
            Segment.POWER_GRID,
            Segment.COOLING_ELECTRICAL_INFRASTRUCTURE,
            Segment.SOVEREIGN_AI_EXPORT_CONTROLS,
            Segment.SOFTWARE_MONETIZATION,
        }

        self.assertTrue(required.issubset(set(CORE_AI_INFRASTRUCTURE_SEGMENTS)))
        self.assertEqual(Segment.HYPERSCALER_CAPEX, normalize_segment("hyperscaler_capex"))
        self.assertEqual(Segment.MEMORY_HBM, normalize_segment("hbm"))
        self.assertEqual(Segment.ADVANCED_PACKAGING_COWOS, normalize_segment("cowos"))

    def test_market_event_maps_themes_to_segments(self) -> None:
        event = self.market_event(themes=("hyperscaler_capex", "hbm", "data_centers"))

        self.assertEqual(
            (
                Segment.HYPERSCALER_CAPEX,
                Segment.MEMORY_HBM,
                Segment.DATACENTER_PROVIDERS,
            ),
            event.segments,
        )
        self.assertEqual(event.segments, segments_from_themes(event.themes))

    def test_market_event_requires_evidence_available_at_and_segment_mapping(self) -> None:
        invalid = [
            {"source_evidence_ids": ()},
            {"available_at": None},
            {"themes": ("generic_market_commentary",)},
        ]

        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.market_event(**overrides)

    def test_market_event_rejects_invalid_event_type_and_confidence(self) -> None:
        with self.assertRaises(ValueError):
            self.market_event(event_type="generic_web_crawl")

        with self.assertRaises(ValueError):
            self.market_event(confidence=Decimal("-0.01"))

        with self.assertRaises(ValueError):
            self.market_event(confidence=Decimal("1.01"))

    def test_segment_impact_identifies_first_and_second_order_tickers(self) -> None:
        impact = self.segment_impact()

        self.assertEqual(Segment.ADVANCED_PACKAGING_COWOS, impact.segment)
        self.assertEqual(("TSM", "ASML"), impact.first_order_tickers)
        self.assertEqual(("NVDA", "AMD"), impact.second_order_tickers)
        self.assertEqual(("evidence-1",), impact.source_evidence_ids)

        invalid = [
            {"first_order_tickers": ()},
            {"second_order_tickers": ()},
            {"source_evidence_ids": ()},
            {"confidence": Decimal("1.1")},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.segment_impact(**overrides)

    def test_equity_impact_assessment_requires_cases_risks_and_invalidation(self) -> None:
        assessment = self.equity_assessment()

        self.assertEqual("NVDA", assessment.ticker)
        self.assertEqual((Segment.ADVANCED_PACKAGING_COWOS,), assessment.relevant_segments)
        self.assertIn("bull", assessment.bull_case.lower())
        self.assertIn("bear", assessment.bear_case.lower())
        self.assertEqual(("cowos_capacity_delay",), assessment.risk_flags)
        self.assertTrue(assessment.invalidation)

        invalid = [
            {"bull_case": ""},
            {"bear_case": ""},
            {"risk_flags": ()},
            {"invalidation": ""},
            {"relevant_segments": ()},
            {"source_evidence_ids": ()},
            {"confidence": Decimal("-0.1")},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.equity_assessment(**overrides)

    def market_event(self, **overrides: object) -> MarketEvent:
        data = {
            "event_id": "market-event-1",
            "event_type": MarketEventType.CAPEX_SIGNAL,
            "source_evidence_ids": ("evidence-1",),
            "tickers": ("nvda", "tsm"),
            "companies": ("NVIDIA", "Taiwan Semiconductor Manufacturing"),
            "themes": ("hyperscaler_capex", "cowos"),
            "catalyst": "Hyperscaler AI capex guidance increased.",
            "ai_relevance": "More AI capex pulls accelerator and advanced packaging demand forward.",
            "direction": MarketEventDirection.POSITIVE,
            "time_horizon": "short_to_medium",
            "confidence": Decimal("0.8"),
            "occurred_at": OCCURRED_AT,
            "available_at": AVAILABLE_AT,
            "content_hash": "hash-market-event",
            "extracted_by_model_run_id": "model-run-1",
            "review_status": MarketEventReviewStatus.USABLE,
        }
        data.update(overrides)
        return MarketEvent(**data)

    def segment_impact(self, **overrides: object) -> SegmentImpact:
        data = {
            "event_id": "market-event-1",
            "segment": Segment.ADVANCED_PACKAGING_COWOS,
            "direction": MarketEventDirection.POSITIVE,
            "impact_summary": "CoWoS capacity tightness benefits suppliers and constrains accelerator shipments.",
            "first_order_tickers": ("tsm", "asml"),
            "second_order_tickers": ("nvda", "amd"),
            "source_evidence_ids": ("evidence-1",),
            "confidence": Decimal("0.75"),
        }
        data.update(overrides)
        return SegmentImpact(**data)

    def equity_assessment(self, **overrides: object) -> EquityImpactAssessment:
        data = {
            "assessment_id": "equity-impact-nvda-1",
            "event_id": "market-event-1",
            "ticker": "nvda",
            "relevant_segments": (Segment.ADVANCED_PACKAGING_COWOS,),
            "bull_case": "Bull case: constrained CoWoS supply keeps accelerator pricing power elevated.",
            "bear_case": "Bear case: packaging capacity delays defer recognized revenue.",
            "risk_flags": ("cowos_capacity_delay",),
            "invalidation": "Invalidate if CoWoS lead times normalize while accelerator demand indicators weaken.",
            "source_evidence_ids": ("evidence-1",),
            "confidence": Decimal("0.7"),
        }
        data.update(overrides)
        return EquityImpactAssessment(**data)


if __name__ == "__main__":
    unittest.main()
