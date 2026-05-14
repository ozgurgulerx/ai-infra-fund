from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.signals.formulas import FORMULA_VERSIONS  # noqa: E402
from ai_infra_fund_core.signals.valuation import (  # noqa: E402
    ValuationInputs,
    compute_valuation_snapshot,
)


AS_OF = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class ValuationSignalTests(unittest.TestCase):
    def test_valuation_snapshot_combines_dcf_owner_multiple_and_residual_income(self) -> None:
        snapshot = compute_valuation_snapshot(
            ticker="nvda",
            as_of=AS_OF,
            inputs=ValuationInputs(
                market_cap=Decimal("1000"),
                free_cash_flow=Decimal("100"),
                growth_rate=Decimal("0"),
                discount_rate=Decimal("0.10"),
                terminal_growth_rate=Decimal("0"),
                net_income=Decimal("100"),
                depreciation_and_amortization=Decimal("0"),
                capex=Decimal("0"),
                working_capital_change=Decimal("0"),
                ebitda=Decimal("100"),
                peer_ev_ebitda_multiple=Decimal("10"),
                net_debt=Decimal("0"),
                book_value=Decimal("1000"),
                cost_of_equity=Decimal("0.10"),
                return_on_equity=Decimal("0.10"),
                margin_of_safety=Decimal("0"),
            ),
        )

        self.assertEqual("NVDA", snapshot.ticker)
        self.assertEqual(Decimal("1000"), snapshot.dcf_value)
        self.assertEqual(Decimal("1000"), snapshot.owner_earnings_value)
        self.assertEqual(Decimal("1000"), snapshot.ev_ebitda_value)
        self.assertEqual(Decimal("1000"), snapshot.residual_income_value)
        self.assertEqual(Decimal("1000"), snapshot.weighted_intrinsic_value)
        self.assertEqual(Decimal("0"), snapshot.valuation_gap)
        self.assertEqual(Decimal("0.5"), snapshot.valuation_score)
        self.assertEqual("fairly_valued", snapshot.valuation_label)
        self.assertEqual("v1", snapshot.formula_version)
        self.assertEqual("v1", FORMULA_VERSIONS["valuation_score"])

    def test_valuation_score_moves_with_margin_of_safety(self) -> None:
        undervalued = compute_valuation_snapshot(
            ticker="amd",
            as_of=AS_OF,
            inputs=valuation_inputs(market_cap=Decimal("800")),
        )
        overvalued = compute_valuation_snapshot(
            ticker="amd",
            as_of=AS_OF,
            inputs=valuation_inputs(market_cap=Decimal("1250")),
        )

        self.assertEqual(Decimal("0.25"), undervalued.valuation_gap)
        self.assertEqual(Decimal("0.75"), undervalued.valuation_score)
        self.assertEqual("undervalued", undervalued.valuation_label)
        self.assertEqual(Decimal("-0.2"), overvalued.valuation_gap)
        self.assertEqual(Decimal("0.3"), overvalued.valuation_score)
        self.assertEqual("overvalued", overvalued.valuation_label)

    def test_rejects_invalid_terminal_assumptions_before_scoring(self) -> None:
        with self.assertRaisesRegex(ValueError, "discount_rate must exceed terminal_growth_rate"):
            compute_valuation_snapshot(
                ticker="msft",
                as_of=AS_OF,
                inputs=valuation_inputs(discount_rate=Decimal("0.03"), terminal_growth_rate=Decimal("0.03")),
            )


def valuation_inputs(**overrides: Decimal) -> ValuationInputs:
    values = {
        "market_cap": Decimal("1000"),
        "free_cash_flow": Decimal("100"),
        "growth_rate": Decimal("0"),
        "discount_rate": Decimal("0.10"),
        "terminal_growth_rate": Decimal("0"),
        "net_income": Decimal("100"),
        "depreciation_and_amortization": Decimal("0"),
        "capex": Decimal("0"),
        "working_capital_change": Decimal("0"),
        "ebitda": Decimal("100"),
        "peer_ev_ebitda_multiple": Decimal("10"),
        "net_debt": Decimal("0"),
        "book_value": Decimal("1000"),
        "cost_of_equity": Decimal("0.10"),
        "return_on_equity": Decimal("0.10"),
        "margin_of_safety": Decimal("0"),
    }
    values.update(overrides)
    return ValuationInputs(**values)


if __name__ == "__main__":
    unittest.main()
