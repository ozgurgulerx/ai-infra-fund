from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


class FakeCursor:
    def __init__(self, owner: "FakeConnection") -> None:
        self._owner = owner
        self._last_rows: list[tuple[object, ...]] = []
        self._row_iter = iter([])
        self.description: tuple = ()

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self._owner.executed.append((statement, params or ()))
        statement_lower = statement.lower()
        if statement_lower.lstrip().startswith("insert"):
            assert params is not None
            (
                event_id,
                kind,
                run_id,
                severity,
                payload_json,
                occurred_at,
                created_at,
            ) = params
            self._owner.rows[event_id] = {
                "event_id": event_id,
                "kind": kind,
                "run_id": run_id,
                "severity": severity,
                "payload": payload_json,
                "occurred_at": occurred_at,
                "created_at": created_at,
            }
            self._last_rows = []
            self._row_iter = iter(self._last_rows)
            self.description = ()
            return
        if "where run_id" in statement_lower:
            run_id = params[0] if params else None
            matching = [
                row for row in self._owner.rows.values() if row["run_id"] == run_id
            ]
        else:
            matching = list(self._owner.rows.values())
            if params:
                if "since" in statement_lower and params[0] is not None:
                    matching = [
                        row for row in matching if row["occurred_at"] >= params[0]
                    ]
        matching.sort(
            key=lambda row: (row["occurred_at"], row["created_at"], row["event_id"]),
            reverse=True,
        )
        if "limit" in statement_lower:
            limit = params[-1] if params else len(matching)
            matching = matching[: int(limit)]
        column_names = (
            "event_id",
            "kind",
            "run_id",
            "severity",
            "payload",
            "occurred_at",
            "created_at",
        )
        rows = [tuple(row[col] for col in column_names) for row in matching]
        self._last_rows = rows
        self._row_iter = iter(rows)
        self.description = tuple(
            type("Column", (), {"name": name})() for name in column_names
        )

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


class ExperimentEventsRepositoryTests(unittest.TestCase):
    def _build_event(
        self,
        *,
        kind: str,
        run_id: str | None,
        payload: dict[str, object],
        minutes_ago: int,
    ):
        from ai_infra_fund_core.audit.experiment_events import build_event

        occurred_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc) - timedelta(
            minutes=minutes_ago
        )
        return build_event(
            kind=kind,
            run_id=run_id,
            payload=payload,
            occurred_at=occurred_at,
        )

    def test_record_persists_event_payload_as_json(self) -> None:
        from ai_infra_fund_api.repositories.experiment_events import (
            ExperimentEventRepository,
        )

        connection = FakeConnection()
        repository = ExperimentEventRepository(connection)
        event = self._build_event(
            kind="signal_computed",
            run_id="run-demo-001",
            payload={"ticker": "NVDA", "score": "0.74"},
            minutes_ago=10,
        )

        repository.record(event)

        self.assertIn(event.event_id, connection.rows)
        stored = connection.rows[event.event_id]
        self.assertEqual("signal_computed", stored["kind"])
        self.assertEqual("run-demo-001", stored["run_id"])
        # payload should round-trip as JSON-serializable
        import json

        decoded = json.loads(stored["payload"])
        self.assertEqual({"score": "0.74", "ticker": "NVDA"}, decoded)

    def test_list_recent_returns_events_in_descending_order(self) -> None:
        from ai_infra_fund_api.repositories.experiment_events import (
            ExperimentEventRepository,
        )

        connection = FakeConnection()
        repository = ExperimentEventRepository(connection)
        first = self._build_event(
            kind="signal_computed",
            run_id="run-demo-001",
            payload={"i": 1},
            minutes_ago=30,
        )
        second = self._build_event(
            kind="weights_generated",
            run_id="run-demo-001",
            payload={"i": 2},
            minutes_ago=20,
        )
        third = self._build_event(
            kind="recommendation_issued",
            run_id="run-demo-001",
            payload={"i": 3},
            minutes_ago=10,
        )
        for event in (first, second, third):
            repository.record(event)

        rows = repository.list_recent(limit=10)

        self.assertEqual(
            ["recommendation_issued", "weights_generated", "signal_computed"],
            [row["kind"] for row in rows],
        )

    def test_list_for_run_returns_only_matching_run_id(self) -> None:
        from ai_infra_fund_api.repositories.experiment_events import (
            ExperimentEventRepository,
        )

        connection = FakeConnection()
        repository = ExperimentEventRepository(connection)
        a = self._build_event(
            kind="signal_computed",
            run_id="run-A",
            payload={"i": 1},
            minutes_ago=10,
        )
        b = self._build_event(
            kind="signal_computed",
            run_id="run-B",
            payload={"i": 2},
            minutes_ago=10,
        )
        for event in (a, b):
            repository.record(event)

        rows = repository.list_for_run("run-A")

        self.assertEqual(1, len(rows))
        self.assertEqual("run-A", rows[0]["run_id"])


if __name__ == "__main__":
    unittest.main()
