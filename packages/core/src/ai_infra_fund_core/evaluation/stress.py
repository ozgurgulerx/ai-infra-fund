from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from random import Random
from typing import Iterable


ZERO = Decimal("0")
ONE = Decimal("1")
METRIC_QUANT = Decimal("0.000001")


@dataclass(frozen=True, slots=True)
class MonteCarloStressResult:
    seed: int
    simulations: int
    horizon_periods: int
    terminal_returns: tuple[Decimal, ...]
    max_drawdowns: tuple[Decimal, ...]
    mean_return: Decimal
    median_return: Decimal
    p05_return: Decimal
    p95_return: Decimal
    worst_return: Decimal
    best_return: Decimal
    mean_max_drawdown: Decimal
    median_max_drawdown: Decimal
    p95_max_drawdown: Decimal
    worst_max_drawdown: Decimal


def run_monte_carlo_stress(
    *,
    returns: Iterable[Decimal],
    simulations: int,
    horizon_periods: int,
    seed: int,
) -> MonteCarloStressResult:
    normalized_returns = _normalize_returns(returns)
    if simulations <= 0:
        raise ValueError("simulations must be positive")
    if horizon_periods <= 0:
        raise ValueError("horizon_periods must be positive")

    rng = Random(seed)
    terminal_returns: list[Decimal] = []
    max_drawdowns: list[Decimal] = []

    for _ in range(simulations):
        terminal_return, max_drawdown = _simulate_path(
            returns=normalized_returns,
            horizon_periods=horizon_periods,
            rng=rng,
        )
        terminal_returns.append(terminal_return)
        max_drawdowns.append(max_drawdown)

    quantized_returns = tuple(_quantize(value) for value in terminal_returns)
    quantized_drawdowns = tuple(_quantize(value) for value in max_drawdowns)

    return MonteCarloStressResult(
        seed=seed,
        simulations=simulations,
        horizon_periods=horizon_periods,
        terminal_returns=quantized_returns,
        max_drawdowns=quantized_drawdowns,
        mean_return=_mean(terminal_returns),
        median_return=_median(terminal_returns),
        p05_return=_percentile(terminal_returns, Decimal("0.05")),
        p95_return=_percentile(terminal_returns, Decimal("0.95")),
        worst_return=_quantize(min(terminal_returns)),
        best_return=_quantize(max(terminal_returns)),
        mean_max_drawdown=_mean(max_drawdowns),
        median_max_drawdown=_median(max_drawdowns),
        p95_max_drawdown=_percentile(max_drawdowns, Decimal("0.95")),
        worst_max_drawdown=_quantize(max(max_drawdowns)),
    )


def _simulate_path(
    *,
    returns: tuple[Decimal, ...],
    horizon_periods: int,
    rng: Random,
) -> tuple[Decimal, Decimal]:
    value = ONE
    peak = ONE
    max_drawdown = ZERO

    for _ in range(horizon_periods):
        value *= ONE + rng.choice(returns)
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return value - ONE, max_drawdown


def _normalize_returns(returns: Iterable[Decimal]) -> tuple[Decimal, ...]:
    normalized = tuple(Decimal(str(value)) for value in returns)
    if not normalized:
        raise ValueError("returns must not be empty")
    for value in normalized:
        if value < -ONE:
            raise ValueError("returns cannot be less than -100%")
    return normalized


def _mean(values: list[Decimal]) -> Decimal:
    return _quantize(sum(values, ZERO) / Decimal(len(values)))


def _median(values: list[Decimal]) -> Decimal:
    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return _quantize(sorted_values[midpoint])
    return _quantize((sorted_values[midpoint - 1] + sorted_values[midpoint]) / Decimal("2"))


def _percentile(values: list[Decimal], percentile: Decimal) -> Decimal:
    sorted_values = sorted(values)
    position = (percentile * Decimal(len(sorted_values))).to_integral_value(rounding=ROUND_CEILING)
    index = max(0, min(int(position) - 1, len(sorted_values) - 1))
    return _quantize(sorted_values[index])


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(METRIC_QUANT, rounding=ROUND_HALF_UP)
