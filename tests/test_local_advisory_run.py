from __future__ import annotations

from pathlib import Path
import stat
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))


class LocalAdvisoryRunTests(unittest.TestCase):
    def test_local_advisory_run_persists_full_chain_from_user_inputs(self) -> None:
        from ai_infra_fund_worker.local_advisory_run import run_local_advisory

        with tempfile.TemporaryDirectory() as tmp:
            input_dir = write_sample_inputs(Path(tmp))
            connection = FakeConnection()

            result = run_local_advisory(connection, input_dir)
            second = run_local_advisory(connection, input_dir)

        self.assertEqual("succeeded", result["status"])
        self.assertEqual("local_advisory", result["run_type"])
        self.assertEqual(0, result["exit_code"])
        self.assertEqual(result["run_id"], second["run_id"])
        self.assertIn("recommendation_id=", str(result["artifact_uri"]))
        self.assertIn("audit_id=", str(result["artifact_uri"]))
        self.assertIn("backtest_run_id=", str(result["artifact_uri"]))
        self.assertIn("advisory_label=advisory_only", str(result["artifact_uri"]))

        statements = "\n".join(
            statement for statement, _params in connection.cursor_instance.executions
        )
        for table_name in (
            "core.portfolio_snapshots",
            "core.portfolio_snapshot_positions",
            "core.trade_entries",
            "core.watched_equities",
            "core.universe_members",
            "signals.market_snapshots",
            "evidence.evidence_items",
            "evidence.evidence_chunks",
            "evidence.evidence_claims",
            "evidence.source_registry",
            "evidence.source_raw_captures",
            "signals.equity_events",
            "signals.sentiment_snapshots",
            "signals.technical_snapshots",
            "signals.fundamental_snapshots",
            "audit.equity_intelligence_runs",
            "audit.model_runs",
            "signals.signal_bundles",
            "recommendations.target_weights",
            "recommendations.recommendation_artifacts",
            "recommendations.recommendation_audits",
            "audit.backtest_runs",
            "audit.run_artifacts",
        ):
            self.assertIn(table_name, statements)

        for statement, params in connection.cursor_instance.executions:
            self.assertIsInstance(params, tuple)
            self.assertNotIn("PLACE_ORDER", statement.upper())
            self.assertNotIn("SUBMIT_ORDER", statement.upper())
            self.assertNotIn("ORDER_EXECUTION", statement.upper())

        self.assertIn("evidence_claim_ids", statements)
        self.assertIn("model_run_ids", statements)
        self.assertIn("review_status", statements)

    def test_missing_evidence_provenance_fails_closed_and_writes_failed_run_artifact(
        self,
    ) -> None:
        from ai_infra_fund_worker.local_advisory_run import run_local_advisory

        with tempfile.TemporaryDirectory() as tmp:
            input_dir = write_sample_inputs(Path(tmp), missing_evidence_license=True)
            connection = FakeConnection()

            result = run_local_advisory(connection, input_dir)

        self.assertEqual("failed", result["status"])
        self.assertEqual(1, result["exit_code"])
        self.assertIn("license_label", str(result["error_summary"]))
        statements = [
            statement for statement, _params in connection.cursor_instance.executions
        ]
        self.assertEqual(1, len(statements))
        self.assertIn("INSERT INTO audit.run_artifacts", statements[0])

    def test_event_sink_receives_signal_weights_and_recommendation_events(self) -> None:
        from ai_infra_fund_worker.local_advisory_run import run_local_advisory

        emitted: list[object] = []

        with tempfile.TemporaryDirectory() as tmp:
            input_dir = write_sample_inputs(Path(tmp))
            connection = FakeConnection()

            run_local_advisory(connection, input_dir, event_sink=emitted.append)

        kinds = [event.kind for event in emitted]  # type: ignore[attr-defined]
        self.assertIn("signal_computed", kinds)
        self.assertIn("weights_generated", kinds)
        self.assertIn("recommendation_issued", kinds)
        # weights_generated must precede recommendation_issued.
        self.assertLess(
            kinds.index("weights_generated"), kinds.index("recommendation_issued")
        )
        # All events should carry the same advisory run_id.
        run_ids = {event.run_id for event in emitted}  # type: ignore[attr-defined]
        self.assertEqual(1, len(run_ids))
        run_id = run_ids.pop()
        assert run_id is not None
        self.assertTrue(run_id.startswith("run-local-advisory-"))

    def test_local_advisory_run_uses_deterministic_no_model_marker(self) -> None:
        from ai_infra_fund_worker.local_advisory_run import run_local_advisory

        with tempfile.TemporaryDirectory() as tmp:
            connection = FakeConnection()
            result = run_local_advisory(connection, write_sample_inputs(Path(tmp)))

        self.assertIn("deterministic-no-model", result["model_run_id"])
        model_run_inserts = [
            params
            for statement, params in connection.cursor_instance.executions
            if "INSERT INTO audit.model_runs" in statement
        ]
        self.assertEqual(1, len(model_run_inserts))
        self.assertIn("deterministic-no-model", model_run_inserts[0])
        self.assertIn("success", model_run_inserts[0])

    def test_sample_local_advisory_script_exists_and_invokes_worker_module(
        self,
    ) -> None:
        script = ROOT / "scripts" / "run_local_advisory_sample.sh"

        self.assertTrue(script.is_file())
        self.assertTrue(script.stat().st_mode & stat.S_IXUSR)
        text = script.read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", text)
        self.assertIn("python -m ai_infra_fund_worker.local_advisory_run", text)
        self.assertIn("AI_INFRA_FUND_LOCAL_INPUT_DIR", text)
        self.assertNotIn("curl", text)

    def test_local_advisory_module_has_no_external_model_or_execution_surface(
        self,
    ) -> None:
        module = (
            ROOT
            / "services"
            / "worker"
            / "src"
            / "ai_infra_fund_worker"
            / "local_advisory_run.py"
        )
        text = module.read_text(encoding="utf-8").lower()

        forbidden = [
            "openai",
            "azure",
            "requests",
            "httpx",
            "place_order",
            "submit_order",
            "order_execution",
        ]
        offenders = [word for word in forbidden if word in text]
        self.assertEqual([], offenders)


class FakeCursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.description: tuple[tuple[str], ...] = ()

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params if params is not None else ()))

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


def write_sample_inputs(root: Path, *, missing_evidence_license: bool = False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "portfolio_positions.csv").write_text(
        "\n".join(
            [
                "ticker,quantity,cost_basis,market_price,currency,asset_type,account_label,as_of,available_at",
                "NVDA,3,200,900,USD,equity,local,2026-05-14T10:00:00+00:00,2026-05-14T10:05:00+00:00",
                "MSFT,4,300,410,USD,equity,local,2026-05-14T10:00:00+00:00,2026-05-14T10:05:00+00:00",
                "CASH,1000,1,1,USD,cash,local,2026-05-14T10:00:00+00:00,2026-05-14T10:05:00+00:00",
            ]
        ),
        encoding="utf-8",
    )
    (root / "trade_journal.csv").write_text(
        "\n".join(
            [
                "ticker,side,quantity,price,fees,trade_date,status,account_label,notes",
                "NVDA,buy,1,850,0,2026-05-10,completed,local,manual entry",
            ]
        ),
        encoding="utf-8",
    )
    (root / "universe.csv").write_text(
        "\n".join(
            [
                "ticker,name,theme,role,watchlist_status,max_weight,liquidity_floor,thesis_source",
                "NVDA,NVIDIA,ai_accelerators,core,active,0.25,0.00,local thesis",
                "MSFT,Microsoft,ai_cloud,core,active,0.25,0.00,local thesis",
            ]
        ),
        encoding="utf-8",
    )
    (root / "market_snapshots.csv").write_text(
        "\n".join(
            [
                "ticker,asset_type,as_of,available_at,source,close_price,volume",
                "NVDA,equity,2026-05-14T10:00:00+00:00,2026-05-14T10:05:00+00:00,manual,900,1000000",
                "MSFT,equity,2026-05-14T10:00:00+00:00,2026-05-14T10:05:00+00:00,manual,410,1200000",
            ]
        ),
        encoding="utf-8",
    )
    (root / "nvda-note.md").write_text(
        "NVDA accelerator demand remains strong and local evidence supports medium-term AI infrastructure exposure.",
        encoding="utf-8",
    )
    license_label = "" if missing_evidence_license else "user_private"
    (root / "evidence_index.csv").write_text(
        "\n".join(
            [
                "file_path,source_uri,license_label,data_class,tickers,themes,title,confidence,horizon",
                f"nvda-note.md,file://local/nvda-note.md,{license_label},private_research,NVDA,ai_accelerators,Local AI note,0.80,medium_term",
            ]
        ),
        encoding="utf-8",
    )
    return root


if __name__ == "__main__":
    unittest.main()
