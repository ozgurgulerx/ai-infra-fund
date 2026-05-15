from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_api.repositories.dashboard import DashboardRepository  # noqa: E402


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 5, 14, 13, 0, tzinfo=timezone.utc)

SUMMARY_COLUMNS = (
    "total_items",
    "total_chunks",
    "total_claims",
    "items_by_data_class",
    "latest_ingested_at",
    "latest_created_at",
)

RECOMMENDATION_COLUMNS = (
    "total_recommendations",
    "total_audits",
    "schema_valid_audits",
    "schema_invalid_audits",
    "latest_created_at",
)

MODEL_RUN_COLUMNS = (
    "total_model_runs",
    "runs_by_status",
    "latest_created_at",
)

EVALUATION_COLUMNS = (
    "total_backtest_runs",
    "backtest_runs_by_status",
    "total_run_artifacts",
    "run_artifacts_by_status",
    "latest_created_at",
)

DATA_QUALITY_COLUMNS = (
    "total_checks",
    "checks_by_status",
    "checks_by_severity",
    "latest_checked_at",
    "latest_created_at",
)

INCIDENT_COLUMNS = (
    "total_incidents",
    "incidents_by_severity",
    "incidents_by_freeze_status",
    "open_incidents",
    "latest_created_at",
)

WATCHLIST_COLUMNS = (
    "total_members",
    "by_watchlist_status",
    "latest_updated_at",
)

WATCHLIST_MEMBER_COLUMNS = (
    "ticker",
    "name",
    "theme",
    "role",
    "watchlist_status",
    "max_weight",
    "liquidity_floor",
    "thesis_source",
    "updated_at",
)

CRAWL_FRONTIER_COLUMNS = (
    "dataset_name",
    "source",
    "latest_retrieved_at",
    "latest_available_at",
    "latest_effective_at",
    "latest_created_at",
    "snapshot_count",
    "row_count",
)

EQUITY_EVENT_COLUMNS = (
    "evidence_id",
    "source_uri",
    "source_type",
    "title",
    "publisher",
    "published_at",
    "ingested_at",
    "data_class",
    "tickers",
    "themes",
    "summary",
)

SIGNAL_SNAPSHOT_COLUMNS = (
    "signal_bundle_id",
    "ticker",
    "as_of",
    "strategic_thesis_score",
    "tactical_technical_score",
    "forward_indicator_score",
    "portfolio_risk_score",
    "formula_versions",
    "input_snapshot_hash",
    "created_at",
)

ADVISORY_RUN_COLUMNS = (
    "run_id",
    "run_type",
    "started_at",
    "completed_at",
    "artifact_uri",
    "status",
    "error_summary",
    "created_at",
)

TICKER_RECOMMENDATION_COLUMNS = (
    "recommendation_id",
    "ticker_or_portfolio",
    "advisory_label",
    "action",
    "horizon",
    "target_weights_id",
    "signal_bundle_id",
    "evidence_ids",
    "model_run_ids",
    "created_at",
)


