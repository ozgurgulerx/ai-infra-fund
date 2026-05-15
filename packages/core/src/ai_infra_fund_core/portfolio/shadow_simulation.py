"""Shadow-portfolio simulation.

Pure functions that compute portfolio drift vs. the latest advisory
target weights, and a counterfactual value curve if the target weights
had been held over a price window. Advisory-only — no execution surface.

Every price point must carry an ``available_at`` timestamp <= ``as_of``;
otherwise ``LookaheadError`` is raised.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from ai_infra_fund_core.contracts.signals import TargetWeights


class LookaheadError(ValueError):
    """Raised when a simulation input timestamp exceeds the ``as_of`` cutoff."""


@dataclass(frozen=True, slots=True)
class DriftRow:
    ticker: str
    current_weight: Decimal
    target_weight: Decimal
    drift: Decimal


@dataclass(frozen=True, slots=True)
class ShadowCurvePoint:
    date: datetime
    shadow_value: Decimal


@dataclass(frozen=True, slots=True)
class ShadowCurve:
    points: tuple[ShadowCurvePoint, ...]
    metrics: dict[str, Decimal]


def compute_portfolio_drift(
    *,
    holdings: Mapping[str, Decimal],
    target_weights: TargetWeights,
) -> tuple[DriftRow, ...]:
    tickers = sorted(set(holdings) | set(target_weights.weights))
    rows: list[DriftRow] = []
    for ticker in tickers:
        current = _to_decimal(holdings.get(ticker, Decimal("0")))
        target = _to_decimal(target_weights.weights.get(ticker, Decimal("0")))
        rows.append(
            DriftRow(
                ticker=ticker,
                current_weight=current,
                target_weight=target,
                drift=target - current,
            )
        )
    return tuple(rows)


def simulate_shadow_curve(
    *,
    target_weights: TargetWeights,
    price_series: Mapping[str, Sequence[Mapping[str, Any]]],
    as_of: datetime,
    starting_value: Decimal = Decimal("1"),
) -> ShadowCurve:
    if as_of.tzinfo is None:
        raise LookaheadError("as_of must be timezone-aware")

    tickers = [
        ticker
        for ticker in target_weights.weights
        if _to_decimal(target_weights.weights[ticker]) > Decimal("0")
    ]
    if not tickers:
        return ShadowCurve(
            points=(ShadowCurvePoint(date=as_of, shadow_value=starting_value),),
            metrics={
                "shadow_return": Decimal("0"),
                "starting_value": starting_value,
                "ending_value": starting_value,
            },
        )

    normalized_series: dict[str, list[tuple[datetime, Decimal]]] = {}
    for ticker in tickers:
        if ticker not in price_series:
            raise ValueError(f"price_series missing entries for {ticker}")
        points = price_series[ticker]
        normalized: list[tuple[datetime, Decimal]] = []
        for point in points:
            date = _require_aware_timestamp(point.get("date"), "date")
            available_at = _require_aware_timestamp(
                point.get("available_at"), "available_at"
            )
            if available_at > as_of:
                raise LookaheadError(
                    f"price for {ticker} at {available_at.isoformat()} "
                    f"available after as_of {as_of.isoformat()}"
                )
            price = _to_decimal(point.get("price"))
            if price <= Decimal("0"):
                raise ValueError(f"price must be positive for {ticker}")
            normalized.append((date, price))
        normalized.sort(key=lambda row: row[0])
        normalized_series[ticker] = normalized

    sample_dates = [row[0] for row in normalized_series[tickers[0]]]
    length = len(sample_dates)
    for ticker, series in normalized_series.items():
        if len(series) != length:
            raise ValueError(f"price_series for {ticker} must contain {length} points")

    starting_prices = {ticker: normalized_series[ticker][0][1] for ticker in tickers}
    weights = {
        ticker: _to_decimal(target_weights.weights[ticker]) for ticker in tickers
    }
    cash_weight = _to_decimal(target_weights.cash_weight)

    points: list[ShadowCurvePoint] = []
    for index, date in enumerate(sample_dates):
        ticker_contribution = sum(
            (
                weights[ticker]
                * (normalized_series[ticker][index][1] / starting_prices[ticker])
                for ticker in tickers
            ),
            Decimal("0"),
        )
        value = starting_value * (ticker_contribution + cash_weight)
        points.append(ShadowCurvePoint(date=date, shadow_value=value))

    shadow_return = (points[-1].shadow_value / points[0].shadow_value) - Decimal("1")
    return ShadowCurve(
        points=tuple(points),
        metrics={
            "shadow_return": shadow_return,
            "starting_value": points[0].shadow_value,
            "ending_value": points[-1].shadow_value,
        },
    )


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _require_aware_timestamp(value: object, field_name: str) -> datetime:
    """Validate a lookahead-sensitive timestamp field.

    Raises ``LookaheadError`` (not ``ValueError``) so the route layer can
    consistently surface every timestamp problem on a time-keyed input as
    HTTP 422 ``LOOKAHEAD_VIOLATION``.
    """
    if not isinstance(value, datetime):
        raise LookaheadError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise LookaheadError(f"{field_name} must be timezone-aware")
    return value


__all__ = [
    "DriftRow",
    "LookaheadError",
    "ShadowCurve",
    "ShadowCurvePoint",
    "compute_portfolio_drift",
    "simulate_shadow_curve",
]
