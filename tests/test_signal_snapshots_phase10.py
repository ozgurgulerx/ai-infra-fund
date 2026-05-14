from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.signals.fundamental import (  # noqa: E402
    FundamentalPeriodSnapshot,
    compute_fundamental_snapshot,
)
from ai_infra_fund_core.signals.integration import combine_signal_components  # noqa: E402
from ai_infra_fund_core.signals.scoring import (  # noqa: E402
    ForwardIndicatorInputs,
    PortfolioRiskInputs,
    StrategicThesisInputs,
)
from ai_infra_fund_core.signals.sentiment import (  # noqa: E402
    SentimentEvidence,
    compute_sentiment_snapshot,
)
from ai_infra_fund_core.signals.technical import (  # noqa: E402
    MarketPoint,
    compute_technical_snapshot,
)


AS_OF = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class Phase10SentimentSnapshotTests(unittest.TestCase):
    def test_sentiment_snapshot_is_source_weighted_and_keeps_evidence_ids(self) -> None:
        snapshot = compute_sentiment_snapshot(
            ticker="nvda",
            as_of=AS_OF,
            evidence=[
                SentimentEvidence(
                    evidence_id="ev-company",
                    source_type="company_release",
                    direction="positive",
                    confidence=Decimal("0.80"),
                    horizon_days=90,
                ),
                SentimentEvidence(
                    evidence_id="ev-news",
                    source_type="news",
                    direction="negative",
                    confidence=Decimal("0.60"),
                    horizon_days=30,
                ),
                SentimentEvidence(
                    evidence_id="ev-social",
                    source_type="social",
                    direction="positive",
                    confidence=Decimal("0.40"),
                    horizon_days=7,
                ),
            ],
        )

        self.assertEqual("NVDA", snapshot.ticker)
        self.assertEqual("positive", snapshot.direction)
        self.assertEqual(Decimal("0.390"), snapshot.directional_score)
        self.assertEqual(Decimal("0.674"), snapshot.confidence)
        self.assertEqual(65, snapshot.horizon_days)
        self.assertEqual(("ev-company", "ev-news", "ev-social"), snapshot.evidence_ids)
        self.assertEqual(Decimal("0.631"), snapshot.sentiment_score)

    def test_sentiment_snapshot_has_deterministic_neutral_fallback(self) -> None:
        snapshot = compute_sentiment_snapshot(ticker="amd", as_of=AS_OF, evidence=[])

        self.assertEqual("neutral", snapshot.direction)
        self.assertEqual(Decimal("0"), snapshot.directional_score)
        self.assertEqual(Decimal("0"), snapshot.confidence)
        self.assertEqual(30, snapshot.horizon_days)
        self.assertEqual((), snapshot.evidence_ids)
        self.assertEqual(Decimal("0.5"), snapshot.sentiment_score)


class Phase10TechnicalSnapshotTests(unittest.TestCase):
    def test_technical_snapshot_uses_point_in_time_market_data(self) -> None:
        points = [
            MarketPoint(as_of=datetime(2026, 5, day, tzinfo=timezone.utc), close=Decimal(str(close)), volume=Decimal(str(volume)))
            for day, close, volume in (
                (1, 100, 1000),
                (2, 102, 1000),
                (3, 104, 1000),
                (4, 106, 1000),
                (5, 108, 1000),
                (6, 110, 1000),
                (7, 112, 1000),
                (8, 114, 1000),
                (9, 116, 1000),
                (10, 118, 2000),
                (15, 200, 9000),
            )
        ]

        snapshot = compute_technical_snapshot(ticker="nvda", as_of=datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc), points=points)

        self.assertEqual(Decimal("114"), snapshot.short_moving_average)
        self.assertEqual(Decimal("109"), snapshot.long_moving_average)
        self.assertEqual(Decimal("0.093"), snapshot.momentum)
        self.assertEqual(Decimal("0.729"), snapshot.trend_strength)
        self.assertEqual(Decimal("1"), snapshot.rsi_score)
        self.assertEqual(Decimal("0"), snapshot.drawdown)
        self.assertEqual(Decimal("0.909"), snapshot.volume_confirmation)
        self.assertGreater(snapshot.volatility, Decimal("0"))
        self.assertLess(snapshot.volatility, Decimal("0.02"))
        self.assertEqual(Decimal("0.797"), snapshot.tactical_technical_score)


