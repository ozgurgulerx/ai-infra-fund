from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import stat
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))


NOW = datetime(2026, 5, 16, 8, 30, tzinfo=timezone.utc)


class DailyAiInfraBriefRunTests(unittest.TestCase):
    def test_run_persists_readiness_gated_advisory_brief_and_artifact(self) -> None:
        from ai_infra_fund_worker.daily_ai_infra_brief_run import (
            run_daily_ai_infra_brief,
        )

        connection = FakeConnection()

        result = run_daily_ai_infra_brief(connection, run_at=NOW)

        self.assertEqual("succeeded", result["status"])
        self.assertEqual(0, result["exit_code"])
        self.assertEqual("daily_ai_infra_brief", result["run_type"])
        self.assertEqual("advisory_only", result["advisory_label"])
        self.assertEqual(1, result["published_advisory_count"])
        self.assertEqual(0, result["suppressed_candidate_count"])
        self.assertEqual(1, connection.commit_count)

        statements = "\n".join(
            statement for statement, _params in connection.cursor_instance.executions
        )
        for table_name in (
            "analyst.source_signals",
            "analyst.market_events",
            "analyst.segment_impacts",
            "analyst.equity_impact_assessments",
            "analyst.valuation_contexts",
            "analyst.risk_regime_updates",
            "analyst.trade_plans",
            "analyst.portfolio_exposure_snapshots",
            "analyst.outcome_journal_entries",
            "evidence.evidence_items",
            "analyst.trading_advisories",
            "analyst.analyst_briefs",
            "audit.run_artifacts",
        ):
            self.assertIn(table_name, statements)

        advisory_params = connection.cursor_instance.single_insert(
            "INSERT INTO analyst.trading_advisories"
        )
        self.assertEqual(result["published_advisory_ids"][0], advisory_params[0])
        self.assertEqual("NVDA", advisory_params[2])
        self.assertEqual("advisory_only", advisory_params[3])
        self.assertEqual("accumulate", advisory_params[4])
        self.assertIn("evidence-1", advisory_params[6])
        self.assertIn("model-run-1", advisory_params[7])
        self.assertIn("evidence_present", advisory_params[10])
        self.assertIn("source_fresh", advisory_params[10])
        self.assertIn("data_class_allowed", advisory_params[10])
        self.assertEqual("trade-plan-1", advisory_params[11])
        advisory_payload = json.loads(advisory_params[12])
        self.assertEqual(["market-event-1"], advisory_payload["market_event_ids"])
        self.assertEqual(["segment-1"], advisory_payload["segment_impact_ids"])
        self.assertEqual(["risk-1"], advisory_payload["risk_regime_ids"])
        self.assertEqual("valuation-1", advisory_payload["valuation_context_id"])
        self.assertTrue(advisory_payload["readiness"]["publishable"])

        brief_params = connection.cursor_instance.single_insert(
            "INSERT INTO analyst.analyst_briefs"
        )
        self.assertEqual(result["brief_id"], brief_params[0])
        self.assertEqual(NOW, brief_params[1])
        self.assertEqual("AI Infrastructure Daily Brief", brief_params[2])
        self.assertEqual("advisory_only", brief_params[3])
        self.assertEqual(["market-event-1"], brief_params[5])
        self.assertEqual(["segment-1"], brief_params[6])
        self.assertEqual(result["published_advisory_ids"], brief_params[7])
        self.assertEqual(["model-run-1"], brief_params[8])
        brief_payload = json.loads(brief_params[9])
        self.assertEqual("portfolio-snapshot-1", brief_payload["portfolio_snapshot_id"])
        self.assertEqual(["trade-plan-1"], brief_payload["open_trade_plan_ids"])
        self.assertEqual(1, brief_payload["journal_state"]["outcome_count"])
        self.assertEqual([], brief_payload["suppressed_candidates"])
        self.assertEqual("advisory_only", brief_payload["advisory_label"])

        artifact_params = connection.cursor_instance.single_insert(
            "INSERT INTO audit.run_artifacts"
        )
        self.assertEqual(result["run_id"], artifact_params[0])
        self.assertEqual("daily_ai_infra_brief", artifact_params[1])
        self.assertEqual(result["inputs_hash"], artifact_params[4])
        self.assertEqual(result["output_hash"], artifact_params[5])
        self.assertIn(f"brief_id={result['brief_id']}", artifact_params[6])
        self.assertEqual("succeeded", artifact_params[7])
        self.assertIsNone(artifact_params[8])

    def test_run_suppresses_advisory_when_evidence_is_missing(self) -> None:
        from ai_infra_fund_worker.daily_ai_infra_brief_run import (
            run_daily_ai_infra_brief,
        )

        connection = FakeConnection(evidence_rows=[])

        result = run_daily_ai_infra_brief(connection, run_at=NOW)

        self.assertEqual("succeeded", result["status"])
        self.assertEqual(0, result["exit_code"])
        self.assertEqual(0, result["published_advisory_count"])
        self.assertEqual(1, result["suppressed_candidate_count"])
        self.assertEqual(1, connection.commit_count)
        self.assertFalse(
            connection.cursor_instance.has_insert("INSERT INTO analyst.trading_advisories")
        )

        brief_params = connection.cursor_instance.single_insert(
            "INSERT INTO analyst.analyst_briefs"
        )
        self.assertEqual([], brief_params[7])
        brief_payload = json.loads(brief_params[9])
        self.assertEqual(
            ["missing_evidence"],
            brief_payload["suppressed_candidates"][0]["blocking_reasons"],
        )
        self.assertEqual("advisory_only", brief_payload["advisory_label"])

        artifact_params = connection.cursor_instance.single_insert(
            "INSERT INTO audit.run_artifacts"
        )
        self.assertEqual("succeeded", artifact_params[7])
        self.assertIsNone(artifact_params[8])

    def test_run_persists_shadow_drafts_and_model_run_in_stub_mode(self) -> None:
        from ai_infra_fund_worker.daily_ai_infra_brief_run import (
            run_daily_ai_infra_brief,
        )

        connection = FakeConnection()

        result = run_daily_ai_infra_brief(
            connection,
            run_at=NOW,
            shadow_model_client=StubShadowAnalystModelClient(_valid_shadow_response()),
        )

        self.assertEqual("review_required", result["shadow_analyst_status"])
        self.assertEqual(6, result["shadow_draft_count"])
        self.assertEqual(1, result["shadow_model_run_count"])
        self.assertEqual(1, connection.commit_count)

        model_run_params = connection.cursor_instance.single_insert(
            "INSERT INTO audit.model_runs"
        )
        self.assertEqual("evidence_summary", model_run_params[1])
        self.assertTrue(model_run_params[12])
        self.assertEqual("success", model_run_params[15])
        self.assertIn("public_evidence", model_run_params[14])

        draft_rows = connection.cursor_instance.insert_params(
            "INSERT INTO analyst.shadow_analyst_drafts"
        )
        self.assertEqual(6, len(draft_rows))
        first_draft = draft_rows[0]
        self.assertEqual("SegmentImpactDraft", first_draft[1])
        self.assertEqual("daily_brief", first_draft[2])
        self.assertIsNone(first_draft[3])
        self.assertEqual(model_run_params[0], first_draft[4])
        self.assertEqual("review_required", first_draft[5])
        self.assertEqual(["evidence-1"], first_draft[7])
        self.assertEqual([], first_draft[8])
        payload = json.loads(first_draft[6])
        self.assertFalse(payload["can_publish_directly"])

        brief_params = connection.cursor_instance.single_insert(
            "INSERT INTO analyst.analyst_briefs"
        )
        brief_payload = json.loads(brief_params[9])
        self.assertEqual("review_required", brief_payload["shadow_analyst"]["status"])
        self.assertEqual(6, brief_payload["shadow_analyst"]["draft_count"])
        self.assertNotIn("Review-required segment draft.", json.dumps(brief_payload))

    def test_run_persists_invalid_shadow_draft_as_rejected(self) -> None:
        from ai_infra_fund_worker.daily_ai_infra_brief_run import (
            run_daily_ai_infra_brief,
        )

        invalid = _valid_shadow_response()
        invalid["trading_advisories"][0]["payload"]["target_weights"] = {"NVDA": "0.4"}
        invalid["trading_advisories"][0]["material_claims"] = (
            {"claim": "Model tries to own target weights.", "evidence_ids": ()},
        )

        connection = FakeConnection()
        result = run_daily_ai_infra_brief(
            connection,
            run_at=NOW,
            shadow_model_client=StubShadowAnalystModelClient(invalid),
        )

        self.assertEqual("rejected", result["shadow_analyst_status"])
        model_run_params = connection.cursor_instance.single_insert(
            "INSERT INTO audit.model_runs"
        )
        self.assertFalse(model_run_params[12])
        self.assertEqual("failure", model_run_params[15])
        draft_rows = connection.cursor_instance.insert_params(
            "INSERT INTO analyst.shadow_analyst_drafts"
        )
        rejected = [row for row in draft_rows if row[5] == "rejected"]
        self.assertTrue(rejected)
        self.assertTrue(rejected[0][8])
        self.assertIn("target_weights", " ".join(rejected[0][8]))

    def test_run_persists_shadow_fallback_when_model_client_unavailable(self) -> None:
        from ai_infra_fund_worker.daily_ai_infra_brief_run import (
            run_daily_ai_infra_brief,
        )

        connection = FakeConnection()
        result = run_daily_ai_infra_brief(connection, run_at=NOW)

        self.assertEqual("fallback", result["shadow_analyst_status"])
        self.assertEqual(1, result["shadow_draft_count"])
        model_run_params = connection.cursor_instance.single_insert(
            "INSERT INTO audit.model_runs"
        )
        self.assertFalse(model_run_params[12])
        self.assertEqual("failure", model_run_params[15])
        self.assertIn("unavailable", model_run_params[16])

        fallback_params = connection.cursor_instance.single_insert(
            "INSERT INTO analyst.shadow_analyst_drafts"
        )
        self.assertEqual("ShadowAnalystFallback", fallback_params[1])
        self.assertEqual("fallback", fallback_params[5])
        self.assertEqual(model_run_params[0], fallback_params[4])
        self.assertEqual(["evidence-1"], fallback_params[7])
        self.assertTrue(fallback_params[8])

    def test_run_denies_private_research_shadow_path_without_model_call(self) -> None:
        from ai_infra_fund_worker.daily_ai_infra_brief_run import (
            run_daily_ai_infra_brief,
        )

        client = StubShadowAnalystModelClient(_valid_shadow_response())
        connection = FakeConnection(evidence_rows=[private_evidence_row()])

        result = run_daily_ai_infra_brief(
            connection,
            run_at=NOW,
            shadow_model_client=client,
        )

        self.assertEqual("denied", result["shadow_analyst_status"])
        self.assertEqual([], client.calls)
        self.assertEqual(1, result["shadow_model_run_count"])

        model_run_params = connection.cursor_instance.single_insert(
            "INSERT INTO audit.model_runs"
        )
        self.assertFalse(model_run_params[12])
        self.assertEqual("denied", model_run_params[15])
        self.assertIn("private_research", model_run_params[16])

        denied_params = connection.cursor_instance.single_insert(
            "INSERT INTO analyst.shadow_analyst_drafts"
        )
        self.assertEqual("ShadowAnalystDenied", denied_params[1])
        self.assertEqual("denied", denied_params[5])
        self.assertEqual(model_run_params[0], denied_params[4])
        self.assertEqual(["evidence-1"], denied_params[7])
        self.assertTrue(denied_params[8])

    def test_run_script_exists_and_invokes_daily_worker_module(self) -> None:
        script = ROOT / "scripts" / "run_daily_ai_infra_brief_once.sh"

        self.assertTrue(script.is_file())
        self.assertTrue(script.stat().st_mode & stat.S_IXUSR)
        text = script.read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", text)
        self.assertIn("docker compose build migrate worker", text)
        self.assertIn("python -m ai_infra_fund_worker.daily_ai_infra_brief_run", text)
        self.assertNotIn("curl", text)

    def test_daily_worker_stays_local_deterministic_and_advisory_only(self) -> None:
        module = (
            ROOT
            / "services"
            / "worker"
            / "src"
            / "ai_infra_fund_worker"
            / "daily_ai_infra_brief_run.py"
        )
        text = module.read_text(encoding="utf-8").lower()

        forbidden = [
            "openai",
            "anthropic",
            "requests",
            "httpx",
            "marketdata",
            "place_order",
            "submit_order",
            "broker_client",
            "order_execution",
            "ai_infra_fund_api",
        ]
        offenders = [word for word in forbidden if word in text]
        self.assertEqual([], offenders)


