"""Deterministic signal scoring for the advisory control room."""

from .formulas import FORMULA_VERSIONS
from .scoring import (
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

__all__ = [
    "FORMULA_VERSIONS",
    "ForwardIndicatorInputs",
    "PortfolioRiskInputs",
    "SignalInputs",
    "StrategicThesisInputs",
    "TacticalTechnicalInputs",
    "compute_signal_bundle",
    "score_forward_indicator",
    "score_portfolio_risk",
    "score_strategic_thesis",
    "score_tactical_technical",
]