class Phase10FundamentalSnapshotTests(unittest.TestCase):
    def test_fundamental_snapshot_scores_fixture_metrics(self) -> None:
        snapshot = compute_fundamental_snapshot(
            ticker="msft",
            as_of=AS_OF,
            periods=[
                FundamentalPeriodSnapshot(
                    period_end=datetime(2025, 12, 31, tzinfo=timezone.utc),
                    revenue=Decimal("100"),
                    operating_margin=Decimal("0.20"),
                    valuation_multiple=Decimal("30"),
                    guidance_revenue_growth=Decimal("0.04"),
                    capex_to_revenue=Decimal("0.10"),
                    debt_to_equity=Decimal("0.30"),
                    cash_to_debt=Decimal("1.20"),
                    eps_actual=Decimal("2.00"),
                    eps_consensus=Decimal("2.00"),
                ),
                FundamentalPeriodSnapshot(
                    period_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
                    revenue=Decimal("125"),
                    operating_margin=Decimal("0.24"),
                    valuation_multiple=Decimal("45"),
                    guidance_revenue_growth=Decimal("0.12"),
                    capex_to_revenue=Decimal("0.16"),
                    debt_to_equity=Decimal("0.40"),
                    cash_to_debt=Decimal("2.00"),
                    eps_actual=Decimal("2.20"),
                    eps_consensus=Decimal("2.00"),
                ),
            ],
            benchmark_valuation_multiple=Decimal("30"),
        )

        self.assertEqual("MSFT", snapshot.ticker)
        self.assertEqual(Decimal("0.25"), snapshot.revenue_growth)
        self.assertEqual(Decimal("0.04"), snapshot.margin_trend)
        self.assertEqual(Decimal("0.5"), snapshot.valuation_pressure)
        self.assertEqual("positive", snapshot.guidance_direction)
        self.assertEqual(Decimal("0.16"), snapshot.capex_exposure)
        self.assertEqual(Decimal("0.16"), snapshot.balance_sheet_risk)
        self.assertEqual(Decimal("0.1"), snapshot.earnings_surprise)
        self.assertEqual(Decimal("0.856"), snapshot.fundamental_score)


class Phase10SignalIntegrationTests(unittest.TestCase):
    def test_combines_snapshots_and_existing_signal_inputs_into_deterministic_scores(self) -> None:
        sentiment = compute_sentiment_snapshot(
            ticker="nvda",
            as_of=AS_OF,
            evidence=[
                SentimentEvidence(
                    evidence_id="ev-company",
                    source_type="company_release",
                    direction="positive",
                    confidence=Decimal("0.80"),
                    horizon_days=90,
                )
            ],
        )
        technical = compute_technical_snapshot(
            ticker="nvda",
            as_of=datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc),
            points=[
                MarketPoint(as_of=datetime(2026, 5, day, tzinfo=timezone.utc), close=Decimal(str(close)), volume=Decimal("1000"))
                for day, close in enumerate((100, 101, 102, 103, 104, 105, 106, 107, 108, 109), start=1)
            ],
        )
        fundamental = compute_fundamental_snapshot(
            ticker="nvda",
            as_of=AS_OF,
            periods=[
                FundamentalPeriodSnapshot(
                    period_end=datetime(2025, 12, 31, tzinfo=timezone.utc),
                    revenue=Decimal("100"),
                    operating_margin=Decimal("0.20"),
                    valuation_multiple=Decimal("30"),
                    guidance_revenue_growth=Decimal("0.04"),
                    capex_to_revenue=Decimal("0.10"),
                    debt_to_equity=Decimal("0.30"),
                    cash_to_debt=Decimal("1.20"),
                    eps_actual=Decimal("2.00"),
                    eps_consensus=Decimal("2.00"),
                ),
                FundamentalPeriodSnapshot(
                    period_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
                    revenue=Decimal("125"),
                    operating_margin=Decimal("0.24"),
                    valuation_multiple=Decimal("45"),
                    guidance_revenue_growth=Decimal("0.12"),
                    capex_to_revenue=Decimal("0.16"),
                    debt_to_equity=Decimal("0.40"),
                    cash_to_debt=Decimal("2.00"),
                    eps_actual=Decimal("2.20"),
                    eps_consensus=Decimal("2.00"),
                ),
            ],
            benchmark_valuation_multiple=Decimal("30"),
        )

        scores = combine_signal_components(
            strategic=StrategicThesisInputs(
                evidence_confidence=Decimal("0.80"),
                thesis_alignment=Decimal("0.70"),
                market_importance=Decimal("0.90"),
                staleness_days=20,
            ),
            sentiment=sentiment,
            technical=technical,
            fundamental=fundamental,
            forward=ForwardIndicatorInputs(
                futures_pressure=Decimal("0.60"),
                capex_revision=Decimal("0.70"),
                supply_chain_pressure=Decimal("0.50"),
                power_availability=Decimal("0.80"),
            ),
            risk=PortfolioRiskInputs(
                concentration_risk=Decimal("0.20"),
                theme_exposure_risk=Decimal("0.30"),
                liquidity_risk=Decimal("0.10"),
                drawdown_risk=Decimal("0.20"),
            ),
        )

        self.assertEqual(Decimal("0.785"), scores.strategic_thesis_score)
        self.assertEqual(Decimal("0.9"), scores.sentiment_score)
        self.assertEqual(technical.tactical_technical_score, scores.tactical_technical_score)
        self.assertEqual(Decimal("0.856"), scores.fundamental_score)
        self.assertEqual(Decimal("0.63"), scores.forward_indicator_score)
        self.assertEqual(Decimal("0.21"), scores.portfolio_risk_score)
        self.assertEqual(Decimal("0.775"), scores.combined_attractiveness_score)
        self.assertEqual(
            {
                "strategic_thesis_score",
                "sentiment_score",
                "tactical_technical_score",
                "fundamental_score",
                "forward_indicator_score",
                "portfolio_risk_score",
                "combined_attractiveness_score",
            },
            set(scores.score_breakdown),
        )


if __name__ == "__main__":
    unittest.main()
