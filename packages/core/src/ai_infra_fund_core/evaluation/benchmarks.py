from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import Sequence

from ai_infra_fund_core.contracts.common import (
    normalize_tuple,
    require_non_empty_tuple,
    require_positive,
    require_text,
)


METRIC_QUANT = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class BenchmarkComparisonResult:
    strategy_id: str
    recommendation_id: str
    data_snapshot_ids: tuple[str, ...]
    run_artifact_ids: tuple[str, ...]
    benchmark_id: str
    benchmark_version: str
    formula_version: str
    strategy_return: Decimal
    benchmark_return: Decimal
    relative_return: Decimal
    strategy_max_drawdown: Decimal
    benchmark_max_drawdown: Decimal
    relative_drawdown: Decimal
    strategy_volatility: Decimal
    benchmark_volatility: Decimal
    relative_volatility: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategy_id", require_text(self.strategy_id, "strategy_id"))
        object.__setattr__(self, "recommendation_id", require_text(self.recommendation_id, "recommendation_id"))
        object.__setattr__(
            self,
            "data_snapshot_ids",
            require_non_empty_tuple(normalize_tuple(self.data_snapshot_ids, "data_snapshot_ids"), "data_snapshot_ids"),
        )
        object.__setattr__(
            self,
            "run_artifact_ids",
            require_non_empty_tuple(normalize_tuple(self.run_artifact_ids, "run_artifact_ids"), "run_artifact_ids"),
        )
        object.__setattr__(self, "benchmark_id", require_text(self.benchmark_id, "benchmark_id"))
        object.__setattr__(self, "benchmark_version", require_text(self.benchmark_version, "benchmark_version"))
        object.__setattr__(self, "formula_version", require_text(self.formula_version, "formula_version"))


def compare_to_benchmark(
    *,
    strategy_id: str,
    recommendation_id: str,
    data_snapshot_ids: Sequence[str],
    run_artifact_ids: Sequence[str],
    benchmark_id: str,
    benchmark_version: str,
    formula_version: str,
    strategy_values: Sequence[Decimal],
    benchmark_values: Sequence[Decimal],
) -> BenchmarkComparisonResult:
    strategy_curve = _validated_curve(strategy_values, "strategy_values")
    benchmark_curve = _validated_curve(benchmark_values, "benchmark_values")
    if len(strategy_curve) != len(benchmark_curve):
        raise ValueError("strategy_values and benchmark_values must cover the same number of periods")
    snapshot_ids = require_non_empty_tuple(normalize_tuple(data_snapshot_ids, "data_snapshot_ids"), "data_snapshot_ids")
    artifact_ids = require_non_empty_tuple(normalize_tuple(run_artifact_ids, "run_artifact_ids"), "run_artifact_ids")

    strategy_return = _total_return(strategy_curve)
    benchmark_return = _total_return(benchmark_curve)
    strategy_drawdown = _max_drawdown(strategy_curve)
    benchmark_drawdown = _max_drawdown(benchmark_curve)
    strategy_volatility = _volatility(_period_returns(strategy_curve))
    benchmark_volatility = _volatility(_period_returns(benchmark_curve))

    return BenchmarkComparisonResult(
        strategy_id=strategy_id,
        recommendation_id=recommendation_id,
        data_snapshot_ids=snapshot_ids,
        run_artifact_ids=artifact_ids,
        benchmark_id=benchmark_id,
        benchmark_version=benchmark_version,
        formula_version=formula_version,
        strategy_return=strategy_return,
        benchmark_return=benchmark_return,
        relative_return=_quantize(strategy_return - benchmark_return),
        strategy_max_drawdown=strategy_drawdown,
        benchmark_max_drawdown=benchmark_drawdown,
        relative_drawdown=_quantize(strategy_drawdown - benchmark_drawdown),
        strategy_volatility=strategy_volatility,
        benchmark_volatility=benchmark_volatility,
        relative_volatility=_quantize(strategy_volatility - benchmark_volatility),
    )


def _validated_curve(values: Sequence[Decimal], field_name: str) -> tuple[Decimal, ...]:
    curve = tuple(Decimal(str(value)) for value in values)
    if len(curve) < 2:
        raise ValueError(f"{field_name} must include at least two periods")
    for value in curve:
        require_positive(value, f"{field_name} values")
    return curve


def _total_return(values: tuple[Decimal, ...]) -> Decimal:
    return _quantize((values[-1] / values[0]) - Decimal("1"))


def _period_returns(values: tuple[Decimal, ...]) -> tuple[Decimal, ...]:
    return tuple((current / previous) - Decimal("1") for previous, current in zip(values, values[1:]))


def _max_drawdown(values: tuple[Decimal, ...]) -> Decimal:
    peak = values[0]
    max_drawdown = Decimal("0")
    for value in values:
        peak = max(peak, value)
        drawdown = (value / peak) - Decimal("1")
        max_drawdown = min(max_drawdown, drawdown)
    return _quantize(max_drawdown)


def _volatility(returns: tuple[Decimal, ...]) -> Decimal:
    mean = sum(returns, Decimal("0")) / Decimal(len(returns))
    variance = sum((period_return - mean) ** 2 for period_return in returns) / Decimal(len(returns))
    with localcontext() as context:
        context.prec = 28
        return _quantize(variance.sqrt())


def _quantize(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(METRIC_QUANT, rounding=ROUND_HALF_UP)
