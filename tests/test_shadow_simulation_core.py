from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))


from ai_infra_fund_core.contracts.signals import TargetWeights  # noqa: E402


NOW = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)


def _target_weights() -> TargetWeights:
    return TargetWeights(
        target_weights_id="target-weights-test",
        as_of=NOW,
        portfolio_id="portfolio-test",
        cash_weight=Decimal("0.20"),
        weights={"NVDA": Decimal("0.50"), "MSFT": Decimal("0.30")},
        constraints={"cash_floor": "0.10", "formula_version": "v1"},
        source_signal_bundle_ids=("signal-bundle-test",),
        generated_by="deterministic_portfolio_engine.v1",
        validation_status="validated",
        created_at=NOW,
    )


def _price_series() -> dict[str, list[dict[str, object]]]:
    base = NOW - timedelta(days=4)
    return {
        "NVDA": [
            {
                "date": base + timedelta(days=i),
                "available_at": base + timedelta(days=i),
                "price": Decimal("100") + Decimal(i),
            }
            for i in range(5)
        ],
        "MSFT": [
            {
                "date": base + timedelta(days=i),
                "available_at": base + timedelta(days=i),
                "price": Decimal("400") + Decimal(2 * i),
            }
            for i in range(5)
        ],
    }


class ShadowSimulationCoreTests(unittest.TestCase):
    def test_compute_portfolio_drift_returns_expected_rows(self) -> None:
        from ai_infra_fund_core.portfolio.shadow_simulation import (
            compute_portfolio_drift,
        )

        rows = compute_portfolio_drift(
            holdings={"NVDA": Decimal("0.60"), "AMD": Decimal("0.10")},
            target_weights=_target_weights(),
        )

        as_dict = {row.ticker: row for row in rows}
        self.assertIn("NVDA", as_dict)
        self.assertEqual(Decimal("0.60"), as_dict["NVDA"].current_weight)
        self.assertEqual(Decimal("0.50"), as_dict["NVDA"].target_weight)
        self.assertEqual(Decimal("-0.10"), as_dict["NVDA"].drift)
        self.assertIn("MSFT", as_dict)
        self.assertEqual(Decimal("0.00"), as_dict["MSFT"].current_weight)
        self.assertEqual(Decimal("0.30"), as_dict["MSFT"].target_weight)
        self.assertIn("AMD", as_dict)
        self.assertEqual(Decimal("0.00"), as_dict["AMD"].target_weight)

    def test_simulate_shadow_curve_produces_deterministic_values(self) -> None:
        from ai_infra_fund_core.portfolio.shadow_simulation import (
            simulate_shadow_curve,
        )

        curve = simulate_shadow_curve(
            target_weights=_target_weights(),
            price_series=_price_series(),
            as_of=NOW,
        )

        self.assertEqual(5, len(curve.points))
        # First point should equal starting value (1.0 by default).
        self.assertEqual(Decimal("1"), curve.points[0].shadow_value)
        # The series is strictly increasing because both prices rise monotonically.
        for previous, current in zip(curve.points, curve.points[1:]):
            self.assertGreater(current.shadow_value, previous.shadow_value)
        self.assertGreater(curve.metrics["shadow_return"], Decimal("0"))

    def test_simulate_shadow_curve_raises_when_price_point_exceeds_as_of(self) -> None:
        from ai_infra_fund_core.portfolio.shadow_simulation import (
            LookaheadError,
            simulate_shadow_curve,
        )

        prices = _price_series()
        # Push one price's availability beyond as_of -> lookahead.
        prices["NVDA"][-1]["available_at"] = NOW + timedelta(days=1)

        with self.assertRaises(LookaheadError):
            simulate_shadow_curve(
                target_weights=_target_weights(),
                price_series=prices,
                as_of=NOW,
            )

    def test_simulate_shadow_curve_raises_lookahead_for_naive_timestamps(
        self,
    ) -> None:
        from ai_infra_fund_core.portfolio.shadow_simulation import (
            LookaheadError,
            simulate_shadow_curve,
        )

        prices = _price_series()
        # Strip tzinfo on one price's availability stamp.
        naive_available_at = prices["NVDA"][0]["available_at"]
        assert isinstance(naive_available_at, datetime)
        prices["NVDA"][0]["available_at"] = naive_available_at.replace(tzinfo=None)

        with self.assertRaises(LookaheadError):
            simulate_shadow_curve(
                target_weights=_target_weights(),
                price_series=prices,
                as_of=NOW,
            )


if __name__ == "__main__":
    unittest.main()
