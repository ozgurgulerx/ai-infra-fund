from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.evaluation.benchmarks import (  # noqa: E402
    BenchmarkComparisonResult,
    compare_to_benchmark,
)


class Phase7BenchmarkComparisonTests(unittest.TestCase):
    def test_benchmark_and_shadow_apis_are_exported_from_evaluation_package(self) -> None:
        from ai_infra_fund_core.evaluation import (  # noqa: PLC0415
            BenchmarkComparisonResult as ExportedBenchmarkComparisonResult,
            ShadowModeEvaluationRecord,
            compare_to_benchmark as exported_compare_to_benchmark,
            create_shadow_mode_record,
        )

        self.assertIs(ExportedBenchmarkComparisonResult, BenchmarkComparisonResult)
        self.assertEqual("ShadowModeEvaluationRecord", ShadowModeEvaluationRecord.__name__)
        self.assertIs(exported_compare_to_benchmark, compare_to_benchmark)
        self.assertTrue(callable(create_shadow_mode_record))

    def test_compares_strategy_against_benchmark_with_audit_lineage(self) -> None:
        result = compare_to_benchmark(
            strategy_id="strategy-ai-infra-core",
            recommendation_id="recommendation-2026-05-14",
            data_snapshot_ids=("market-snapshot-1", "factor-snapshot-1"),
            run_artifact_ids=("backtest-run-1", "benchmark-run-1"),
            benchmark_id="benchmark-equal-weight-ai-infra",
            benchmark_version="benchmark-v1",
            formula_version="benchmark-comparison-v1",
            strategy_values=(Decimal("100"), Decimal("120"), Decimal("90"), Decimal("108")),
            benchmark_values=(Decimal("100"), Decimal("110"), Decimal("104.5"), Decimal("120.175")),
        )

        self.assertIsInstance(result, BenchmarkComparisonResult)
        self.assertEqual("strategy-ai-infra-core", result.strategy_id)
        self.assertEqual("recommendation-2026-05-14", result.recommendation_id)
        self.assertEqual(("market-snapshot-1", "factor-snapshot-1"), result.data_snapshot_ids)
        self.assertEqual(("backtest-run-1", "benchmark-run-1"), result.run_artifact_ids)
        self.assertEqual("benchmark-v1", result.benchmark_version)
        self.assertEqual("benchmark-comparison-v1", result.formula_version)
        self.assertEqual(Decimal("0.0800"), result.strategy_return)
        self.assertEqual(Decimal("0.2018"), result.benchmark_return)
        self.assertEqual(Decimal("-0.1218"), result.relative_return)
        self.assertEqual(Decimal("-0.2500"), result.strategy_max_drawdown)
        self.assertEqual(Decimal("-0.0500"), result.benchmark_max_drawdown)
        self.assertEqual(Decimal("-0.2000"), result.relative_drawdown)
        self.assertEqual(Decimal("0.2121"), result.strategy_volatility)
        self.assertEqual(Decimal("0.0850"), result.benchmark_volatility)
        self.assertEqual(Decimal("0.1271"), result.relative_volatility)

    def test_rejects_misaligned_or_invalid_benchmark_inputs(self) -> None:
        with self.assertRaisesRegex(ValueError, "strategy_values and benchmark_values must cover the same number of periods"):
            compare_to_benchmark(
                strategy_id="strategy-ai-infra-core",
                recommendation_id="recommendation-2026-05-14",
                data_snapshot_ids=("market-snapshot-1",),
                run_artifact_ids=("backtest-run-1",),
                benchmark_id="benchmark-equal-weight-ai-infra",
                benchmark_version="benchmark-v1",
                formula_version="benchmark-comparison-v1",
                strategy_values=(Decimal("100"), Decimal("105")),
                benchmark_values=(Decimal("100"), Decimal("101"), Decimal("102")),
            )

        with self.assertRaisesRegex(ValueError, "strategy_values values must be positive"):
            compare_to_benchmark(
                strategy_id="strategy-ai-infra-core",
                recommendation_id="recommendation-2026-05-14",
                data_snapshot_ids=("market-snapshot-1",),
                run_artifact_ids=("backtest-run-1",),
                benchmark_id="benchmark-equal-weight-ai-infra",
                benchmark_version="benchmark-v1",
                formula_version="benchmark-comparison-v1",
                strategy_values=(Decimal("100"), Decimal("0")),
                benchmark_values=(Decimal("100"), Decimal("101")),
            )


if __name__ == "__main__":
    unittest.main()