SOURCE_SIGNAL_COLUMNS = (
    "signal_id",
    "source_type",
    "signal_category",
    "title",
    "available_at",
    "tickers",
    "themes",
    "evidence_ids",
    "derived_market_event_ids",
    "confidence",
    "review_status",
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
    "available_at",
    "extracted_by_model_run_id",
    "review_status",
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
)

VALUATION_COLUMNS = (
    "valuation_context_id",
    "ticker",
    "valuation_state",
    "assumptions",
    "risk_flags",
    "evidence_ids",
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
    "available_at",
)

TRADE_PLAN_COLUMNS = (
    "trade_plan_id",
    "ticker",
    "status",
    "advisory_action",
    "linked_event_ids",
    "readiness",
    "blocking_reasons",
    "manual_journal_only",
    "evidence_ids",
    "linked_advisory_id",
    "last_reviewed_at",
)

PORTFOLIO_COLUMNS = (
    "snapshot_id",
    "as_of",
    "advisory_label",
    "position_count",
    "positions_json",
    "concentration_flags",
    "stale_price_flags",
)

OUTCOME_COLUMNS = (
    "outcome_id",
    "manual_journal_entry_id",
    "advisory_id",
    "ticker",
    "market_event_ids",
    "evidence_ids",
    "outcome_label",
    "reviewed_at",
    "advisory_label",
)

