from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "services" / "api" / "src"
sys.path.insert(0, str(API_SRC))


NOW = datetime(2026, 5, 16, 8, 0, tzinfo=timezone.utc)


class AdvisoryWorkstationReadModelRepositoryTests(unittest.TestCase):
    def test_latest_analyst_brief_returns_linked_fixture_backed_payload(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        connection = FakeConnection(
            [
                ResultSet([brief_row()], BRIEF_COLUMNS),
                ResultSet([market_event_row()], MARKET_EVENT_COLUMNS),
                ResultSet([segment_impact_row()], SEGMENT_COLUMNS),
                ResultSet([equity_assessment_row()], ASSESSMENT_COLUMNS),
                ResultSet([risk_regime_row()], RISK_COLUMNS),
                ResultSet([trading_advisory_row()], ADVISORY_COLUMNS),
            ]
        )

        payload = AdvisoryWorkstationRepository(connection).get_latest_analyst_brief()

        self.assertEqual("available", payload["status"])
        self.assertEqual("advisory_only", payload["advisory_label"])
        self.assertEqual("brief-1", payload["brief"]["brief_id"])
        self.assertEqual("market-event-1", payload["market_events"][0]["event_id"])
        self.assertEqual("segment-1", payload["segment_impacts"][0]["segment_id"])
        self.assertEqual("assessment-1", payload["equity_impact_assessments"][0]["assessment_id"])
        self.assertEqual("risk-1", payload["risk_regime_updates"][0]["regime_id"])
        self.assertEqual("advisory-1", payload["trading_advisories"][0]["advisory_id"])
        self.assertEqual(6, len(connection.cursor_instance.executions))

    def test_latest_analyst_brief_fetches_only_brief_linked_objects(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        connection = FakeConnection(
            [
                ResultSet([brief_row()], BRIEF_COLUMNS),
                ResultSet([market_event_row()], MARKET_EVENT_COLUMNS),
                ResultSet([segment_impact_row()], SEGMENT_COLUMNS),
                ResultSet([equity_assessment_row()], ASSESSMENT_COLUMNS),
                ResultSet([risk_regime_row()], RISK_COLUMNS),
                ResultSet([trading_advisory_row()], ADVISORY_COLUMNS),
            ]
        )

        AdvisoryWorkstationRepository(connection).get_latest_analyst_brief()

        executions = connection.cursor_instance.executions
        self.assertIn("WHERE event_id = ANY", executions[1][0])
        self.assertEqual((["market-event-1"], ["market-event-1"], 1), executions[1][1])
        self.assertIn("WHERE segment_id = ANY", executions[2][0])
        self.assertEqual((["segment-1"], ["segment-1"], 1), executions[2][1])
        self.assertIn("WHERE linked_event_ids &&", executions[3][0])
        self.assertEqual((["market-event-1"], 50), executions[3][1])
        self.assertIn("WHERE linked_event_ids &&", executions[4][0])
        self.assertEqual((["market-event-1"], 10), executions[4][1])
        self.assertIn("WHERE advisory_id = ANY", executions[5][0])
        self.assertEqual((["advisory-1"], ["advisory-1"], 1), executions[5][1])

    def test_ticker_summary_filters_by_ticker_and_preserves_trace_links(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        connection = FakeConnection(
            [
                ResultSet([source_signal_row()], SOURCE_SIGNAL_COLUMNS),
                ResultSet([market_event_row()], MARKET_EVENT_COLUMNS),
                ResultSet([equity_assessment_row()], ASSESSMENT_COLUMNS),
                ResultSet([valuation_row()], VALUATION_COLUMNS),
                ResultSet([trading_advisory_row()], ADVISORY_COLUMNS),
            ]
        )

        payload = AdvisoryWorkstationRepository(connection).get_ticker_analyst_summary(
            "nvda"
        )

        self.assertEqual("available", payload["status"])
        self.assertEqual("NVDA", payload["ticker"])
        self.assertEqual(["evidence-1"], payload["trading_advisories"][0]["evidence_ids"])
        for statement, params in connection.cursor_instance.executions:
            self.assertIn("UPPER(%s)", statement)
            self.assertEqual(("NVDA", 10), params)

    def test_empty_latest_brief_returns_empty_state(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        connection = FakeConnection(ResultSet([], BRIEF_COLUMNS))

        payload = AdvisoryWorkstationRepository(connection).get_latest_analyst_brief()

        self.assertEqual(
            {
                "status": "empty",
                "advisory_label": "advisory_only",
                "detail": "No API-backed analyst brief has been produced.",
            },
            payload,
        )


SOURCE_SIGNAL_COLUMNS = (
    "signal_id",
    "source_type",
    "signal_category",
    "title",
    "observed_at",
    "available_at",
    "tickers",
    "themes",
    "evidence_ids",
    "derived_market_event_ids",
    "confidence",
    "review_status",
    "payload_json",
)

MARKET_EVENT_COLUMNS = (
    "event_id",
    "event_type",
    "source_signal_ids",
    "evidence_ids",
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
    "payload_json",
)

SEGMENT_COLUMNS = (
    "segment_id",
    "segment_name",
    "primary_tickers",
    "second_order_tickers",
    "linked_event_ids",
    "impact_direction",
    "impact_summary",
    "evidence_ids",
    "payload_json",
)

ASSESSMENT_COLUMNS = (
    "assessment_id",
    "ticker",
    "company",
    "linked_event_ids",
    "assessment",
    "watch_items",
    "advisory_implication",
    "risk_flags",
    "invalidation",
    "evidence_ids",
    "payload_json",
)

VALUATION_COLUMNS = (
    "valuation_context_id",
    "ticker",
    "valuation_state",
    "forward_pe",
    "ev_sales",
    "assumptions",
    "risk_flags",
    "evidence_ids",
    "payload_json",
)

RISK_COLUMNS = (
    "regime_id",
    "risk_type",
    "status",
    "linked_event_ids",
    "evidence_ids",
    "summary",
    "portfolio_monitoring_note",
    "payload_json",
)

ADVISORY_COLUMNS = (
    "advisory_id",
    "recommendation_artifact_id",
    "ticker",
    "advisory_label",
    "analyst_action",
    "advisory_summary",
    "evidence_ids",
    "model_run_ids",
    "signal_bundle_id",
    "target_weights_id",
    "deterministic_checks",
    "linked_trade_plan_id",
    "payload_json",
)

BRIEF_COLUMNS = (
    "brief_id",
    "as_of",
    "title",
    "advisory_label",
    "executive_summary",
    "market_event_ids",
    "segment_impact_ids",
    "trading_advisory_ids",
    "model_run_ids",
    "payload_json",
)


class ResultSet:
    def __init__(self, rows: list[tuple[object, ...]], columns: tuple[str, ...]) -> None:
        self.rows = rows
        self.columns = columns


class FakeCursor:
    def __init__(self, result_sets: list[ResultSet]) -> None:
        self._result_sets = result_sets
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.description: tuple[tuple[str], ...] = ()
        self.rows: list[tuple[object, ...]] = []

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params if params is not None else ()))
        result_set = self._result_sets[min(len(self.executions) - 1, len(self._result_sets) - 1)]
        self.rows = result_set.rows
        self.description = tuple((column,) for column in result_set.columns)

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self, result_set: ResultSet | list[ResultSet]) -> None:
        result_sets = result_set if isinstance(result_set, list) else [result_set]
        self.cursor_instance = FakeCursor(result_sets)

    def cursor(self) -> FakeCursor:
        return self.cursor_instance


def source_signal_row() -> tuple[object, ...]:
    return (
        "source-signal-1",
        "earnings_transcript",
        "hyperscaler_capex",
        "Cloud capex changed",
        NOW,
        NOW,
        ["NVDA"],
        ["hyperscaler capex"],
        ["evidence-1"],
        ["market-event-1"],
        "high",
        "reviewed",
        {"source": "fixture"},
    )


def market_event_row() -> tuple[object, ...]:
    return (
        "market-event-1",
        "capex_signal",
        ["source-signal-1"],
        ["evidence-1"],
        ["NVDA"],
        ["NVIDIA"],
        ["accelerator demand"],
        "Cloud capex moved higher.",
        "Supports accelerator demand.",
        "positive",
        "6_to_18_months",
        "high",
        NOW,
        NOW,
        "sha256:fixture",
        "model-run-1",
        "reviewed",
        {"source": "fixture"},
    )


def segment_impact_row() -> tuple[object, ...]:
    return (
        "segment-1",
        "AI Accelerators",
        ["NVDA"],
        ["TSM"],
        ["market-event-1"],
        "positive",
        "Accelerator demand improves.",
        ["evidence-1"],
        {"source": "fixture"},
    )


def equity_assessment_row() -> tuple[object, ...]:
    return (
        "assessment-1",
        "NVDA",
        "NVIDIA",
        ["market-event-1"],
        "Demand improves.",
        ["HBM allocation"],
        "watch",
        ["valuation"],
        "Invalidate if capex evidence reverses.",
        ["evidence-1"],
        {"source": "fixture"},
    )


def valuation_row() -> tuple[object, ...]:
    return (
        "valuation-1",
        "NVDA",
        "premium_supported",
        "34.0",
        "16.5",
        ["AI demand remains high"],
        ["valuation"],
        ["evidence-1"],
        {"source": "fixture"},
    )


def risk_regime_row() -> tuple[object, ...]:
    return (
        "risk-1",
        "power_capacity",
        "elevated",
        ["market-event-1"],
        ["evidence-1"],
        "Power is constrained.",
        "Watch energized capacity.",
        {"source": "fixture"},
    )


def trading_advisory_row() -> tuple[object, ...]:
    return (
        "advisory-1",
        "recommendation-1",
        "NVDA",
        "advisory_only",
        "watch",
        "Demand is strong but risk remains.",
        ["evidence-1"],
        ["model-run-1"],
        "signal-1",
        "target-1",
        ["source_signal_bundle_linked"],
        "trade-plan-1",
        {"source": "fixture"},
    )


def brief_row() -> tuple[object, ...]:
    return (
        "brief-1",
        NOW,
        "AI Infrastructure Brief",
        "advisory_only",
        "Catalysts moved.",
        ["market-event-1"],
        ["segment-1"],
        ["advisory-1"],
        ["model-run-1"],
        {"source": "fixture"},
    )


if __name__ == "__main__":
    unittest.main()
