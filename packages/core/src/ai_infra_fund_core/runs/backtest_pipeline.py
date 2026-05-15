"""Pure backtest-pipeline composition.

Glues the existing evaluation primitives together to produce a
deterministic ``BacktestRun`` artifact. No I/O.

The worker module ``backtest_orchestrator.py`` is the I/O shell that
reads requests from Postgres, calls this composition function, and
persists the resulting ``BacktestRun`` + ``RunArtifact`` rows.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from ai_infra_fund_core.contracts.common import stable_hash_payload
from ai_infra_fund_core.contracts.evaluation import BacktestRun
from ai_infra_fund_core.evaluation.benchmarks import (
    BenchmarkComparisonResult,
    compare_to_benchmark,
)
from ai_infra_fund_core.evaluation.bias_checks import (
    BiasCheckResult,
    check_lookahead_bias,
)
from ai_infra_fund_core.evaluation.shadow import (
    ShadowModeEvaluationRecord,
    create_shadow_mode_record,
)
from ai_infra_fund_core.evaluation.stress import (
    MonteCarloStressResult,
    run_monte_carlo_stress,
)


@dataclass(frozen=True, slots=True)
class BacktestPipelineInputs:
    strategy_id: str
    production_recommendation_id: str
    dataset_snapshot_ids: tuple[str, ...]
    validation_protocol: str
    cost_assumptions: Mapping[str, Any]
    formula_version: str
    benchmark_id: str
    benchmark_version: str
    features: Sequence[Mapping[str, Any]]
    predictions: Sequence[Mapping[str, Any]]
    strategy_values: Sequence[Decimal]
    benchmark_values: Sequence[Decimal]
    monte_carlo_returns: Sequence[Decimal]
    monte_carlo_simulations: int
    monte_carlo_horizon_periods: int
    monte_carlo_seed: int
    model_run_id: str
    shadow_output_id: str
    run_artifact_ids: tuple[str, ...]
    as_of: datetime
    available_at: datetime
    created_at: datetime
    extra_metrics: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BacktestRunDraft:
    backtest_run: BacktestRun
    bias_check: BiasCheckResult
    benchmark_comparison: BenchmarkComparisonResult
    monte_carlo: MonteCarloStressResult
    shadow_record: ShadowModeEvaluationRecord


class LookaheadViolationError(ValueError):
    """Raised when backtest inputs would expose data published after ``as_of``."""


def compose_backtest_pipeline(inputs: BacktestPipelineInputs) -> BacktestRunDraft:
    if inputs.available_at > inputs.as_of:
        raise LookaheadViolationError(
            f"available_at ({inputs.available_at.isoformat()}) must be <= "
            f"as_of ({inputs.as_of.isoformat()})"
        )
    bias_check = check_lookahead_bias(inputs.features, inputs.predictions)
    benchmark = compare_to_benchmark(
        strategy_id=inputs.strategy_id,
        recommendation_id=inputs.production_recommendation_id,
        data_snapshot_ids=inputs.dataset_snapshot_ids,
        run_artifact_ids=inputs.run_artifact_ids,
        benchmark_id=inputs.benchmark_id,
        benchmark_version=inputs.benchmark_version,
        formula_version=inputs.formula_version,
        strategy_values=inputs.strategy_values,
        benchmark_values=inputs.benchmark_values,
    )
    monte_carlo = run_monte_carlo_stress(
        returns=inputs.monte_carlo_returns,
        simulations=inputs.monte_carlo_simulations,
        horizon_periods=inputs.monte_carlo_horizon_periods,
        seed=inputs.monte_carlo_seed,
    )
    metrics = _metrics_payload(
        bias_check=bias_check,
        benchmark=benchmark,
        monte_carlo=monte_carlo,
        extra=inputs.extra_metrics,
    )

    # Hash on content-only metrics: identical inputs must yield the same
    # artifact_hash regardless of when the pipeline ran. shadow_mode is
    # comparison-event metadata (depends on created_at) and is appended after.
    artifact_hash = stable_hash_payload(
        {
            "strategy_id": inputs.strategy_id,
            "dataset_snapshot_ids": list(inputs.dataset_snapshot_ids),
            "validation_protocol": inputs.validation_protocol,
            "cost_assumptions": dict(inputs.cost_assumptions),
            "metrics": metrics,
            "as_of": inputs.as_of.isoformat(),
            "available_at": inputs.available_at.isoformat(),
        }
    )
    backtest_run_id = f"backtest-{artifact_hash[:24]}"

    shadow_record = create_shadow_mode_record(
        production_recommendation_id=inputs.production_recommendation_id,
        strategy_id=inputs.strategy_id,
        data_snapshot_ids=inputs.dataset_snapshot_ids,
        run_artifact_ids=inputs.run_artifact_ids,
        model_run_id=inputs.model_run_id,
        shadow_output_id=inputs.shadow_output_id,
        formula_version=inputs.formula_version,
        benchmark_version=inputs.benchmark_version,
        model_output_metadata={"source": "backtest_pipeline_v1"},
        metrics=metrics,
        created_at=inputs.created_at,
    )
    metrics["shadow_mode"] = {
        "evaluation_id": shadow_record.evaluation_id,
        "shadow_output_id": shadow_record.shadow_output_id,
        "affects_production": shadow_record.affects_production,
    }

    backtest_run = BacktestRun(
        backtest_run_id=backtest_run_id,
        strategy_id=inputs.strategy_id,
        dataset_snapshot_ids=inputs.dataset_snapshot_ids,
        validation_protocol=inputs.validation_protocol,
        cost_assumptions=dict(inputs.cost_assumptions),
        metrics=metrics,
        artifact_hash=artifact_hash,
        as_of=inputs.as_of,
        available_at=inputs.available_at,
        created_at=inputs.created_at,
    )
    return BacktestRunDraft(
        backtest_run=backtest_run,
        bias_check=bias_check,
        benchmark_comparison=benchmark,
        monte_carlo=monte_carlo,
        shadow_record=shadow_record,
    )


def _metrics_payload(
    *,
    bias_check: BiasCheckResult,
    benchmark: BenchmarkComparisonResult,
    monte_carlo: MonteCarloStressResult,
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "bias_checks": {
            "passed": bias_check.passed,
            "violations": list(bias_check.violations),
        },
        "benchmark_comparison": {
            "benchmark_id": benchmark.benchmark_id,
            "benchmark_version": benchmark.benchmark_version,
            "formula_version": benchmark.formula_version,
            "strategy_return": str(benchmark.strategy_return),
            "benchmark_return": str(benchmark.benchmark_return),
            "relative_return": str(benchmark.relative_return),
            "strategy_max_drawdown": str(benchmark.strategy_max_drawdown),
            "benchmark_max_drawdown": str(benchmark.benchmark_max_drawdown),
            "relative_drawdown": str(benchmark.relative_drawdown),
            "strategy_volatility": str(benchmark.strategy_volatility),
            "benchmark_volatility": str(benchmark.benchmark_volatility),
            "relative_volatility": str(benchmark.relative_volatility),
        },
        "monte_carlo": {
            "seed": monte_carlo.seed,
            "simulations": monte_carlo.simulations,
            "horizon_periods": monte_carlo.horizon_periods,
            "mean_return": str(monte_carlo.mean_return),
            "median_return": str(monte_carlo.median_return),
            "p05_return": str(monte_carlo.p05_return),
            "p95_return": str(monte_carlo.p95_return),
            "worst_return": str(monte_carlo.worst_return),
            "best_return": str(monte_carlo.best_return),
            "mean_max_drawdown": str(monte_carlo.mean_max_drawdown),
            "median_max_drawdown": str(monte_carlo.median_max_drawdown),
            "p95_max_drawdown": str(monte_carlo.p95_max_drawdown),
            "worst_max_drawdown": str(monte_carlo.worst_max_drawdown),
        },
        "formula_versions": {
            "benchmark_formula": benchmark.formula_version,
            "benchmark_version": benchmark.benchmark_version,
        },
        **({"extra": dict(extra)} if extra else {}),
    }


__all__ = [
    "BacktestPipelineInputs",
    "BacktestRunDraft",
    "LookaheadViolationError",
    "compose_backtest_pipeline",
]