class DashboardRepositoryTests(unittest.TestCase):
    def test_returns_zero_default_summaries_on_empty_database(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet([(0, 0, 0, {}, None, None)], SUMMARY_COLUMNS),
                ResultSet([(0, 0, 0, 0, None)], RECOMMENDATION_COLUMNS),
                ResultSet([(0, {}, None)], MODEL_RUN_COLUMNS),
                ResultSet([(0, {}, 0, {}, None)], EVALUATION_COLUMNS),
                ResultSet([(0, {}, {}, None, None)], DATA_QUALITY_COLUMNS),
                ResultSet([(0, {}, {}, 0, None)], INCIDENT_COLUMNS),
            ],
        )

        summary = DashboardRepository(connection).overview()

        self.assertEqual("empty", summary["status"])
        self.assertEqual(0, summary["evidence"]["total_items"])
        self.assertEqual(0, summary["evidence"]["total_chunks"])
        self.assertEqual(0, summary["evidence"]["total_claims"])
        self.assertEqual({}, summary["evidence"]["items_by_data_class"])
        self.assertIsNone(summary["evidence"]["latest_ingested_at"])
        self.assertIsNone(summary["evidence"]["latest_created_at"])
        self.assertEqual(0, summary["recommendations"]["total_recommendations"])
        self.assertEqual(0, summary["model_runs"]["total_model_runs"])
        self.assertEqual(0, summary["evaluations"]["total_backtest_runs"])
        self.assertEqual(0, summary["data_quality"]["total_checks"])
        self.assertEqual(0, summary["incidents"]["total_incidents"])
        self.assertEqual(0, connection.commit_count)
        self.assertEqual(6, len(connection.cursor_instance.executions))
        for statement, params in connection.cursor_instance.executions:
            self.assertIn("SELECT", statement.upper())
            self.assertNotIn("INSERT", statement.upper())
            self.assertNotIn("UPDATE", statement.upper())
            self.assertNotIn("DELETE", statement.upper())
            self.assertIsInstance(params, tuple)

    def test_route_adapter_methods_delegate_to_read_only_summaries(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [(1, 2, 3, {"public_evidence": 1}, NOW, LATER)], SUMMARY_COLUMNS
                ),
                ResultSet([(4, 5, 5, 0, LATER)], RECOMMENDATION_COLUMNS),
                ResultSet([(6, {"success": 5, "denied": 1}, LATER)], MODEL_RUN_COLUMNS),
                ResultSet(
                    [(7, {"succeeded": 7}, 8, {"succeeded": 8}, LATER)],
                    EVALUATION_COLUMNS,
                ),
                ResultSet(
                    [(9, {"pass": 9}, {"low": 9}, NOW, LATER)], DATA_QUALITY_COLUMNS
                ),
                ResultSet(
                    [(10, {"low": 10}, {"resolved": 10}, 0, LATER)], INCIDENT_COLUMNS
                ),
            ],
        )

        modules = DashboardRepository(connection).get_status_modules()

        self.assertEqual(6, len(connection.cursor_instance.executions))
        module_ids = [module["id"] for module in modules["modules"]]
        self.assertIn("data-plane", module_ids)
        self.assertIn("evidence-plane", module_ids)
        self.assertIn("recommendation-artifacts", module_ids)
        self.assertIn("model-router", module_ids)
        self.assertIn("evaluation-harness", module_ids)
        self.assertIn("data-quality", module_ids)
        self.assertIn("incidents", module_ids)
        for module in modules["modules"]:
            self.assertIn("status", module)
            self.assertIn("source_label", module)
            self.assertIn("detail", module)
            self.assertNotIn("chunk_text", str(module))
            self.assertNotIn("final_payload_json", str(module))

    def test_counts_evidence_items_chunks_claims_and_latest_timestamps(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [(3, 12, 7, {"public": 2, "restricted": 1}, NOW, LATER)],
                    SUMMARY_COLUMNS,
                ),
            ],
        )

        summary = DashboardRepository(connection).evidence_summary()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM evidence.evidence_items", statement)
        self.assertIn("FROM evidence.evidence_chunks", statement)
        self.assertIn("FROM evidence.evidence_claims", statement)
        self.assertNotIn("chunk_text", statement)
        self.assertEqual((), params)
        self.assertEqual(
            {
                "status": "available",
                "total_items": 3,
                "total_chunks": 12,
                "total_claims": 7,
                "items_by_data_class": {"public": 2, "restricted": 1},
                "latest_ingested_at": "2026-05-14T12:00:00+00:00",
                "latest_created_at": "2026-05-14T13:00:00+00:00",
            },
            summary,
        )

    def test_counts_recommendations_and_audits(self) -> None:
        connection = FakeConnection(
            result_sets=[ResultSet([(5, 4, 3, 1, LATER)], RECOMMENDATION_COLUMNS)],
        )

        summary = DashboardRepository(connection).recommendation_summary()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM recommendations.recommendation_artifacts", statement)
        self.assertIn("FROM recommendations.recommendation_audits", statement)
        self.assertNotIn("final_payload_json", statement)
        self.assertEqual((), params)
        self.assertEqual(5, summary["total_recommendations"])
        self.assertEqual(4, summary["total_audits"])
        self.assertEqual(3, summary["schema_valid_audits"])
        self.assertEqual(1, summary["schema_invalid_audits"])
        self.assertEqual("2026-05-14T13:00:00+00:00", summary["latest_created_at"])
        self.assertEqual("available", summary["status"])

    def test_counts_model_runs_by_status(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [(4, {"succeeded": 2, "failed": 1, "running": 1}, LATER)],
                    MODEL_RUN_COLUMNS,
                ),
            ],
        )

        summary = DashboardRepository(connection).model_run_summary()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM audit.model_runs", statement)
        self.assertNotIn("model_id", statement)
        self.assertNotIn("deployment", statement)
        self.assertEqual((), params)
        self.assertEqual(4, summary["total_model_runs"])
        self.assertEqual(
            {"succeeded": 2, "failed": 1, "running": 1}, summary["runs_by_status"]
        )
        self.assertEqual("available", summary["status"])

    def test_counts_evaluation_backtest_and_run_artifact_records(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [
                        (
                            2,
                            {"succeeded": 1, "failed": 1},
                            3,
                            {"succeeded": 2, "pending": 1},
                            LATER,
                        )
                    ],
                    EVALUATION_COLUMNS,
                ),
            ],
        )

        summary = DashboardRepository(connection).evaluation_summary()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM audit.backtest_runs", statement)
        self.assertIn("FROM audit.run_artifacts", statement)
        self.assertNotIn("artifact_uri", statement)
        self.assertEqual((), params)
        self.assertEqual(2, summary["total_backtest_runs"])
        self.assertEqual(
            {"succeeded": 1, "failed": 1}, summary["backtest_runs_by_status"]
        )
        self.assertEqual(3, summary["total_run_artifacts"])
        self.assertEqual(
            {"succeeded": 2, "pending": 1}, summary["run_artifacts_by_status"]
        )

    def test_counts_data_quality_checks_by_status_and_severity(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [
                        (
                            3,
                            {"passed": 2, "failed": 1},
                            {"low": 1, "high": 2},
                            NOW,
                            LATER,
                        )
                    ],
                    DATA_QUALITY_COLUMNS,
                ),
            ],
        )

        summary = DashboardRepository(connection).data_quality_summary()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM governance.data_quality_checks", statement)
        self.assertEqual((), params)
        self.assertEqual(3, summary["total_checks"])
        self.assertEqual({"passed": 2, "failed": 1}, summary["checks_by_status"])
        self.assertEqual({"low": 1, "high": 2}, summary["checks_by_severity"])
        self.assertEqual("available", summary["status"])

    def test_counts_incidents_by_severity_and_freeze_status(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [
                        (
                            4,
                            {"critical": 1, "medium": 3},
                            {"frozen": 2, "none": 2},
                            1,
                            LATER,
                        )
                    ],
                    INCIDENT_COLUMNS,
                ),
            ],
        )

        summary = DashboardRepository(connection).incident_summary()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM governance.incident_records", statement)
        self.assertEqual((), params)
        self.assertEqual(4, summary["total_incidents"])
        self.assertEqual({"critical": 1, "medium": 3}, summary["incidents_by_severity"])
        self.assertEqual(
            {"frozen": 2, "none": 2}, summary["incidents_by_freeze_status"]
        )
        self.assertEqual(1, summary["open_incidents"])
        self.assertEqual("degraded", summary["status"])

    def test_get_status_overview_matches_overview_payload(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet([(0, 0, 0, {}, None, None)], SUMMARY_COLUMNS),
                ResultSet([(0, 0, 0, 0, None)], RECOMMENDATION_COLUMNS),
                ResultSet([(0, {}, None)], MODEL_RUN_COLUMNS),
                ResultSet([(0, {}, 0, {}, None)], EVALUATION_COLUMNS),
                ResultSet([(0, {}, {}, None, None)], DATA_QUALITY_COLUMNS),
                ResultSet([(0, {}, {}, 0, None)], INCIDENT_COLUMNS),
            ],
        )

        summary = DashboardRepository(connection).get_status_overview()

        self.assertEqual("empty", summary["status"])
        self.assertEqual(0, summary["evidence"]["total_items"])
        self.assertEqual(0, summary["recommendations"]["total_recommendations"])

    def test_phase10_watchlist_summary_reads_universe_members_only(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet([(2, {"active": 1, "watch": 1}, LATER)], WATCHLIST_COLUMNS),
                ResultSet(
                    [
                        (
                            "NVDA",
                            "NVIDIA",
                            "ai_accelerators",
                            "core",
                            "active",
                            "0.20",
                            "1000000",
                            "manual thesis",
                            LATER,
                        )
                    ],
                    WATCHLIST_MEMBER_COLUMNS,
                ),
            ],
        )

        summary = DashboardRepository(connection).watchlist_summary()

        self.assertEqual("available", summary["status"])
        self.assertEqual(2, summary["total_members"])
        self.assertEqual({"active": 1, "watch": 1}, summary["by_watchlist_status"])
        self.assertEqual("NVDA", summary["members"][0]["ticker"])
        self.assertEqual("0.20", summary["members"][0]["max_weight"])
        self.assertEqual(2, len(connection.cursor_instance.executions))
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM core.universe_members", statement)
        self.assertNotIn("INSERT", statement.upper())
        self.assertEqual((), params)

    def test_phase10_empty_watchlist_summary_is_defensive(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet([(0, {}, None)], WATCHLIST_COLUMNS),
                ResultSet([], WATCHLIST_MEMBER_COLUMNS),
            ],
        )

        summary = DashboardRepository(connection).watchlist_summary()

        self.assertEqual("empty", summary["status"])
        self.assertEqual(0, summary["total_members"])
        self.assertEqual([], summary["members"])

    def test_phase10_crawl_frontier_health_reads_data_snapshots(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [("equity_events", "local", NOW, LATER, NOW, LATER, 3, 42)],
                    CRAWL_FRONTIER_COLUMNS,
                )
            ],
        )

        summary = DashboardRepository(connection).crawl_frontier_health()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM audit.data_snapshots", statement)
        self.assertEqual((), params)
        self.assertEqual("available", summary["status"])
        self.assertEqual("2026-05-14T13:00:00+00:00", summary["latest_available_at"])
        self.assertEqual(1, len(summary["datasets"]))
        self.assertEqual("equity_events", summary["datasets"][0]["dataset_name"])

    def test_phase10_latest_equity_events_excludes_raw_evidence_body(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [
                        (
                            "evidence-nvda",
                            "https://example.test/nvda",
                            "news",
                            "NVIDIA event",
                            "Example",
                            NOW,
                            LATER,
                            "public_evidence",
                            ["NVDA"],
                            ["ai_accelerators"],
                            "Demand signal",
                        )
                    ],
                    EQUITY_EVENT_COLUMNS,
                )
            ],
        )

        summary = DashboardRepository(connection).latest_equity_events()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM evidence.evidence_items", statement)
        self.assertNotIn("chunk_text", statement)
        self.assertEqual((10,), params)
        self.assertEqual("available", summary["status"])
        self.assertEqual("evidence-nvda", summary["events"][0]["evidence_id"])
        self.assertNotIn("content", summary["events"][0])

    def test_phase10_latest_signal_snapshots_maps_score_cards(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [
                        (
                            "signal-bundle-nvda",
                            "NVDA",
                            LATER,
                            "0.84",
                            "0.61",
                            "0.72",
                            "0.32",
                            {"strategic_thesis_score": "v1"},
                            "c" * 64,
                            LATER,
                        )
                    ],
                    SIGNAL_SNAPSHOT_COLUMNS,
                )
            ],
        )

        summary = DashboardRepository(connection).latest_signal_snapshots()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM signals.signal_bundles", statement)
        self.assertEqual((10,), params)
        self.assertEqual("available", summary["status"])
        snapshot = summary["snapshots"][0]
        self.assertEqual("0.72", snapshot["sentiment_score"])
        self.assertEqual("0.61", snapshot["technical_score"])
        self.assertEqual("0.84", snapshot["fundamental_score"])

    def test_phase10_latest_advisory_run_is_read_only_and_advisory_labeled(
        self,
    ) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [
                        (
                            "run-local-advisory-1",
                            "local_advisory",
                            NOW,
                            LATER,
                            "artifact://local/advisory-run/run-local-advisory-1?advisory_label=advisory_only",
                            "succeeded",
                            None,
                            LATER,
                        )
                    ],
                    ADVISORY_RUN_COLUMNS,
                )
            ],
        )

        summary = DashboardRepository(connection).latest_advisory_run()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM audit.run_artifacts", statement)
        self.assertIn("local_advisory", params)
        self.assertEqual("available", summary["status"])
        self.assertEqual("advisory_only", summary["advisory_label"])
        self.assertEqual("run-local-advisory-1", summary["run_id"])

    def test_phase10_ticker_intelligence_combines_latest_read_models(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [
                        (
                            "NVDA",
                            "NVIDIA",
                            "ai_accelerators",
                            "core",
                            "active",
                            "0.20",
                            "1000000",
                            "manual thesis",
                            LATER,
                        )
                    ],
                    WATCHLIST_MEMBER_COLUMNS,
                ),
                ResultSet(
                    [
                        (
                            "signal-bundle-nvda",
                            "NVDA",
                            LATER,
                            "0.84",
                            "0.61",
                            "0.72",
                            "0.32",
                            {"strategic_thesis_score": "v1"},
                            "c" * 64,
                            LATER,
                        )
                    ],
                    SIGNAL_SNAPSHOT_COLUMNS,
                ),
                ResultSet(
                    [
                        (
                            "recommendation-nvda",
                            "NVDA",
                            "advisory_only",
                            "accumulate",
                            "medium_term",
                            "target-weights-nvda",
                            "signal-bundle-nvda",
                            ["evidence-nvda"],
                            ["model-run-nvda"],
                            LATER,
                        )
                    ],
                    TICKER_RECOMMENDATION_COLUMNS,
                ),
                ResultSet(
                    [
                        (
                            "evidence-nvda",
                            "https://example.test/nvda",
                            "news",
                            "NVIDIA event",
                            "Example",
                            NOW,
                            LATER,
                            "public_evidence",
                            ["NVDA"],
                            ["ai_accelerators"],
                            "Demand signal",
                        )
                    ],
                    EQUITY_EVENT_COLUMNS,
                ),
            ],
        )

        summary = DashboardRepository(connection).ticker_intelligence_summary("nvda")

        self.assertEqual("available", summary["status"])
        self.assertEqual("NVDA", summary["ticker"])
        self.assertEqual("active", summary["watchlist"]["watchlist_status"])
        self.assertEqual("0.61", summary["latest_scores"]["technical_score"])
        self.assertEqual(
            "advisory_only", summary["latest_recommendation"]["advisory_label"]
        )
        self.assertEqual("evidence-nvda", summary["latest_events"][0]["evidence_id"])
        for _statement, params in connection.cursor_instance.executions:
            self.assertIn("NVDA", params)


