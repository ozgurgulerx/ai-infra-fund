from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.common import TradeSide, TradeStatus  # noqa: E402
from ai_infra_fund_core.contracts.portfolio import TradeEntry  # noqa: E402
from ai_infra_fund_core.contracts.signals import SignalBundle, TargetWeights  # noqa: E402
from ai_infra_fund_core.portfolio.constraints import (  # noqa: E402
    PortfolioConstraints,
    validate_portfolio_constraints,
)
from ai_infra_fund_core.portfolio.target_weights import generate_target_weights  # noqa: E402
from ai_infra_fund_core.portfolio.trade_comparison import compare_trade_to_target  # noqa: E402


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class Phase4PortfolioConstraintTests(unittest.TestCase):
    def test_validates_max_single_name_weight_constraint(self) -> None:
        result = validate_portfolio_constraints(
            weights={"NVDA": Decimal("0.45"), "MSFT": Decimal("0.30")},
            cash_weight=Decimal("0.25"),
            constraints=constraints(max_single_name_weight=Decimal("0.40")),
        )

        self.assertFalse(result.passed)
        self.assertIn("max_single_name_weight", result.violation_codes)

    def test_validates_max_theme_exposure_constraint(self) -> None:
        result = validate_portfolio_constraints(
            weights={"NVDA": Decimal("0.30"), "SMCI": Decimal("0.25"), "MSFT": Decimal("0.20")},
            cash_weight=Decimal("0.25"),
            constraints=constraints(max_theme_exposure=Decimal("0.50")),
            theme_by_ticker={"NVDA": "ai_hardware", "SMCI": "ai_hardware", "MSFT": "cloud"},
        )

        self.assertFalse(result.passed)
        self.assertIn("max_theme_exposure", result.violation_codes)

    def test_validates_cash_floor_constraint(self) -> None:
        result = validate_portfolio_constraints(
            weights={"NVDA": Decimal("0.50"), "MSFT": Decimal("0.45")},
            cash_weight=Decimal("0.05"),
            constraints=constraints(cash_floor=Decimal("0.10")),
        )

        self.assertFalse(result.passed)
        self.assertIn("cash_floor", result.violation_codes)

    def test_validates_liquidity_floor_constraint(self) -> None:
        result = validate_portfolio_constraints(
            weights={"NVDA": Decimal("0.40"), "SMCI": Decimal("0.20"), "MSFT": Decimal("0.30")},
            cash_weight=Decimal("0.10"),
            constraints=constraints(liquidity_floor=Decimal("0.50")),
            liquidity_by_ticker={"NVDA": Decimal("0.80"), "SMCI": Decimal("0.30"), "MSFT": Decimal("0.90")},
        )

        self.assertFalse(result.passed)
        self.assertIn("liquidity_floor", result.violation_codes)

    def test_validates_turnover_cap_constraint(self) -> None:
        result = validate_portfolio_constraints(
            weights={"NVDA": Decimal("0.40"), "MSFT": Decimal("0.45")},
            cash_weight=Decimal("0.15"),
            constraints=constraints(turnover_cap=Decimal("0.20")),
            current_weights={"NVDA": Decimal("0.10"), "MSFT": Decimal("0.10")},
            current_cash_weight=Decimal("0.80"),
        )

        self.assertFalse(result.passed)
        self.assertEqual(Decimal("0.65"), result.turnover)
        self.assertIn("turnover_cap", result.violation_codes)

    def test_validates_target_weights_sum(self) -> None:
        result = validate_portfolio_constraints(
            weights={"NVDA": Decimal("0.30"), "MSFT": Decimal("0.30")},
            cash_weight=Decimal("0.20"),
            constraints=constraints(),
        )

        self.assertFalse(result.passed)
        self.assertIn("target_weights_sum", result.violation_codes)


