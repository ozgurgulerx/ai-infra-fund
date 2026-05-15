from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
for path in (CORE_SRC,):
    sys.path.insert(0, str(path))


class ExperimentEventsCoreTests(unittest.TestCase):
    def test_event_kinds_are_a_closed_tuple(self) -> None:
        from ai_infra_fund_core.audit.experiment_events import EVENT_KINDS

        self.assertEqual(
            (
                "signal_computed",
                "weights_generated",
                "recommendation_issued",
                "backtest_started",
                "backtest_completed",
                "shadow_comparison_recorded",
                "price_disagreement",
            ),
            EVENT_KINDS,
        )

    def test_build_event_produces_deterministic_event_id(self) -> None:
        from ai_infra_fund_core.audit.experiment_events import build_event

        occurred_at = datetime(2026, 4, 1, 12, 30, 45, tzinfo=timezone.utc)
        payload = {"ticker": "NVDA", "score": "0.7421"}

        event_a = build_event(
            kind="signal_computed",
            run_id="run-demo-001",
            payload=payload,
            occurred_at=occurred_at,
        )
        event_b = build_event(
            kind="signal_computed",
            run_id="run-demo-001",
            payload=payload,
            occurred_at=occurred_at,
        )

        self.assertEqual(event_a.event_id, event_b.event_id)
        self.assertTrue(event_a.event_id.startswith("audit-evt-"))
        self.assertEqual("signal_computed", event_a.kind)
        self.assertEqual("run-demo-001", event_a.run_id)
        self.assertEqual("info", event_a.severity)
        self.assertEqual(payload, event_a.payload)
        self.assertEqual(occurred_at, event_a.occurred_at)

    def test_build_event_rejects_unknown_kinds(self) -> None:
        from ai_infra_fund_core.audit.experiment_events import build_event

        with self.assertRaises(ValueError):
            build_event(
                kind="not_a_real_kind",
                run_id="run-demo-001",
                payload={},
                occurred_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
            )

    def test_build_event_rejects_naive_datetime(self) -> None:
        from ai_infra_fund_core.audit.experiment_events import build_event

        with self.assertRaises(ValueError):
            build_event(
                kind="signal_computed",
                run_id="run-demo-001",
                payload={},
                occurred_at=datetime(2026, 4, 1, 12, 0, 0),
            )

    def test_build_event_supports_optional_severity(self) -> None:
        from ai_infra_fund_core.audit.experiment_events import build_event

        occurred_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
        event = build_event(
            kind="backtest_completed",
            run_id="run-bt-001",
            payload={"status": "succeeded"},
            occurred_at=occurred_at,
            severity="warn",
        )

        self.assertEqual("warn", event.severity)

    def test_event_id_differs_when_payload_differs(self) -> None:
        from ai_infra_fund_core.audit.experiment_events import build_event

        occurred_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
        first = build_event(
            kind="signal_computed",
            run_id="run-demo-001",
            payload={"ticker": "NVDA"},
            occurred_at=occurred_at,
        )
        second = build_event(
            kind="signal_computed",
            run_id="run-demo-001",
            payload={"ticker": "AMD"},
            occurred_at=occurred_at,
        )

        self.assertNotEqual(first.event_id, second.event_id)

    def test_event_id_differs_when_occurred_at_differs(self) -> None:
        from ai_infra_fund_core.audit.experiment_events import build_event

        payload = {"ticker": "NVDA"}
        first = build_event(
            kind="signal_computed",
            run_id="run-demo-001",
            payload=payload,
            occurred_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        )
        second = build_event(
            kind="signal_computed",
            run_id="run-demo-001",
            payload=payload,
            occurred_at=datetime(2026, 4, 2, tzinfo=timezone.utc),
        )

        self.assertNotEqual(first.event_id, second.event_id)


if __name__ == "__main__":
    unittest.main()
