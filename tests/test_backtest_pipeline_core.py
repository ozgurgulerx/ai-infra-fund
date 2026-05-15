from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))


from ai_infra_fund_core.contracts.evaluation import BacktestRun  # noqa: E402


NOW = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)


def _sample_inputs():
    from ai_infra_fund_core.runs.backtest_pipeline import BacktestPipelineInputs

    features = [
        {
            "feature_id": "f-momentum-30d",
            "available_at": datetime(2026, 3, 25, tzinfo=timezone.utc),
        },
        {
            "feature_id": "f-volatility-30d",
            "available_at": datetime(2026, 3, 26, tzinfo=timezone.utc),
        },
    ]
    predictions = [
        {
            "prediction_id": "p-1",
            "as_of": datetime(2026, 3, 27, tzinfo=timezone.utc),
            "feature_ids": ["f-momentum-30d", "f-volatility-30d"],
        },
        {
            "prediction_id": "p-2",
            "as_of": datetime(2026, 3, 28, tzinfo=timezone.utc),
            "feature_ids": ["f-momentum-30d"],
        },
    ]
    return BacktestPipelineInputs(
        strategy_id="strategy-ai-infra-v1",
        production_recommendation_id="recommendation-demo-001",
        dataset_snapshot_ids=("dataset-snapshot-2026q1",),
        validation_protocol="walk_forward_v1",
        cost_assumptions={
            "spread_bps": "5",
            "slippage_bps": "3",
            "fee_bps": "1",
        },
        formula_version="v1",
        benchmark_id="benchmark-spx",
        benchmark_version="v1",
        features=features,
        predictions=predictions,
        strategy_values=[
            Decimal("100"),
            Decimal("102"),
            Decimal("105"),
            Decimal("103"),
        ],
        benchmark_values=[
            Decimal("100"),
            Decimal("101"),
            Decimal("103"),
            Decimal("104"),
        ],
        monte_carlo_returns=[Decimal("0.01"), Decimal("-0.005"), Decimal("0.008")],
        monte_carlo_simulations=8,
        monte_carlo_horizon_periods=3,
        monte_carlo_seed=42,
        model_run_id="model-run-shadow-001",
        shadow_output_id="shadow-output-001",
        run_artifact_ids=("run-artifact-001",),
        as_of=NOW,
        available_at=NOW,
        created_at=NOW,
    )


class ComposeBacktestPipelineTests(unittest.TestCase):
    def test_pipeline_returns_deterministic_backtest_run(self) -> None:
        from ai_infra_fund_core.runs.backtest_pipeline import compose_backtest_pipeline

        first = compose_backtest_pipeline(_sample_inputs())
        second = compose_backtest_pipeline(_sample_inputs())

        self.assertIsInstance(first.backtest_run, BacktestRun)
        self.assertEqual(
            first.backtest_run.backtest_run_id, second.backtest_run.backtest_run_id
        )
        self.assertEqual(
            first.backtest_run.artifact_hash, second.backtest_run.artifact_hash
        )
        self.assertEqual(first.backtest_run.metrics, second.backtest_run.metrics)

    def test_pipeline_hash_ignores_created_at(self) -> None:
        from dataclasses import replace

        from ai_infra_fund_core.runs.backtest_pipeline import compose_backtest_pipeline

        base = _sample_inputs()
        later = replace(base, created_at=datetime(2027, 6, 1, tzinfo=timezone.utc))
        first = compose_backtest_pipeline(base)
        second = compose_backtest_pipeline(later)
        self.assertEqual(
            first.backtest_run.artifact_hash, second.backtest_run.artifact_hash
        )
        self.assertEqual(
            first.backtest_run.backtest_run_id, second.backtest_run.backtest_run_id
        )

    def test_pipeline_metrics_contain_expected_sections(self) -> None:
        from ai_infra_fund_core.runs.backtest_pipeline import compose_backtest_pipeline

        result = compose_backtest_pipeline(_sample_inputs())
        metrics = result.backtest_run.metrics

        for required_section in (
            "bias_checks",
            "benchmark_comparison",
            "monte_carlo",
            "shadow_mode",
            "formula_versions",
        ):
            self.assertIn(
                required_section, metrics, f"missing section: {required_section}"
            )

        self.assertTrue(metrics["bias_checks"]["passed"])
        self.assertIn("strategy_return", metrics["benchmark_comparison"])
        self.assertIn("mean_return", metrics["monte_carlo"])

    def test_pipeline_records_shadow_mode_record_that_does_not_affect_production(
        self,
    ) -> None:
        from ai_infra_fund_core.runs.backtest_pipeline import compose_backtest_pipeline

        result = compose_backtest_pipeline(_sample_inputs())

        self.assertFalse(result.shadow_record.affects_production)
        self.assertEqual(
            "recommendation-demo-001",
            result.shadow_record.production_recommendation_id,
        )

    def test_pipeline_surfaces_lookahead_violations(self) -> None:
        from ai_infra_fund_core.runs.backtest_pipeline import (
            BacktestPipelineInputs,
            compose_backtest_pipeline,
        )

        # Feature available_at is AFTER the prediction's as_of — lookahead.
        bad_features = [
            {
                "feature_id": "f-future",
                "available_at": datetime(2026, 4, 1, tzinfo=timezone.utc),
            }
        ]
        bad_predictions = [
            {
                "prediction_id": "p-bad",
                "as_of": datetime(2026, 3, 1, tzinfo=timezone.utc),
                "feature_ids": ["f-future"],
            }
        ]
        sample = _sample_inputs()
        bad_inputs = BacktestPipelineInputs(
            strategy_id=sample.strategy_id,
            production_recommendation_id=sample.production_recommendation_id,
            dataset_snapshot_ids=sample.dataset_snapshot_ids,
            validation_protocol=sample.validation_protocol,
            cost_assumptions=sample.cost_assumptions,
            formula_version=sample.formula_version,
            benchmark_id=sample.benchmark_id,
            benchmark_version=sample.benchmark_version,
            features=bad_features,
            predictions=bad_predictions,
            strategy_values=sample.strategy_values,
            benchmark_values=sample.benchmark_values,
            monte_carlo_returns=sample.monte_carlo_returns,
            monte_carlo_simulations=sample.monte_carlo_simulations,
            monte_carlo_horizon_periods=sample.monte_carlo_horizon_periods,
            monte_carlo_seed=sample.monte_carlo_seed,
            model_run_id=sample.model_run_id,
            shadow_output_id=sample.shadow_output_id,
            run_artifact_ids=sample.run_artifact_ids,
            as_of=sample.as_of,
            available_at=sample.available_at,
            created_at=sample.created_at,
        )

        result = compose_backtest_pipeline(bad_inputs)

        self.assertFalse(result.backtest_run.metrics["bias_checks"]["passed"])
        self.assertGreaterEqual(
            len(result.backtest_run.metrics["bias_checks"]["violations"]), 1
        )


if __name__ == "__main__":
    unittest.main()
