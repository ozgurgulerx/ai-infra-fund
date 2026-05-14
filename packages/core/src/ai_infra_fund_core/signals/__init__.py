"""Deterministic signal scoring for the advisory control room."""

from .formulas import FORMULA_VERSIONS
from .fundamental import FundamentalPeriodSnapshot, FundamentalSnapshot, compute_fundamental_snapshot
from .integration import IntegratedSignalScores, combine_signal_components
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
from .sentiment import SentimentEvidence, SentimentSnapshot, compute_sentiment_snapshot
from .technical import MarketPoint, TechnicalSnapshot, compute_technical_snapshot

__all__ = [
    "FORMULA_VERSIONS",
    "ForwardIndicatorInputs",
    "FundamentalPeriodSnapshot",
    "FundamentalSnapshot",
    "IntegratedSignalScores",
    "MarketPoint",
    "PortfolioRiskInputs",
    "SignalInputs",
    "SentimentEvidence",
    "SentimentSnapshot",
    "StrategicThesisInputs",
    "TacticalTechnicalInputs",
    "TechnicalSnapshot",
    "combine_signal_components",
    "compute_fundamental_snapshot",
    "compute_sentiment_snapshot",
    "compute_signal_bundle",
    "compute_technical_snapshot",
    "score_forward_indicator",
    "score_portfolio_risk",
    "score_strategic_thesis",
    "score_tactical_technical",
]