class ResultSet:
    def __init__(
        self, rows: list[tuple[object, ...]], columns: tuple[str, ...]
    ) -> None:
        self.rows = rows
        self.columns = columns


class FakeCursor:
    def __init__(self, result_sets: list[ResultSet]) -> None:
        self._result_sets = result_sets
        self._index = 0
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.description: tuple[tuple[str], ...] = ()
        self.rows: list[tuple[object, ...]] = []

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params if params is not None else ()))
        result_set = self._result_sets[self._index]
        self._index += 1
        self.rows = result_set.rows
        self.description = tuple((column,) for column in result_set.columns)

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self, *, result_sets: list[ResultSet]) -> None:
        self.cursor_instance = FakeCursor(result_sets)
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


PORTFOLIO_SNAPSHOT_COLUMNS = (
    "snapshot_id",
    "as_of",
    "cash_value",
    "total_market_value",
    "source",
)

PORTFOLIO_POSITION_COLUMNS = (
    "ticker",
    "quantity",
    "market_price",
    "market_value",
    "portfolio_weight",
    "unrealized_pnl",
)

RECOMMENDATION_SUMMARY_COLUMNS = (
    "recommendation_id",
    "ticker_or_portfolio",
    "action",
    "horizon",
    "advisory_label",
    "signal_bundle_id",
    "target_weights_id",
    "evidence_count",
    "model_run_count",
    "created_at",
    "schema_valid",
)