EVIDENCE_COLUMNS = (
    "evidence_id",
    "data_class",
    "ingested_at",
    "published_at",
    "content_hash",
)


class FakeCursor:
    def __init__(self, evidence_rows: list[tuple[object, ...]]) -> None:
        self.evidence_rows = evidence_rows
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.description: tuple[tuple[str], ...] = ()
        self.rows: list[tuple[object, ...]] = []

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        normalized = params if params is not None else ()
        self.executions.append((statement, normalized))
        if statement.lstrip().upper().startswith("INSERT"):
            self.rows = []
            self.description = ()
            return
        self.rows, columns = self._select_result(statement)
        self.description = tuple((column,) for column in columns)

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def single_insert(self, marker: str) -> tuple[object, ...]:
        matches = self.insert_params(marker)
        if len(matches) != 1:
            raise AssertionError(f"expected exactly one insert for {marker}, got {len(matches)}")
        return matches[0]

    def insert_params(self, marker: str) -> list[tuple[object, ...]]:
        return [params for statement, params in self.executions if marker in statement]

    def has_insert(self, marker: str) -> bool:
        return any(marker in statement for statement, _params in self.executions)

    def _select_result(
        self, statement: str
    ) -> tuple[list[tuple[object, ...]], tuple[str, ...]]:
        if "FROM analyst.source_signals" in statement:
            return [source_signal_row()], SOURCE_SIGNAL_COLUMNS
        if "FROM analyst.market_events" in statement:
            return [market_event_row()], MARKET_EVENT_COLUMNS
        if "FROM analyst.segment_impacts" in statement:
            return [segment_row()], SEGMENT_COLUMNS
        if "FROM analyst.equity_impact_assessments" in statement:
            return [assessment_row()], ASSESSMENT_COLUMNS
        if "FROM analyst.valuation_contexts" in statement:
            return [valuation_row()], VALUATION_COLUMNS
        if "FROM analyst.risk_regime_updates" in statement:
            return [risk_row()], RISK_COLUMNS
        if "FROM analyst.trade_plans" in statement:
            return [trade_plan_row()], TRADE_PLAN_COLUMNS
        if "FROM analyst.portfolio_exposure_snapshots" in statement:
            return [portfolio_row()], PORTFOLIO_COLUMNS
        if "FROM analyst.outcome_journal_entries" in statement:
            return [outcome_row()], OUTCOME_COLUMNS
        if "FROM evidence.evidence_items" in statement:
            return self.evidence_rows, EVIDENCE_COLUMNS
        raise AssertionError(f"unexpected select: {statement}")

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self, evidence_rows: list[tuple[object, ...]] | None = None) -> None:
        self.cursor_instance = FakeCursor(
            [evidence_row()] if evidence_rows is None else evidence_rows
        )
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


