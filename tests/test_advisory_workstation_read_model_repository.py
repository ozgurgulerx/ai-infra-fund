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
                ResultSet([advisory_update_row()], ADVISORY_UPDATE_COLUMNS),
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
        self.assertEqual(7, len(connection.cursor_instance.executions))

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
                ResultSet([advisory_update_row()], ADVISORY_UPDATE_COLUMNS),
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
                ResultSet([advisory_update_row()], ADVISORY_UPDATE_COLUMNS),
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

    def test_segment_map_returns_segments_with_linked_events_and_risk_context(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        connection = FakeConnection(
            [
                ResultSet([segment_impact_row()], SEGMENT_COLUMNS),
                ResultSet([market_event_row()], MARKET_EVENT_COLUMNS),
                ResultSet([risk_regime_row()], RISK_COLUMNS),
            ]
        )

        payload = AdvisoryWorkstationRepository(connection).get_latest_segment_map()

        self.assertEqual("available", payload["status"])
        self.assertEqual("advisory_only", payload["advisory_label"])
        self.assertEqual("segment-1", payload["segment_impacts"][0]["segment_id"])
        self.assertEqual("market-event-1", payload["market_events"][0]["event_id"])
        self.assertEqual("risk-1", payload["risk_regime_updates"][0]["regime_id"])
        executions = connection.cursor_instance.executions
        self.assertIn("FROM analyst.segment_impacts", executions[0][0])
        self.assertIn("WHERE event_id = ANY", executions[1][0])
        self.assertEqual((["market-event-1"], ["market-event-1"], 1), executions[1][1])
        self.assertIn("FROM analyst.risk_regime_updates", executions[2][0])
        self.assertEqual((["market-event-1"], 20), executions[2][1])

    def test_ticker_workbench_returns_full_ticker_context(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        connection = FakeConnection(
            [
                ResultSet([source_signal_row()], SOURCE_SIGNAL_COLUMNS),
                ResultSet([market_event_row()], MARKET_EVENT_COLUMNS),
                ResultSet([segment_impact_row()], SEGMENT_COLUMNS),
                ResultSet([equity_assessment_row()], ASSESSMENT_COLUMNS),
                ResultSet([valuation_row()], VALUATION_COLUMNS),
                ResultSet([trading_advisory_row()], ADVISORY_COLUMNS),
                ResultSet([advisory_update_row()], ADVISORY_UPDATE_COLUMNS),
                ResultSet([trade_plan_row()], TRADE_PLAN_COLUMNS),
                ResultSet([risk_regime_row()], RISK_COLUMNS),
                ResultSet([llm_note_row()], LLM_NOTE_COLUMNS),
            ]
        )

        payload = AdvisoryWorkstationRepository(connection).get_ticker_workbench("nvda")

        self.assertEqual("available", payload["status"])
        self.assertEqual("NVDA", payload["ticker"])
        self.assertEqual("segment-1", payload["segment_impacts"][0]["segment_id"])
        self.assertEqual("trade-plan-1", payload["trade_plans"][0]["trade_plan_id"])
        self.assertTrue(payload["trade_plans"][0]["manual_journal_only"])
        self.assertEqual("risk-1", payload["risk_regime_updates"][0]["regime_id"])
        self.assertEqual("llm-note-1", payload["llm_analyst_notes"][0]["note_id"])
        self.assertEqual(10, len(connection.cursor_instance.executions))

    def test_ticker_workbench_returns_theme_grouped_rating_news_notes_and_related_tickers(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        connection = FakeConnection(
            [
                ResultSet([source_signal_row()], SOURCE_SIGNAL_COLUMNS),
                ResultSet([market_event_row()], MARKET_EVENT_COLUMNS),
                ResultSet([segment_impact_row()], SEGMENT_COLUMNS),
                ResultSet([equity_assessment_row()], ASSESSMENT_COLUMNS),
                ResultSet([valuation_row()], VALUATION_COLUMNS),
                ResultSet([trading_advisory_row()], ADVISORY_COLUMNS),
                ResultSet([advisory_update_row()], ADVISORY_UPDATE_COLUMNS),
                ResultSet([trade_plan_row()], TRADE_PLAN_COLUMNS),
                ResultSet([risk_regime_row()], RISK_COLUMNS),
                ResultSet([llm_note_row()], LLM_NOTE_COLUMNS),
            ]
        )

        payload = AdvisoryWorkstationRepository(connection).get_ticker_workbench("nvda")

        groups = payload["theme_groups"]
        self.assertGreaterEqual(len(groups), 1)
        first = groups[0]
        self.assertEqual("NVDA", first["ticker"])
        self.assertEqual("advisory_only", first["advisory_label"])
        self.assertIn("theme_id", first)
        self.assertIn("theme_label", first)
        self.assertEqual("watch", first["advisory_stance"]["action"])
        self.assertEqual("advisory-1", first["advisory_stance"]["source_advisory_id"])
        self.assertEqual(["evidence-1"], first["advisory_stance"]["evidence_ids"])
        self.assertEqual(["model-run-1"], first["advisory_stance"]["model_run_ids"])
        self.assertEqual(["source_signal_bundle_linked"], first["advisory_stance"]["deterministic_check_ids"])
        self.assertEqual("source-signal-1", first["source_signals"][0]["signal_id"])
        self.assertEqual("market-event-1", first["market_events"][0]["event_id"])
        self.assertEqual("assessment-1", first["impact_assessments"][0]["assessment_id"])
        self.assertEqual("llm-note-1", first["llm_notes"][0]["note_id"])
        self.assertEqual("trade-plan-1", first["trade_plan_notes"][0]["trade_plan_id"])
        self.assertEqual("TSM", first["related_tickers"][0]["ticker"])
        self.assertIn("relationship_type", first["related_tickers"][0])
        self.assertIn("reason", first["related_tickers"][0])
        self.assertIn("valuation", first["risk_flags"])
        self.assertEqual("Invalidate if capex evidence reverses.", first["invalidation"])
        self.assertTrue(first["next_watch_items"])
        self.assertEqual(["evidence-1"], first["evidence_ids"])

    def test_ticker_workbench_theme_rating_falls_back_to_unrated_without_advisory(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        connection = FakeConnection(
            [
                ResultSet([source_signal_row()], SOURCE_SIGNAL_COLUMNS),
                ResultSet([market_event_row()], MARKET_EVENT_COLUMNS),
                ResultSet([segment_impact_row()], SEGMENT_COLUMNS),
                ResultSet([], ASSESSMENT_COLUMNS),
                ResultSet([], VALUATION_COLUMNS),
                ResultSet([], ADVISORY_COLUMNS),
                ResultSet([], ADVISORY_UPDATE_COLUMNS),
                ResultSet([], TRADE_PLAN_COLUMNS),
                ResultSet([risk_regime_row()], RISK_COLUMNS),
                ResultSet([], LLM_NOTE_COLUMNS),
            ]
        )

        payload = AdvisoryWorkstationRepository(connection).get_ticker_workbench("nvda")

        self.assertEqual("unrated", payload["theme_groups"][0]["advisory_stance"]["action"])
        self.assertEqual("neutral", payload["theme_groups"][0]["advisory_stance"]["tone"])
        self.assertIsNone(payload["theme_groups"][0]["advisory_stance"]["source_advisory_id"])

    def test_latest_advisory_updates_and_watchlist_ratings_return_delta_rows(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        connection = FakeConnection(
            [
                ResultSet([advisory_update_row()], ADVISORY_UPDATE_COLUMNS),
                ResultSet([trading_advisory_row()], ADVISORY_COLUMNS),
                ResultSet([advisory_update_row()], ADVISORY_UPDATE_COLUMNS),
                ResultSet([equity_assessment_row()], ASSESSMENT_COLUMNS),
            ]
        )
        repository = AdvisoryWorkstationRepository(connection)

        updates = repository.get_latest_advisory_updates()
        ratings = repository.get_latest_watchlist_ratings()

        self.assertEqual("available", updates["status"])
        self.assertEqual("advisory-update-1", updates["items"][0]["update_id"])
        self.assertEqual("NVDA", ratings["items"][0]["ticker"])
        self.assertEqual("accumulate", ratings["items"][0]["current_label"])
        self.assertEqual("improved", ratings["items"][0]["outlook_delta"])

    def test_latest_portfolio_exposure_returns_deterministic_snapshot(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        connection = FakeConnection(
            ResultSet([portfolio_exposure_row()], PORTFOLIO_EXPOSURE_COLUMNS)
        )

        payload = AdvisoryWorkstationRepository(connection).get_latest_portfolio_exposure()

        self.assertEqual("available", payload["status"])
        self.assertEqual("advisory_only", payload["advisory_label"])
        self.assertEqual("portfolio-snapshot-1", payload["snapshot"]["snapshot_id"])
        self.assertEqual("NVDA", payload["snapshot"]["positions"][0]["ticker"])
        self.assertEqual(["correlation-1"], payload["snapshot"]["correlation_exposure_ids"])
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM analyst.portfolio_exposure_snapshots", statement)
        self.assertEqual((1,), params)

    def test_market_events_for_ticker_filters_by_ticker_and_returns_freshness_metadata(self) -> None:
        from ai_infra_fund_api.repositories.advisory_workstation import (
            AdvisoryWorkstationRepository,
        )

        connection = FakeConnection(ResultSet([market_event_row()], MARKET_EVENT_COLUMNS))

        payload = AdvisoryWorkstationRepository(connection).get_market_events_for_ticker(
            "nvda"
        )

        self.assertEqual("available", payload["status"])
        self.assertEqual("NVDA", payload["ticker"])
        self.assertEqual("advisory_only", payload["advisory_label"])
        self.assertEqual("market-event-1", payload["items"][0]["event_id"])
        self.assertEqual(["evidence-1"], payload["items"][0]["source_evidence_ids"])
        self.assertEqual(NOW.isoformat(), payload["freshness"]["latest_available_at"])
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("WHERE tickers @> ARRAY[UPPER(%s)]", statement)
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
    "severity",
    "confidence",
    "linked_event_ids",
    "affected_segments",
    "affected_tickers",
    "evidence_ids",
    "summary",
    "portfolio_monitoring_note",
    "relief_condition",
    "invalidation_condition",
    "as_of",
    "available_at",
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

ADVISORY_UPDATE_COLUMNS = (
    "update_id",
    "ticker",
    "company",
    "previous_advisory_id",
    "new_advisory_id",
    "previous_label",
    "current_label",
    "what_changed",
    "update_type",
    "thesis_change_direction",
    "risk_change_direction",
    "valuation_change_direction",
    "confidence_change",
    "time_horizon",
    "evidence_ids",
    "model_run_ids",
    "deterministic_check_ids",
    "advisory_label",
    "payload_json",
    "created_at",
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

TRADE_PLAN_COLUMNS = (
    "trade_plan_id",
    "ticker",
    "company",
    "status",
    "advisory_action",
    "linked_event_ids",
    "linked_signal_bundle_id",
    "linked_recommendation_artifact_id",
    "entry_exit_levels_id",
    "price_target_scenario_id",
    "target_weights_id",
    "deterministic_check_ids",
    "readiness",
    "blocking_reasons",
    "manual_journal_only",
    "evidence_ids",
    "linked_advisory_id",
    "last_reviewed_at",
    "payload_json",
)

PORTFOLIO_EXPOSURE_COLUMNS = (
    "snapshot_id",
    "as_of",
    "currency",
    "source",
    "advisory_label",
    "total_market_value",
    "cash_placeholder",
    "gross_equity_exposure",
    "position_count",
    "positions_json",
    "correlation_exposure_ids",
    "pnl_summary_id",
    "target_weights_id",
    "concentration_flags",
    "stale_price_flags",
    "payload_json",
)

LLM_NOTE_COLUMNS = (
    "note_id",
    "model_run_id",
    "scope",
    "allowed_role",
    "reviewed_object_ids",
    "evidence_ids",
    "note",
    "deterministic_fields_not_modified",
    "created_at",
    "review_status",
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
        "medium",
        "0.74",
        ["market-event-1"],
        ["power_grid"],
        ["NVDA"],
        ["evidence-1"],
        "Power is constrained.",
        "Watch energized capacity.",
        "Confirmed energized capacity.",
        "Power bottleneck evidence reverses.",
        NOW,
        NOW,
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


def advisory_update_row() -> tuple[object, ...]:
    return (
        "advisory-update-1",
        "NVDA",
        "NVIDIA",
        "advisory-0",
        "advisory-1",
        "watch",
        "accumulate",
        "Outlook improved after capex evidence.",
        "advisory_delta",
        "improved",
        "unchanged",
        "unchanged",
        "increased",
        "6_to_18_months",
        ["evidence-1"],
        ["model-run-1"],
        ["readiness-check-1"],
        "advisory_only",
        {"source_url": "https://example.com/source", "title": "Capex source"},
        NOW,
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


def trade_plan_row() -> tuple[object, ...]:
    return (
        "trade-plan-1",
        "NVDA",
        "NVIDIA",
        "active",
        "watch",
        ["market-event-1"],
        "signal-bundle-1",
        "recommendation-1",
        "levels-1",
        "scenario-1",
        "target-1",
        ["readiness-check-1"],
        "ready",
        [],
        True,
        ["evidence-1"],
        "advisory-1",
        NOW,
        {"source": "fixture"},
    )


def portfolio_exposure_row() -> tuple[object, ...]:
    return (
        "portfolio-snapshot-1",
        NOW,
        "USD",
        "manual_journal",
        "advisory_only",
        "50000",
        "5000",
        "0.90",
        1,
        [
            {
                "ticker": "NVDA",
                "company": "NVIDIA",
                "segment_tags": ["accelerators"],
                "market_value": "45000",
                "portfolio_weight": "0.90",
                "cost_basis": "42000",
                "unrealized_pnl": "3000",
                "open_trade_plan_id": "trade-plan-1",
                "risk_flags": ["valuation"],
                "last_price_timestamp": NOW.isoformat(),
            }
        ],
        ["correlation-1"],
        "pnl-1",
        "target-1",
        ["single_name_concentration"],
        [],
        {"source": "fixture"},
    )


def llm_note_row() -> tuple[object, ...]:
    return (
        "llm-note-1",
        "model-run-1",
        "ticker_workbench",
        "equity_thesis_analyst",
        ["assessment-1", "trade-plan-1"],
        ["evidence-1"],
        "Evidence supports watch status but deterministic readiness remains authoritative.",
        ["entry_exit_levels", "pnl", "portfolio_weights"],
        NOW,
        "approved",
        {"source": "fixture"},
    )


if __name__ == "__main__":
    unittest.main()