class PortfolioSummaryTests(unittest.TestCase):
    def test_returns_latest_snapshot_with_day_delta_against_previous(self) -> None:
        latest_id = "11111111-1111-1111-1111-111111111111"
        previous_id = "22222222-2222-2222-2222-222222222222"
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [
                        (latest_id, LATER, "100", "1200", "manual"),
                        (previous_id, NOW, "100", "1000", "manual"),
                    ],
                    PORTFOLIO_SNAPSHOT_COLUMNS,
                ),
                ResultSet(
                    [
                        ("NVDA", "10", "100", "1000", "0.8333", "200"),
                        ("CASH", "100", "1", "100", "0.0833", "0"),
                    ],
                    PORTFOLIO_POSITION_COLUMNS,
                ),
            ],
        )

        summary = DashboardRepository(connection).portfolio_summary()

        statements = [
            statement for statement, _ in connection.cursor_instance.executions
        ]
        self.assertEqual(2, len(statements))
        self.assertIn("FROM core.portfolio_snapshots", statements[0])
        self.assertIn("ORDER BY as_of DESC", statements[0])
        self.assertIn("FROM core.portfolio_snapshot_positions", statements[1])
        self.assertEqual("available", summary["status"])
        self.assertEqual("advisory_only", summary["advisory_label"])
        self.assertEqual(latest_id, summary["snapshot_id"])
        self.assertEqual("1200", summary["total_market_value"])
        self.assertEqual("100", summary["cash_value"])
        self.assertEqual("1000", summary["previous_total_market_value"])
        self.assertAlmostEqual(0.2, summary["day_delta_pct"], places=6)
        self.assertEqual(2, len(summary["positions"]))
        self.assertEqual("NVDA", summary["positions"][0]["ticker"])
        self.assertEqual("0.8333", summary["positions"][0]["portfolio_weight"])

    def test_returns_empty_when_no_snapshots(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet([], PORTFOLIO_SNAPSHOT_COLUMNS),
            ],
        )

        summary = DashboardRepository(connection).portfolio_summary()

        self.assertEqual("empty", summary["status"])
        self.assertIsNone(summary["snapshot_id"])
        self.assertIsNone(summary["day_delta_pct"])
        self.assertEqual([], summary["positions"])
        self.assertEqual(1, len(connection.cursor_instance.executions))

    def test_day_delta_is_none_when_only_one_snapshot_exists(self) -> None:
        latest_id = "33333333-3333-3333-3333-333333333333"
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [(latest_id, NOW, "0", "500", "manual")],
                    PORTFOLIO_SNAPSHOT_COLUMNS,
                ),
                ResultSet([], PORTFOLIO_POSITION_COLUMNS),
            ],
        )

        summary = DashboardRepository(connection).portfolio_summary()

        self.assertEqual("available", summary["status"])
        self.assertIsNone(summary["previous_total_market_value"])
        self.assertIsNone(summary["day_delta_pct"])


