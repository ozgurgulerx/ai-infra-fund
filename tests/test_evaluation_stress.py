from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.evaluation.stress import MonteCarloStressResult, run_monte_carlo_stress  # noqa: E402


class Phase7MonteCarloStressTests(unittest.TestCase):
    def test_monte_carlo_stress_is_deterministic_for_seed(self) -> None:
        returns = (Decimal("0.02"), Decimal("-0.01"), Decimal("0.03"), Decimal("-0.02"))

        first = run_monte_carlo_stress(
            returns=returns,
            simulations=5,
            horizon_periods=4,
            seed=7,
        )
        second = run_monte_carlo_stress(
            returns=returns,
            simulations=5,
            horizon_periods=4,
            seed=7,
        )

        self.assertIsInstance(first, MonteCarloStressResult)
        self.assertEqual(first, second)
        self.assertEqual(7, first.seed)
        self.assertEqual(5, first.simulations)
        self.assertEqual(4, first.horizon_periods)
        self.assertEqual(
            (
                Decimal("0.019292"),
                Decimal("0.093044"),
                Decimal("0.009396"),
                Decimal("0.009396"),
                Decimal("0.009396"),
            ),
            first.terminal_returns,
        )
        self.assertEqual(
            (
                Decimal("0.029800"),
                Decimal("0.000000"),
                Decimal("0.020000"),
                Decimal("0.020000"),
                Decimal("0.020000"),
            ),
            first.max_drawdowns,
        )

    def test_monte_carlo_stress_reports_return_and_drawdown_distribution(self) -> None:
        result = run_monte_carlo_stress(
            returns=(Decimal("0.02"), Decimal("-0.01"), Decimal("0.03"), Decimal("-0.02")),
            simulations=5,
            horizon_periods=4,
            seed=7,
        )

        self.assertEqual(Decimal("0.028105"), result.mean_return)
        self.assertEqual(Decimal("0.009396"), result.median_return)
        self.assertEqual(Decimal("0.009396"), result.p05_return)
        self.assertEqual(Decimal("0.093044"), result.p95_return)
        self.assertEqual(Decimal("0.009396"), result.worst_return)
        self.assertEqual(Decimal("0.093044"), result.best_return)
        self.assertEqual(Decimal("0.017960"), result.mean_max_drawdown)
        self.assertEqual(Decimal("0.020000"), result.median_max_drawdown)
        self.assertEqual(Decimal("0.029800"), result.p95_max_drawdown)
        self.assertEqual(Decimal("0.029800"), result.worst_max_drawdown)

    def test_monte_carlo_stress_rejects_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            run_monte_carlo_stress(returns=(), simulations=5, horizon_periods=4, seed=1)

        with self.assertRaises(ValueError):
            run_monte_carlo_stress(returns=(Decimal("0.01"),), simulations=0, horizon_periods=4, seed=1)

        with self.assertRaises(ValueError):
            run_monte_carlo_stress(returns=(Decimal("-1.01"),), simulations=5, horizon_periods=4, seed=1)


if __name__ == "__main__":
    unittest.main()
