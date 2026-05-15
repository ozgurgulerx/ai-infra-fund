from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


NOW = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)


class FakeCursor:
    def __init__(self, owner: "FakeConnection") -> None:
        self._owner = owner
        self._last_rows: list[tuple[object, ...]] = []
        self.description: tuple = ()

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self._owner.executed.append((statement, params or ()))
        statement_lower = statement.lower().strip()
        if statement_lower.startswith("insert"):
            assert params is not None
            (
                request_id,
                strategy_id,
                dataset_snapshot_ids,
                validation_protocol,
                cost_assumptions_json,
                pipeline_inputs_json,
                formula_version,
                model_run_id,
                git_sha,
                as_of,
                created_at,
                updated_at,
            ) = params
            self._owner.rows[request_id] = {
                "request_id": request_id,
                "strategy_id": strategy_id,
                "dataset_snapshot_ids": list(dataset_snapshot_ids),  # type: ignore[arg-type]
                "validation_protocol": validation_protocol,
                "cost_assumptions": cost_assumptions_json,
                "pipeline_inputs": pipeline_inputs_json,
                "formula_version": formula_version,
                "model_run_id": model_run_id,
                "git_sha": git_sha,
                "as_of": as_of,
                "status": "queued",
                "leased_by": None,
                "lease_expires_at": None,
                "attempt_count": 0,
                "backtest_run_id": None,
                "error_summary": None,
                "created_at": created_at,
                "updated_at": updated_at,
            }
            self._last_rows = []
            self.description = ()
            return
        if statement_lower.startswith("update"):
            assert params is not None
            if (
                "set status = 'queued'" in statement_lower
                and "lease_expires_at < %s" in statement_lower
            ):
                cutoff = params[0]
                reclaimed_ids: list[object] = []
                for row in self._owner.rows.values():
                    if row["status"] != "leased":
                        continue
                    lease_expires_at = row.get("lease_expires_at")
                    if lease_expires_at is None or lease_expires_at >= cutoff:  # type: ignore[operator]
                        continue
                    row["status"] = "queued"
                    row["leased_by"] = None
                    row["lease_expires_at"] = None
                    row["updated_at"] = NOW
                    reclaimed_ids.append(row["request_id"])
                self._last_rows = [(rid,) for rid in reclaimed_ids]
                self.description = (type("Column", (), {"name": "request_id"})(),)
                return
            if "set status = 'leased'" in statement_lower:
                queued = [
                    row
                    for row in self._owner.rows.values()
                    if row["status"] == "queued"
                ]
                queued.sort(
                    key=lambda row: (row["created_at"], row["request_id"])  # type: ignore[arg-type, return-value]
                )
                if not queued:
                    self._last_rows = []
                    self.description = ()
                    return
                row = queued[0]
                row["status"] = "leased"
                row["leased_by"] = params[0]
                row["lease_expires_at"] = params[1]
                row["attempt_count"] = int(row["attempt_count"] or 0) + 1  # type: ignore[arg-type]
                row["updated_at"] = NOW
                self._populate_rows_from(row)
                return
            request_id = params[-1]
            row = self._owner.rows.get(request_id)
            if row is None:
                self._last_rows = []
                self.description = ()
                return
            if "set status = 'running'" in statement_lower:
                row["status"] = "running"
            elif "set status = 'succeeded'" in statement_lower:
                row["status"] = "succeeded"
                row["backtest_run_id"] = params[0]
            elif "set status = 'failed'" in statement_lower:
                row["status"] = "failed"
                row["error_summary"] = params[0]
            row["updated_at"] = NOW
            self._last_rows = []
            self.description = ()
            return
        if "where request_id" in statement_lower:
            request_id = params[0] if params else None
            row = self._owner.rows.get(request_id)
            rows = [row] if row else []
        elif "where status = 'queued'" in statement_lower:
            queued = [
                row for row in self._owner.rows.values() if row["status"] == "queued"
            ]
            queued.sort(key=lambda row: (row["created_at"], row["request_id"]))
            rows = queued[:1]
        else:
            rows = sorted(
                self._owner.rows.values(),
                key=lambda row: (row["created_at"], row["request_id"]),
                reverse=True,
            )
            if params:
                rows = rows[: int(params[0])]
        column_names = (
            "request_id",
            "strategy_id",
            "dataset_snapshot_ids",
            "validation_protocol",
            "cost_assumptions",
            "pipeline_inputs",
            "formula_version",
            "model_run_id",
            "git_sha",
            "as_of",
            "status",
            "leased_by",
            "lease_expires_at",
            "attempt_count",
            "backtest_run_id",
            "error_summary",
            "created_at",
            "updated_at",
        )
        self._last_rows = [tuple(row[col] for col in column_names) for row in rows]
        self.description = tuple(
            type("Column", (), {"name": name})() for name in column_names
        )

    def _populate_rows_from(self, row: dict[str, object]) -> None:
        column_names = (
            "request_id",
            "strategy_id",
            "dataset_snapshot_ids",
            "validation_protocol",
            "cost_assumptions",
            "pipeline_inputs",
            "formula_version",
            "model_run_id",
            "git_sha",
            "as_of",
            "status",
            "leased_by",
            "lease_expires_at",
            "attempt_count",
            "backtest_run_id",
            "error_summary",
            "created_at",
            "updated_at",
        )
        self._last_rows = [tuple(row[col] for col in column_names)]
        self.description = tuple(
            type("Column", (), {"name": name})() for name in column_names
        )

    def fetchone(self) -> tuple[object, ...] | None:
        return self._last_rows[0] if self._last_rows else None

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._last_rows