class LatestRecommendationsTests(unittest.TestCase):
    def test_returns_summary_items_ordered_by_created_at(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [
                        (
                            "rec-nvda-1",
                            "NVDA",
                            "accumulate",
                            "1M",
                            "advisory_only",
                            "sb-1",
                            "tw-1",
                            4,
                            2,
                            LATER,
                            True,
                        ),
                        (
                            "rec-msft-1",
                            "MSFT",
                            "hold",
                            "QTR",
                            "advisory_only",
                            "sb-2",
                            "tw-2",
                            3,
                            1,
                            NOW,
                            True,
                        ),
                    ],
                    RECOMMENDATION_SUMMARY_COLUMNS,
                ),
            ],
        )

        summary = DashboardRepository(connection).latest_recommendations(5)

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM recommendations.recommendation_artifacts", statement)
        self.assertIn("LEFT JOIN recommendations.recommendation_audits", statement)
        self.assertIn("ORDER BY artifact.created_at DESC", statement)
        self.assertIn("LIMIT %s", statement)
        self.assertEqual((5,), params)
        self.assertEqual("available", summary["status"])
        self.assertEqual("advisory_only", summary["advisory_label"])
        self.assertEqual(2, len(summary["items"]))
        first = summary["items"][0]
        self.assertEqual("rec-nvda-1", first["recommendation_id"])
        self.assertEqual("NVDA", first["ticker_or_portfolio"])
        self.assertEqual("accumulate", first["action"])
        self.assertEqual("advisory_only", first["advisory_label"])
        self.assertEqual(4, first["evidence_count"])
        self.assertEqual(2, first["model_run_count"])
        self.assertTrue(first["schema_valid"])

    def test_returns_empty_status_with_no_recommendations(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet([], RECOMMENDATION_SUMMARY_COLUMNS),
            ],
        )

        summary = DashboardRepository(connection).latest_recommendations(10)

        self.assertEqual("empty", summary["status"])
        self.assertEqual([], summary["items"])

    def test_rejects_non_positive_limit(self) -> None:
        connection = FakeConnection(
            result_sets=[ResultSet([], RECOMMENDATION_SUMMARY_COLUMNS)],
        )

        with self.assertRaises(ValueError):
            DashboardRepository(connection).latest_recommendations(0)


class RouteAdapterDelegationTests(unittest.TestCase):
    def test_get_portfolio_summary_delegates_to_portfolio_summary(self) -> None:
        latest_id = "44444444-4444-4444-4444-444444444444"
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [(latest_id, NOW, "0", "100", "manual")],
                    PORTFOLIO_SNAPSHOT_COLUMNS,
                ),
                ResultSet([], PORTFOLIO_POSITION_COLUMNS),
            ],
        )

        summary = DashboardRepository(connection).get_portfolio_summary()

        self.assertEqual("available", summary["status"])

    def test_get_latest_recommendations_delegates_with_default_limit(self) -> None:
        connection = FakeConnection(
            result_sets=[ResultSet([], RECOMMENDATION_SUMMARY_COLUMNS)],
        )

        summary = DashboardRepository(connection).get_latest_recommendations()

        _statement, params = connection.cursor_instance.executions[0]
        self.assertEqual((10,), params)
        self.assertEqual("empty", summary["status"])


if __name__ == "__main__":
    unittest.main()
