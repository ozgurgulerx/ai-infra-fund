from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.signals import SignalBundle  # noqa: E402
from ai_infra_fund_core.signals.formulas import FORMULA_VERSIONS  # noqa: E402
from ai_infra_fund_core.signals.scoring import (  # noqa: E402
    ForwardIndicatorInputs,
    PortfolioRiskInputs,
    SignalInputs,
    StrategicThesisInputs,
    TacticalTechnicalInputs,
    compute_signal_bundle,
    score_forward_indicator,
    score_portfolio_risk,
    score_strategic_thesis,
    score_tactical_technical,
)


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class Phase4SignalScoringTests(unittest.TestCase):
    def test_strategic_thesis_score_formula_includes_staleness_penalty(self) -> None:
        fresh_score = score_strategic_thesis(
            StrategicThesisInputs(
                evidence_confidence=Decimal("0.8"),
                thesis_alignment=Decimal("0.6"),
                market_importance=Decimal("1.0"),
                staleness_days=30,
            )
        )
        stale_score = score_strategic_thesis(
            StrategicThesisInputs(
                evidence_confidence=Decimal("0.8"),
                thesis_alignment=Decimal("0.6"),
                market_importance=Decimal("1.0"),
                staleness_days=360,
            )
        )

        self.assertEqual(Decimal("0.77"), fresh_score)
        self.assertEqual(Decimal("0.462"), stale_score)
        self.assertLess(stale_score, fresh_score)

    def test_tactical_technical_score_formula(self) -> None:
        score = score_tactical_technical(
            TacticalTechnicalInputs(
                trend_strength=Decimal("0.8"),
                momentum=Decimal("0.6"),
                relative_strength=Decimal("0.4"),
                volume_confirmation=Decimal("1.0"),
            )
        )

        self.assertEqual(Decimal("0.69"), score)

    def test_forward_indicator_score_formula(self) -> None:
        score = score_forward_indicator(
            ForwardIndicatorInputs(
                futures_pressure=Decimal("0.7"),
                capex_revision=Decimal("0.8"),
                supply_chain_pressure=Decimal("0.6"),
                power_availability=Decimal("0.5"),
            )
        )

        self.assertEqual(Decimal("0.67"), score)

    def test_portfolio_risk_score_formula(self) -> None:
        score = score_portfolio_risk(
            PortfolioRiskInputs(
                concentration_risk=Decimal("0.8"),
                theme_exposure_risk=Decimal("0.7"),
                liquidity_risk=Decimal("0.2"),
                drawdown_risk=Decimal("0.5"),
            )
        )

        self.assertEqual(Decimal("0.59"), score)

    def test_formula_versions_are_present_for_all_scores(self) -> None:
        self.assertEqual(
            {
                "strategic_thesis_score",
                "sentiment_score",
                "tactical_technical_score",
                "fundamental_score",
                "valuation_score",
                "forward_indicator_score",
                "portfolio_risk_score",
                "combined_attractiveness_score",
                "target_weight_generation",
                "portfolio_constraints",
            },
            set(FORMULA_VERSIONS),
        )
        for version in FORMULA_VERSIONS.values():
            self.assertRegex(version, r"^v[0-9]+$")

    def test_signal_bundle_propagates_formula_versions_and_input_hash(self) -> None:
        bundle = compute_signal_bundle(
            signal_bundle_id="signal-bundle-1",
            ticker="nvda",
            as_of=NOW,
            created_at=NOW,
            input_snapshot_hash="a" * 64,
            inputs=SignalInputs(
                strategic=StrategicThesisInputs(
                    evidence_confidence=Decimal("0.8"),
                    thesis_alignment=Decimal("0.6"),
                    market_importance=Decimal("1.0"),
                    staleness_days=30,
                ),
                tactical=TacticalTechnicalInputs(
                    trend_strength=Decimal("0.8"),
                    momentum=Decimal("0.6"),
                    relative_strength=Decimal("0.4"),
                    volume_confirmation=Decimal("1.0"),
                ),
                forward=ForwardIndicatorInputs(
                    futures_pressure=Decimal("0.7"),
                    capex_revision=Decimal("0.8"),
                    supply_chain_pressure=Decimal("0.6"),
                    power_availability=Decimal("0.5"),
                ),
                risk=PortfolioRiskInputs(
                    concentration_risk=Decimal("0.8"),
                    theme_exposure_risk=Decimal("0.7"),
                    liquidity_risk=Decimal("0.2"),
                    drawdown_risk=Decimal("0.5"),
                ),
            ),
        )

        self.assertIsInstance(bundle, SignalBundle)
        self.assertEqual("NVDA", bundle.ticker)
        self.assertEqual("a" * 64, bundle.input_snapshot_hash)
        self.assertEqual(FORMULA_VERSIONS, bundle.formula_versions)
        self.assertEqual(Decimal("0.77"), bundle.strategic_thesis_score)
        self.assertEqual(Decimal("0.69"), bundle.tactical_technical_score)
        self.assertEqual(Decimal("0.67"), bundle.forward_indicator_score)
        self.assertEqual(Decimal("0.59"), bundle.portfolio_risk_score)

    def test_compute_signal_bundle_emits_event_when_sink_provided(self) -> None:
        emitted: list[object] = []

        bundle = compute_signal_bundle(
            signal_bundle_id="signal-bundle-1",
            ticker="NVDA",
            as_of=NOW,
            created_at=NOW,
            input_snapshot_hash="b" * 64,
            inputs=SignalInputs(
                strategic=StrategicThesisInputs(
                    evidence_confidence=Decimal("0.8"),
                    thesis_alignment=Decimal("0.6"),
                    market_importance=Decimal("1.0"),
                    staleness_days=30,
                ),
                tactical=TacticalTechnicalInputs(
                    trend_strength=Decimal("0.8"),
                    momentum=Decimal("0.6"),
                    relative_strength=Decimal("0.4"),
                    volume_confirmation=Decimal("1.0"),
                ),
                forward=ForwardIndicatorInputs(
                    futures_pressure=Decimal("0.7"),
                    capex_revision=Decimal("0.8"),
                    supply_chain_pressure=Decimal("0.6"),
                    power_availability=Decimal("0.5"),
                ),
                risk=PortfolioRiskInputs(
                    concentration_risk=Decimal("0.8"),
                    theme_exposure_risk=Decimal("0.7"),
                    liquidity_risk=Decimal("0.2"),
                    drawdown_risk=Decimal("0.5"),
                ),
            ),
            event_sink=emitted.append,
            run_id="run-signal-001",
        )

        self.assertIsInstance(bundle, SignalBundle)
        self.assertEqual(1, len(emitted))
        event = emitted[0]
        self.assertEqual("signal_computed", event.kind)  # type: ignore[attr-defined]
        self.assertEqual("run-signal-001", event.run_id)  # type: ignore[attr-defined]

    def test_compute_signal_bundle_default_behavior_unchanged_without_sink(
        self,
    ) -> None:
        inputs = SignalInputs(
            strategic=StrategicThesisInputs(
                evidence_confidence=Decimal("0.8"),
                thesis_alignment=Decimal("0.6"),
                market_importance=Decimal("1.0"),
                staleness_days=30,
            ),
            tactical=TacticalTechnicalInputs(
                trend_strength=Decimal("0.8"),
                momentum=Decimal("0.6"),
                relative_strength=Decimal("0.4"),
                volume_confirmation=Decimal("1.0"),
            ),
            forward=ForwardIndicatorInputs(
                futures_pressure=Decimal("0.7"),
                capex_revision=Decimal("0.8"),
                supply_chain_pressure=Decimal("0.6"),
                power_availability=Decimal("0.5"),
            ),
            risk=PortfolioRiskInputs(
                concentration_risk=Decimal("0.8"),
                theme_exposure_risk=Decimal("0.7"),
                liquidity_risk=Decimal("0.2"),
                drawdown_risk=Decimal("0.5"),
            ),
        )

        first = compute_signal_bundle(
            signal_bundle_id="signal-bundle-1",
            ticker="NVDA",
            as_of=NOW,
            created_at=NOW,
            input_snapshot_hash="c" * 64,
            inputs=inputs,
        )
        second = compute_signal_bundle(
            signal_bundle_id="signal-bundle-1",
            ticker="NVDA",
            as_of=NOW,
            created_at=NOW,
            input_snapshot_hash="c" * 64,
            inputs=inputs,
            event_sink=lambda _event: None,
            run_id="run-signal-001",
        )

        self.assertEqual(first.signal_bundle_id, second.signal_bundle_id)
        self.assertEqual(first.strategic_thesis_score, second.strategic_thesis_score)

    def test_score_bounds_and_invalid_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            score_tactical_technical(
                TacticalTechnicalInputs(
                    trend_strength=Decimal("1.1"),
                    momentum=Decimal("0.6"),
                    relative_strength=Decimal("0.4"),
                    volume_confirmation=Decimal("1.0"),
                )
            )

        with self.assertRaises(ValueError):
            score_strategic_thesis(
                StrategicThesisInputs(
                    evidence_confidence=Decimal("0.8"),
                    thesis_alignment=Decimal("0.6"),
                    market_importance=Decimal("1.0"),
                    staleness_days=-1,
                )
            )


if __name__ == "__main__":
    unittest.main()
