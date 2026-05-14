from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.evaluation.costs import (  # noqa: E402
    CapacityAssumptions,
    TransactionCostAssumptions,
    estimate_transaction_cost,
    validate_capacity,
)


class Phase7TransactionCostTests(unittest.TestCase):
    def test_estimates_spread_slippage_fees_and_total_cost(self) -> None:
        estimate = estimate_transaction_cost(
            ticker="nvda",
            quantity=Decimal("10"),
            price=Decimal("250"),
            assumptions=TransactionCostAssumptions(
                spread_bps=Decimal("8"),
                slippage_bps=Decimal("12"),
                fee_per_trade=Decimal("1.25"),
                fee_rate_bps=Decimal("1.5"),
            ),
        )

        self.assertEqual("NVDA", estimate.ticker)
        self.assertEqual(Decimal("2500.000000"), estimate.notional)
        self.assertEqual(Decimal("2.000000"), estimate.spread_cost)
        self.assertEqual(Decimal("3.000000"), estimate.slippage_cost)
        self.assertEqual(Decimal("1.625000"), estimate.fees)
        self.assertEqual(Decimal("6.625000"), estimate.total_cost)
        self.assertEqual(Decimal("26.500000"), estimate.cost_bps)

    def test_transaction_cost_model_rejects_invalid_financial_inputs(self) -> None:
        with self.assertRaises(ValueError):
            TransactionCostAssumptions(spread_bps=Decimal("-1"))

        with self.assertRaises(ValueError):
            estimate_transaction_cost(
                ticker="NVDA",
                quantity=Decimal("0"),
                price=Decimal("250"),
                assumptions=TransactionCostAssumptions(),
            )


class Phase7CapacityTests(unittest.TestCase):
    def test_capacity_model_accepts_order_within_participation_limit(self) -> None:
        result = validate_capacity(
            ticker="msft",
            quantity=Decimal("50000"),
            price=Decimal("100"),
            assumptions=CapacityAssumptions(
                average_daily_volume=Decimal("1000000"),
                max_participation_rate=Decimal("0.10"),
                minimum_average_daily_volume=Decimal("250000"),
            ),
        )

        self.assertTrue(result.passed)
        self.assertEqual("MSFT", result.ticker)
        self.assertEqual(Decimal("0.050000"), result.participation_rate)
        self.assertEqual(Decimal("100000.000000"), result.allowed_quantity)
        self.assertEqual(Decimal("5000000.000000"), result.order_notional)
        self.assertEqual((), result.violation_codes)

    def test_capacity_model_rejects_excessive_participation(self) -> None:
        result = validate_capacity(
            ticker="SMCI",
            quantity=Decimal("150000"),
            price=Decimal("100"),
            assumptions=CapacityAssumptions(
                average_daily_volume=Decimal("1000000"),
                max_participation_rate=Decimal("0.10"),
                minimum_average_daily_volume=Decimal("250000"),
            ),
        )

        self.assertFalse(result.passed)
        self.assertEqual(Decimal("0.150000"), result.participation_rate)
        self.assertIn("max_participation_rate", result.violation_codes)

    def test_capacity_model_rejects_insufficient_liquidity(self) -> None:
        result = validate_capacity(
            ticker="BBAI",
            quantity=Decimal("5000"),
            price=Decimal("20"),
            assumptions=CapacityAssumptions(
                average_daily_volume=Decimal("100000"),
                max_participation_rate=Decimal("0.10"),
                minimum_average_daily_volume=Decimal("250000"),
            ),
        )

        self.assertFalse(result.passed)
        self.assertIn("minimum_average_daily_volume", result.violation_codes)

    def test_evaluation_modules_do_not_import_model_sdks_or_execution_surface(self) -> None:
        forbidden = (
            "from azure",
            "import azure",
            "from openai",
            "import openai",
            "from anthropic",
            "import anthropic",
            "broker_client",
            "place_order",
            "submit_order",
            "order_execution",
            "live_order",
        )
        offenders: list[str] = []
        for path in (CORE_SRC / "ai_infra_fund_core" / "evaluation").glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                if pattern in text:
                    offenders.append(f"{path.relative_to(ROOT)} contains {pattern}")

        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