class FakeConnection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.rows: dict[object, dict[str, object]] = {}
        self._committed = 0

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self._committed += 1


def _sample_request_dict() -> dict[str, object]:
    return {
        "request_id": "backtest-req-aaaa1111",
        "strategy_id": "strategy-ai-infra-v1",
        "dataset_snapshot_ids": ["dataset-snapshot-2026q1"],
        "validation_protocol": "walk_forward_v1",
        "cost_assumptions": {"spread_bps": "5"},
        "pipeline_inputs": {"placeholder": True},
        "formula_version": "v1",
        "model_run_id": "model-run-shadow-001",
        "git_sha": "abc1234",
        "as_of": NOW,
        "created_at": NOW,
    }


class BacktestRequestRepositoryTests(unittest.TestCase):
    def test_enqueue_stores_request_with_queued_status(self) -> None:
        from ai_infra_fund_api.repositories.backtest_requests import (
            BacktestRequestRepository,
        )

        connection = FakeConnection()
        repository = BacktestRequestRepository(connection)

        repository.enqueue(**_sample_request_dict())

        stored = connection.rows["backtest-req-aaaa1111"]
        self.assertEqual("queued", stored["status"])
        self.assertEqual("strategy-ai-infra-v1", stored["strategy_id"])
        decoded = json.loads(stored["cost_assumptions"])
        self.assertEqual({"spread_bps": "5"}, decoded)

    def test_lease_next_moves_request_to_leased(self) -> None:
        from ai_infra_fund_api.repositories.backtest_requests import (
            BacktestRequestRepository,
        )

        connection = FakeConnection()
        repository = BacktestRequestRepository(connection)
        repository.enqueue(**_sample_request_dict())

        claimed = repository.lease_next(leased_by="worker-1", ttl_seconds=120)

        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual("backtest-req-aaaa1111", claimed["request_id"])
        stored = connection.rows["backtest-req-aaaa1111"]
        self.assertEqual("leased", stored["status"])
        self.assertEqual("worker-1", stored["leased_by"])
        self.assertEqual(1, int(stored["attempt_count"]))

    def test_mark_succeeded_records_backtest_run_id(self) -> None:
        from ai_infra_fund_api.repositories.backtest_requests import (
            BacktestRequestRepository,
        )

        connection = FakeConnection()
        repository = BacktestRequestRepository(connection)
        repository.enqueue(**_sample_request_dict())

        repository.mark_succeeded(
            request_id="backtest-req-aaaa1111",
            backtest_run_id="backtest-abc123",
        )

        stored = connection.rows["backtest-req-aaaa1111"]
        self.assertEqual("succeeded", stored["status"])
        self.assertEqual("backtest-abc123", stored["backtest_run_id"])

    def test_mark_failed_records_error_summary(self) -> None:
        from ai_infra_fund_api.repositories.backtest_requests import (
            BacktestRequestRepository,
        )

        connection = FakeConnection()
        repository = BacktestRequestRepository(connection)
        repository.enqueue(**_sample_request_dict())

        repository.mark_failed(
            request_id="backtest-req-aaaa1111",
            error_summary="lookahead bias detected",
        )

        stored = connection.rows["backtest-req-aaaa1111"]
        self.assertEqual("failed", stored["status"])
        self.assertEqual("lookahead bias detected", stored["error_summary"])

    def test_get_by_id_returns_payload(self) -> None:
        from ai_infra_fund_api.repositories.backtest_requests import (
            BacktestRequestRepository,
        )

        connection = FakeConnection()
        repository = BacktestRequestRepository(connection)
        repository.enqueue(**_sample_request_dict())

        fetched = repository.get_by_id("backtest-req-aaaa1111")

        self.assertIsNotNone(fetched)
        assert fetched is not None
        self.assertEqual("queued", fetched["status"])
        self.assertEqual("strategy-ai-infra-v1", fetched["strategy_id"])

    def test_lease_next_returns_none_when_queue_empty(self) -> None:
        from ai_infra_fund_api.repositories.backtest_requests import (
            BacktestRequestRepository,
        )

        connection = FakeConnection()
        repository = BacktestRequestRepository(connection)

        claimed = repository.lease_next(leased_by="worker-1", ttl_seconds=120)

        self.assertIsNone(claimed)

    def test_reclaim_expired_leases_returns_stuck_rows_to_queue(self) -> None:
        from ai_infra_fund_api.repositories.backtest_requests import (
            BacktestRequestRepository,
        )

        connection = FakeConnection()
        repository = BacktestRequestRepository(connection)
        repository.enqueue(**_sample_request_dict())
        leased = repository.lease_next(leased_by="worker-1", ttl_seconds=120)
        assert leased is not None

        # Force the lease into the past so it is reclaimable.
        connection.rows["backtest-req-aaaa1111"]["lease_expires_at"] = NOW - timedelta(
            minutes=10
        )

        reclaimed = repository.reclaim_expired_leases(now=NOW)

        self.assertEqual(["backtest-req-aaaa1111"], reclaimed)
        stored = connection.rows["backtest-req-aaaa1111"]
        self.assertEqual("queued", stored["status"])
        self.assertIsNone(stored["leased_by"])
        self.assertIsNone(stored["lease_expires_at"])

    def test_reclaim_expired_leases_leaves_active_leases_alone(self) -> None:
        from ai_infra_fund_api.repositories.backtest_requests import (
            BacktestRequestRepository,
        )

        connection = FakeConnection()
        repository = BacktestRequestRepository(connection)
        repository.enqueue(**_sample_request_dict())
        repository.lease_next(leased_by="worker-1", ttl_seconds=300)

        # Lease expires later than now.
        connection.rows["backtest-req-aaaa1111"]["lease_expires_at"] = NOW + timedelta(
            minutes=5
        )

        reclaimed = repository.reclaim_expired_leases(now=NOW)

        self.assertEqual([], reclaimed)
        stored = connection.rows["backtest-req-aaaa1111"]
        self.assertEqual("leased", stored["status"])


if __name__ == "__main__":
    unittest.main()