def source_signal_row() -> tuple[object, ...]:
    return (
        "source-signal-1",
        "earnings_transcript",
        "hyperscaler_capex",
        "Cloud capex raised",
        NOW,
        ["NVDA"],
        ["hyperscaler capex"],
        ["evidence-1"],
        ["market-event-1"],
        "high",
        "reviewed",
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
        "Hyperscaler capex was raised for AI infrastructure.",
        "Supports demand for AI accelerators and networking.",
        "positive",
        "6_to_18_months",
        "high",
        NOW,
        "model-run-1",
        "reviewed",
    )


def segment_row() -> tuple[object, ...]:
    return (
        "segment-1",
        "AI Accelerators",
        ["NVDA"],
        ["TSM"],
        ["market-event-1"],
        "positive",
        "Accelerator demand improves.",
        ["evidence-1"],
    )


def assessment_row() -> tuple[object, ...]:
    return (
        "assessment-1",
        "NVDA",
        "NVIDIA",
        ["market-event-1"],
        "AI capex demand improves the near-term setup.",
        ["HBM supply", "valuation discipline"],
        "accumulate_on_confirmed_capex",
        ["valuation", "supply"],
        "Invalidate if capex evidence reverses.",
        ["evidence-1"],
    )


def valuation_row() -> tuple[object, ...]:
    return (
        "valuation-1",
        "NVDA",
        "premium_supported",
        ["AI demand remains high"],
        ["valuation"],
        ["evidence-1"],
    )