class Phase4TargetWeightGenerationTests(unittest.TestCase):
    def test_generates_reproducible_validated_target_weights(self) -> None:
        input_signals = (
            signal("signal-nvda", "NVDA", Decimal("0.90"), Decimal("0.80"), Decimal("0.70"), Decimal("0.20")),
            signal("signal-msft", "MSFT", Decimal("0.70"), Decimal("0.60"), Decimal("0.50"), Decimal("0.10")),
            signal("signal-smci", "SMCI", Decimal("0.60"), Decimal("0.40"), Decimal("0.40"), Decimal("0.50")),
        )
        engine_constraints = constraints(
            max_single_name_weight=Decimal("0.40"),
            max_theme_exposure=Decimal("0.50"),
            cash_floor=Decimal("0.10"),
            liquidity_floor=Decimal("0.50"),
            turnover_cap=Decimal("1.00"),
        )

        first = generate_target_weights(
            portfolio_id="portfolio-1",
            signals=input_signals,
            constraints=engine_constraints,
            as_of=NOW,
            created_at=NOW,
            theme_by_ticker={"NVDA": "ai_hardware", "MSFT": "cloud", "SMCI": "ai_hardware"},
            liquidity_by_ticker={"NVDA": Decimal("0.90"), "MSFT": Decimal("0.85"), "SMCI": Decimal("0.40")},
        )
        second = generate_target_weights(
            portfolio_id="portfolio-1",
            signals=input_signals,
            constraints=engine_constraints,
            as_of=NOW,
            created_at=NOW,
            theme_by_ticker={"NVDA": "ai_hardware", "MSFT": "cloud", "SMCI": "ai_hardware"},
            liquidity_by_ticker={"NVDA": Decimal("0.90"), "MSFT": Decimal("0.85"), "SMCI": Decimal("0.40")},
        )

        self.assertIsInstance(first, TargetWeights)
        self.assertEqual(first, second)
        self.assertEqual("validated", first.validation_status)
        self.assertEqual(("signal-nvda", "signal-msft"), first.source_signal_bundle_ids)
        self.assertEqual(Decimal("1.00"), first.cash_weight + sum(first.weights.values(), Decimal("0")))
        self.assertLessEqual(first.weights["NVDA"], Decimal("0.40"))
        self.assertNotIn("SMCI", first.weights)
        self.assertEqual("deterministic_portfolio_engine.v1", first.generated_by)

    def test_target_generation_respects_turnover_cap(self) -> None:
        generated = generate_target_weights(
            portfolio_id="portfolio-1",
            signals=(signal("signal-nvda", "NVDA", Decimal("0.90"), Decimal("0.80"), Decimal("0.70"), Decimal("0.20")),),
            constraints=constraints(
                max_single_name_weight=Decimal("0.80"),
                cash_floor=Decimal("0.10"),
                turnover_cap=Decimal("0.10"),
            ),
            as_of=NOW,
            created_at=NOW,
            current_weights={"NVDA": Decimal("0.10")},
            current_cash_weight=Decimal("0.90"),
        )

        validation = validate_portfolio_constraints(
            weights=generated.weights,
            cash_weight=generated.cash_weight,
            constraints=constraints(turnover_cap=Decimal("0.10")),
            current_weights={"NVDA": Decimal("0.10")},
            current_cash_weight=Decimal("0.90"),
        )
        self.assertTrue(validation.passed)
        self.assertLessEqual(validation.turnover, Decimal("0.10"))

    def test_target_weights_reject_raw_llm_or_model_output(self) -> None:
        with self.assertRaises(ValueError):
            TargetWeights.from_raw_llm_output({"NVDA": 0.50})

        with self.assertRaises(ValueError):
            TargetWeights(
                target_weights_id="target-weights-llm",
                as_of=NOW,
                portfolio_id="portfolio-1",
                cash_weight=Decimal("0.50"),
                weights={"NVDA": Decimal("0.50")},
                constraints={"cash_floor": "0.10"},
                source_signal_bundle_ids=("signal-nvda",),
                generated_by="model_output",
                validation_status="validated",
                created_at=NOW,
            )


class Phase4TradeComparisonTests(unittest.TestCase):
    def test_compares_manual_trade_against_target_weights(self) -> None:
        targets = TargetWeights(
            target_weights_id="target-weights-1",
            as_of=NOW,
            portfolio_id="portfolio-1",
            cash_weight=Decimal("0.60"),
            weights={"NVDA": Decimal("0.40")},
            constraints={"cash_floor": "0.10"},
            source_signal_bundle_ids=("signal-nvda",),
            generated_by="deterministic_portfolio_engine.v1",
            validation_status="validated",
            created_at=NOW,
        )

        aligned = compare_trade_to_target(
            trade=trade("NVDA", TradeSide.BUY, quantity=Decimal("10"), price=Decimal("100")),
            target_weights=targets,
            current_weights={"NVDA": Decimal("0.20")},
            portfolio_market_value=Decimal("10000"),
        )
        oversized = compare_trade_to_target(
            trade=trade("NVDA", TradeSide.BUY, quantity=Decimal("30"), price=Decimal("100")),
            target_weights=targets,
            current_weights={"NVDA": Decimal("0.20")},
            portfolio_market_value=Decimal("10000"),
        )

        self.assertTrue(aligned.is_directionally_aligned)
        self.assertFalse(aligned.exceeds_target)
        self.assertFalse(oversized.is_directionally_aligned)
        self.assertTrue(oversized.exceeds_target)

    def test_signal_and_portfolio_modules_do_not_import_model_clients(self) -> None:
        forbidden = (
            "from azure",
            "import azure",
            "from openai",
            "import openai",
            "from anthropic",
            "import anthropic",
            "model_routing",
        )
        offenders: list[str] = []
        for package_root in (
            CORE_SRC / "ai_infra_fund_core" / "signals",
            CORE_SRC / "ai_infra_fund_core" / "portfolio",
        ):
            for path in package_root.glob("*.py"):
                text = path.read_text(encoding="utf-8")
                for pattern in forbidden:
                    if pattern in text:
                        offenders.append(f"{path.relative_to(ROOT)} contains {pattern}")

        self.assertEqual([], offenders)


def constraints(**overrides: object) -> PortfolioConstraints:
    data = {
        "max_single_name_weight": Decimal("0.40"),
        "max_theme_exposure": Decimal("0.60"),
        "cash_floor": Decimal("0.10"),
        "liquidity_floor": Decimal("0.20"),
        "turnover_cap": Decimal("1.00"),
    }
    data.update(overrides)
    return PortfolioConstraints(**data)


def signal(
    signal_bundle_id: str,
    ticker: str,
    strategic: Decimal,
    tactical: Decimal,
    forward: Decimal,
    risk: Decimal,
) -> SignalBundle:
    return SignalBundle(
        signal_bundle_id=signal_bundle_id,
        ticker=ticker,
        as_of=NOW,
        strategic_thesis_score=strategic,
        tactical_technical_score=tactical,
        forward_indicator_score=forward,
        portfolio_risk_score=risk,
        formula_versions={"test": "v1"},
        input_snapshot_hash="a" * 64,
        created_at=NOW,
    )


def trade(ticker: str, side: TradeSide, *, quantity: Decimal, price: Decimal) -> TradeEntry:
    return TradeEntry(
        trade_id=f"trade-{ticker.lower()}",
        ticker=ticker,
        side=side,
        quantity=quantity,
        price=price,
        fees=Decimal("0"),
        trade_date=date(2026, 5, 14),
        settlement_date=None,
        account_label="manual",
        status=TradeStatus.INTENDED,
        source="manual",
        notes="local journal only",
        created_at=NOW,
    )


if __name__ == "__main__":
    unittest.main()
