from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping


ZERO = Decimal("0")
ONE = Decimal("1")
WEIGHT_TOLERANCE = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class PortfolioConstraints:
    max_single_name_weight: Decimal
    max_theme_exposure: Decimal
    cash_floor: Decimal
    liquidity_floor: Decimal
    turnover_cap: Decimal

    def __post_init__(self) -> None:
        for field_name in (
            "max_single_name_weight",
            "max_theme_exposure",
            "cash_floor",
            "liquidity_floor",
            "turnover_cap",
        ):
            value = _unit(getattr(self, field_name), field_name)
            object.__setattr__(self, field_name, value)


@dataclass(frozen=True, slots=True)
class ConstraintValidationResult:
    passed: bool
    violation_codes: tuple[str, ...]
    turnover: Decimal


def validate_portfolio_constraints(
    *,
    weights: Mapping[str, Decimal],
    cash_weight: Decimal,
    constraints: PortfolioConstraints,
    theme_by_ticker: Mapping[str, str] | None = None,
    liquidity_by_ticker: Mapping[str, Decimal] | None = None,
    current_weights: Mapping[str, Decimal] | None = None,
    current_cash_weight: Decimal | None = None,
) -> ConstraintValidationResult:
    normalized_weights = _normalize_weights(weights)
    cash = _unit(cash_weight, "cash_weight")
    violations: list[str] = []

    total_weight = cash + sum(normalized_weights.values(), ZERO)
    if abs(total_weight - ONE) > WEIGHT_TOLERANCE:
        violations.append("target_weights_sum")

    if any(weight > constraints.max_single_name_weight for weight in normalized_weights.values()):
        violations.append("max_single_name_weight")

    if _theme_violation(normalized_weights, constraints, theme_by_ticker or {}):
        violations.append("max_theme_exposure")

    if cash < constraints.cash_floor:
        violations.append("cash_floor")

    if _liquidity_violation(normalized_weights, constraints, liquidity_by_ticker or {}):
        violations.append("liquidity_floor")

    turnover = _portfolio_turnover(
        normalized_weights,
        cash,
        current_weights or {},
        current_cash_weight,
    )
    if turnover > constraints.turnover_cap:
        violations.append("turnover_cap")

    return ConstraintValidationResult(
        passed=not violations,
        violation_codes=tuple(dict.fromkeys(violations)),
        turnover=turnover,
    )


def constraints_to_dict(constraints: PortfolioConstraints) -> dict[str, str]:
    return {
        "max_single_name_weight": str(constraints.max_single_name_weight),
        "max_theme_exposure": str(constraints.max_theme_exposure),
        "cash_floor": str(constraints.cash_floor),
        "liquidity_floor": str(constraints.liquidity_floor),
        "turnover_cap": str(constraints.turnover_cap),
    }


def _normalize_weights(weights: Mapping[str, Decimal]) -> dict[str, Decimal]:
    normalized: dict[str, Decimal] = {}
    for ticker, weight in weights.items():
        ticker_text = str(ticker).strip().upper()
        if not ticker_text:
            raise ValueError("weights ticker is required")
        normalized[ticker_text] = _unit(weight, f"weight:{ticker_text}")
    return normalized


def _theme_violation(
    weights: Mapping[str, Decimal],
    constraints: PortfolioConstraints,
    theme_by_ticker: Mapping[str, str],
) -> bool:
    theme_totals: dict[str, Decimal] = {}
    for ticker, weight in weights.items():
        theme = theme_by_ticker.get(ticker)
        if not theme:
            continue
        theme_totals[theme] = theme_totals.get(theme, ZERO) + weight
    return any(total > constraints.max_theme_exposure for total in theme_totals.values())


def _liquidity_violation(
    weights: Mapping[str, Decimal],
    constraints: PortfolioConstraints,
    liquidity_by_ticker: Mapping[str, Decimal],
) -> bool:
    for ticker, weight in weights.items():
        if weight == ZERO:
            continue
        liquidity = liquidity_by_ticker.get(ticker)
        if liquidity is not None and _unit(liquidity, f"liquidity:{ticker}") < constraints.liquidity_floor:
            return True
    return False


def _portfolio_turnover(
    weights: Mapping[str, Decimal],
    cash_weight: Decimal,
    current_weights: Mapping[str, Decimal],
    current_cash_weight: Decimal | None,
) -> Decimal:
    if current_cash_weight is None and not current_weights:
        return ZERO
    normalized_current = _normalize_weights(current_weights)
    current_cash = _unit(current_cash_weight or ZERO, "current_cash_weight")
    tickers = set(weights) | set(normalized_current)
    gross_change = sum(
        abs(weights.get(ticker, ZERO) - normalized_current.get(ticker, ZERO))
        for ticker in tickers
    )
    gross_change += abs(cash_weight - current_cash)
    return (gross_change / Decimal("2")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP).normalize()


def _unit(value: Decimal, field_name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value < ZERO or decimal_value > ONE:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return decimal_value