def risk_row() -> tuple[object, ...]:
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
        "Power and HBM constraints still require sizing discipline.",
        NOW,
    )


def trade_plan_row() -> tuple[object, ...]:
    return (
        "trade-plan-1",
        "NVDA",
        "active",
        "accumulate",
        ["market-event-1"],
        "ready",
        [],
        True,
        ["evidence-1"],
        "advisory-old-1",
        NOW,
    )


def portfolio_row() -> tuple[object, ...]:
    return (
        "portfolio-snapshot-1",
        NOW,
        "advisory_only",
        1,
        [{"ticker": "NVDA", "portfolio_weight": "0.18"}],
        ["single_name_watch"],
        [],
    )


def outcome_row() -> tuple[object, ...]:
    return (
        "outcome-1",
        "manual-trade-1",
        "advisory-old-1",
        "NVDA",
        ["market-event-1"],
        ["evidence-1"],
        "open",
        NOW,
        "advisory_only",
    )


def evidence_row() -> tuple[object, ...]:
    return (
        "evidence-1",
        "public_evidence",
        NOW,
        NOW,
        "sha256:evidence-1",
    )


def private_evidence_row() -> tuple[object, ...]:
    return (
        "evidence-1",
        "private_research",
        NOW,
        NOW,
        "sha256:evidence-1",
    )


class StubShadowAnalystModelClient:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def generate_structured(
        self,
        *,
        route: object,
        bundle: object,
        output_schema: str,
    ) -> dict[str, object]:
        self.calls.append(
            {"route": route, "bundle": bundle, "output_schema": output_schema}
        )
        return self.response


def _valid_shadow_response() -> dict[str, object]:
    claim = {
        "claim": "Hyperscaler capex supports AI accelerator demand.",
        "evidence_ids": ("evidence-1",),
    }
    common = {
        "evidence_ids": ("evidence-1",),
        "material_claims": (claim,),
        "payload": {"summary": "Review-required analyst draft."},
    }
    return {
        "segment_impacts": (
            {
                **common,
                "segment_name": "accelerators",
                "linked_event_ids": ("market-event-1",),
                "first_order_tickers": ("NVDA",),
                "second_order_tickers": ("TSM",),
            },
        ),
        "equity_impact_assessments": (
            {
                **common,
                "ticker": "NVDA",
                "assessment": "Capex signal is constructive.",
                "bull_case": "Accelerator demand remains durable.",
                "bear_case": "Supply or valuation pressure weakens setup.",
                "risk_flags": ("valuation",),
                "invalidation_condition": "Capex evidence reverses.",
            },
        ),
        "valuation_contexts": (
            {
                **common,
                "ticker": "NVDA",
                "valuation_summary": "Premium valuation depends on durable AI demand.",
            },
        ),
        "risk_regime_updates": (
            {
                **common,
                "risk_type": "valuation",
                "affected_tickers": ("NVDA",),
                "summary": "Valuation discipline remains required.",
            },
        ),
        "trading_advisories": (
            {
                **common,
                "ticker": "NVDA",
                "analyst_action": "accumulate",
                "rationale": "Constructive catalyst, pending deterministic gate.",
                "market_event_ids": ("market-event-1",),
            },
        ),
        "analyst_briefs": (
            {
                **common,
                "headline": "AI capex supports accelerator demand.",
                "summary": "NVDA remains linked to hyperscaler capex evidence.",
            },
        ),
    }


if __name__ == "__main__":
    unittest.main()
