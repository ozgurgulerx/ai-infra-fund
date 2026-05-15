from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from ai_infra_fund_core.audit.experiment_events import EventSink, build_event
from ai_infra_fund_core.contracts.signals import SignalBundle

from .formulas import FORMULA_VERSIONS, SCORE_QUANT


ZERO = Decimal("0")
ONE = Decimal("1")


@dataclass(frozen=True, slots=True)
class StrategicThesisInputs:
    evidence_confidence: Decimal
    thesis_alignment: Decimal
    market_importance: Decimal
    staleness_days: int


@dataclass(frozen=True, slots=True)
class TacticalTechnicalInputs:
    trend_strength: Decimal
    momentum: Decimal
    relative_strength: Decimal
    volume_confirmation: Decimal


@dataclass(frozen=True, slots=True)
class ForwardIndicatorInputs:
    futures_pressure: Decimal
    capex_revision: Decimal
    supply_chain_pressure: Decimal
    power_availability: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioRiskInputs:
    concentration_risk: Decimal
    theme_exposure_risk: Decimal
    liquidity_risk: Decimal
    drawdown_risk: Decimal


@dataclass(frozen=True, slots=True)
class SignalInputs:
    strategic: StrategicThesisInputs
    tactical: TacticalTechnicalInputs
    forward: ForwardIndicatorInputs
    risk: PortfolioRiskInputs


def score_strategic_thesis(inputs: StrategicThesisInputs) -> Decimal:
    if inputs.staleness_days < 0:
        raise ValueError("staleness_days must be non-negative")
    base_score = _weighted_sum(
        (
            (_unit(inputs.evidence_confidence, "evidence_confidence"), Decimal("0.45")),
            (_unit(inputs.thesis_alignment, "thesis_alignment"), Decimal("0.35")),
            (_unit(inputs.market_importance, "market_importance"), Decimal("0.20")),
        )
    )
    return _quantize(base_score * _staleness_multiplier(inputs.staleness_days))


def score_tactical_technical(inputs: TacticalTechnicalInputs) -> Decimal:
    return _quantize(
        _weighted_sum(
            (
                (_unit(inputs.trend_strength, "trend_strength"), Decimal("0.35")),
                (_unit(inputs.momentum, "momentum"), Decimal("0.30")),
                (_unit(inputs.relative_strength, "relative_strength"), Decimal("0.20")),
                (
                    _unit(inputs.volume_confirmation, "volume_confirmation"),
                    Decimal("0.15"),
                ),
            )
        )
    )


def score_forward_indicator(inputs: ForwardIndicatorInputs) -> Decimal:
    return _quantize(
        _weighted_sum(
            (
                (_unit(inputs.futures_pressure, "futures_pressure"), Decimal("0.35")),
                (_unit(inputs.capex_revision, "capex_revision"), Decimal("0.25")),
                (
                    _unit(inputs.supply_chain_pressure, "supply_chain_pressure"),
                    Decimal("0.25"),
                ),
                (
                    _unit(inputs.power_availability, "power_availability"),
                    Decimal("0.15"),
                ),
            )
        )
    )


def score_portfolio_risk(inputs: PortfolioRiskInputs) -> Decimal:
    return _quantize(
        _weighted_sum(
            (
                (
                    _unit(inputs.concentration_risk, "concentration_risk"),
                    Decimal("0.30"),
                ),
                (
                    _unit(inputs.theme_exposure_risk, "theme_exposure_risk"),
                    Decimal("0.30"),
                ),
                (_unit(inputs.liquidity_risk, "liquidity_risk"), Decimal("0.20")),
                (_unit(inputs.drawdown_risk, "drawdown_risk"), Decimal("0.20")),
            )
        )
    )


def compute_signal_bundle(
    *,
    signal_bundle_id: str,
    ticker: str,
    as_of: datetime,
    created_at: datetime,
    input_snapshot_hash: str,
    inputs: SignalInputs,
    event_sink: EventSink | None = None,
    run_id: str | None = None,
) -> SignalBundle:
    bundle = SignalBundle(
        signal_bundle_id=signal_bundle_id,
        ticker=ticker,
        as_of=as_of,
        strategic_thesis_score=score_strategic_thesis(inputs.strategic),
        tactical_technical_score=score_tactical_technical(inputs.tactical),
        forward_indicator_score=score_forward_indicator(inputs.forward),
        portfolio_risk_score=score_portfolio_risk(inputs.risk),
        formula_versions=dict(FORMULA_VERSIONS),
        input_snapshot_hash=input_snapshot_hash,
        created_at=created_at,
    )
    if event_sink is not None:
        event = build_event(
            kind="signal_computed",
            run_id=run_id,
            payload={
                "signal_bundle_id": bundle.signal_bundle_id,
                "ticker": bundle.ticker,
                "as_of": bundle.as_of.isoformat(),
                "strategic_thesis_score": str(bundle.strategic_thesis_score),
                "tactical_technical_score": str(bundle.tactical_technical_score),
                "forward_indicator_score": str(bundle.forward_indicator_score),
                "portfolio_risk_score": str(bundle.portfolio_risk_score),
            },
            occurred_at=created_at,
        )
        event_sink(event)
    return bundle


def _weighted_sum(weighted_values: tuple[tuple[Decimal, Decimal], ...]) -> Decimal:
    return sum(value * weight for value, weight in weighted_values)


def _staleness_multiplier(staleness_days: int) -> Decimal:
    stale_after_days = Decimal("180")
    max_penalty = Decimal("0.40")
    days = Decimal(staleness_days)
    if days <= stale_after_days:
        return ONE
    penalty = min(
        max_penalty, ((days - stale_after_days) / stale_after_days) * max_penalty
    )
    return ONE - penalty


def _unit(value: Decimal, field_name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value < ZERO or decimal_value > ONE:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return decimal_value


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal(SCORE_QUANT), rounding=ROUND_HALF_UP).normalize()
