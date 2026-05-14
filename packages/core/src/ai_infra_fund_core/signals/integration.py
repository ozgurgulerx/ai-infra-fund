from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from .formulas import SCORE_QUANT
from .fundamental import FundamentalSnapshot
from .scoring import (
    ForwardIndicatorInputs,
    PortfolioRiskInputs,
    StrategicThesisInputs,
    TacticalTechnicalInputs,
    score_forward_indicator,
    score_portfolio_risk,
    score_strategic_thesis,
    score_tactical_technical,
)
from .sentiment import SentimentSnapshot
from .technical import TechnicalSnapshot


ZERO = Decimal("0")
ONE = Decimal("1")


@dataclass(frozen=True, slots=True)
class IntegratedSignalScores:
    strategic_thesis_score: Decimal
    sentiment_score: Decimal
    tactical_technical_score: Decimal
    fundamental_score: Decimal
    forward_indicator_score: Decimal
    portfolio_risk_score: Decimal
    combined_attractiveness_score: Decimal
    score_breakdown: dict[str, str]


def combine_signal_components(
    *,
    strategic: StrategicThesisInputs | Decimal,
    sentiment: SentimentSnapshot | Decimal,
    technical: TechnicalSnapshot | TacticalTechnicalInputs | Decimal,
    fundamental: FundamentalSnapshot | Decimal,
    forward: ForwardIndicatorInputs | Decimal,
    risk: PortfolioRiskInputs | Decimal,
) -> IntegratedSignalScores:
    strategic_score = _score_strategic(strategic)
    sentiment_score = _score_sentiment(sentiment)
    technical_score = _score_technical(technical)
    fundamental_score = _score_fundamental(fundamental)
    forward_score = _score_forward(forward)
    risk_score = _score_risk(risk)
    combined_score = _quantize(
        strategic_score * Decimal("0.30")
        + sentiment_score * Decimal("0.15")
        + technical_score * Decimal("0.20")
        + fundamental_score * Decimal("0.15")
        + forward_score * Decimal("0.10")
        + (ONE - risk_score) * Decimal("0.10")
    )
    breakdown = {
        "strategic_thesis_score": str(strategic_score),
        "sentiment_score": str(sentiment_score),
        "tactical_technical_score": str(technical_score),
        "fundamental_score": str(fundamental_score),
        "forward_indicator_score": str(forward_score),
        "portfolio_risk_score": str(risk_score),
        "combined_attractiveness_score": str(combined_score),
    }
    return IntegratedSignalScores(
        strategic_thesis_score=strategic_score,
        sentiment_score=sentiment_score,
        tactical_technical_score=technical_score,
        fundamental_score=fundamental_score,
        forward_indicator_score=forward_score,
        portfolio_risk_score=risk_score,
        combined_attractiveness_score=combined_score,
        score_breakdown=breakdown,
    )


def _score_strategic(value: StrategicThesisInputs | Decimal) -> Decimal:
    return score_strategic_thesis(value) if isinstance(value, StrategicThesisInputs) else _unit(value, "strategic")


def _score_sentiment(value: SentimentSnapshot | Decimal) -> Decimal:
    return value.sentiment_score if isinstance(value, SentimentSnapshot) else _unit(value, "sentiment")


def _score_technical(value: TechnicalSnapshot | TacticalTechnicalInputs | Decimal) -> Decimal:
    if isinstance(value, TechnicalSnapshot):
        return value.tactical_technical_score
    if isinstance(value, TacticalTechnicalInputs):
        return score_tactical_technical(value)
    return _unit(value, "technical")


def _score_fundamental(value: FundamentalSnapshot | Decimal) -> Decimal:
    return value.fundamental_score if isinstance(value, FundamentalSnapshot) else _unit(value, "fundamental")


def _score_forward(value: ForwardIndicatorInputs | Decimal) -> Decimal:
    return score_forward_indicator(value) if isinstance(value, ForwardIndicatorInputs) else _unit(value, "forward")


def _score_risk(value: PortfolioRiskInputs | Decimal) -> Decimal:
    return score_portfolio_risk(value) if isinstance(value, PortfolioRiskInputs) else _unit(value, "risk")


def _unit(value: Decimal, field_name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value < ZERO or decimal_value > ONE:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return _quantize(decimal_value)


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal(SCORE_QUANT), rounding=ROUND_HALF_UP).normalize()
