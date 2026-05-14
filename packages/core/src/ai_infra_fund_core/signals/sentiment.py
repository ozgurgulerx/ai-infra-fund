from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from ai_infra_fund_core.contracts.common import require_aware_datetime, require_text

from .formulas import SCORE_QUANT


ZERO = Decimal("0")
ONE = Decimal("1")
DEFAULT_HORIZON_DAYS = 30

SOURCE_WEIGHTS = {
    "regulatory_filing": Decimal("1.00"),
    "company_release": Decimal("0.90"),
    "earnings_call": Decimal("0.85"),
    "research_report": Decimal("0.75"),
    "news": Decimal("0.60"),
    "unknown": Decimal("0.40"),
    "social": Decimal("0.25"),
}

_DIRECTIONS = {
    "positive": Decimal("1"),
    "neutral": Decimal("0"),
    "negative": Decimal("-1"),
}


@dataclass(frozen=True, slots=True)
class SentimentEvidence:
    evidence_id: str
    source_type: str
    direction: str
    confidence: Decimal
    horizon_days: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", require_text(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "source_type", require_text(self.source_type, "source_type").lower())
        direction = require_text(self.direction, "direction").lower()
        if direction not in _DIRECTIONS:
            raise ValueError("direction must be positive, neutral, or negative")
        object.__setattr__(self, "direction", direction)
        object.__setattr__(self, "confidence", _unit(self.confidence, "confidence"))
        if self.horizon_days <= 0:
            raise ValueError("horizon_days must be positive")


@dataclass(frozen=True, slots=True)
class SentimentSnapshot:
    ticker: str
    as_of: datetime
    direction: str
    directional_score: Decimal
    confidence: Decimal
    horizon_days: int
    evidence_ids: tuple[str, ...]
    sentiment_score: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        require_aware_datetime(self.as_of, "as_of")


def compute_sentiment_snapshot(
    *,
    ticker: str,
    as_of: datetime,
    evidence: Sequence[SentimentEvidence],
) -> SentimentSnapshot:
    require_aware_datetime(as_of, "as_of")
    if not evidence:
        return SentimentSnapshot(
            ticker=ticker,
            as_of=as_of,
            direction="neutral",
            directional_score=ZERO,
            confidence=ZERO,
            horizon_days=DEFAULT_HORIZON_DAYS,
            evidence_ids=(),
            sentiment_score=Decimal("0.5"),
        )

    weighted_items = tuple((_weighted_contribution(item), item) for item in evidence)
    total_contribution = sum(contribution for contribution, _ in weighted_items)
    if total_contribution <= ZERO:
        return compute_sentiment_snapshot(ticker=ticker, as_of=as_of, evidence=[])

    raw_direction = sum(_DIRECTIONS[item.direction] * contribution for contribution, item in weighted_items) / total_contribution
    total_source_weight = sum(_source_weight(item.source_type) for item in evidence)
    confidence = total_contribution / total_source_weight if total_source_weight > ZERO else ZERO
    horizon = int(
        (sum(Decimal(item.horizon_days) * contribution for contribution, item in weighted_items) / total_contribution)
        .quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    direction = _direction_label(raw_direction)
    evidence_ids = tuple(
        item.evidence_id
        for contribution, item in sorted(weighted_items, key=lambda weighted: (-weighted[0], weighted[1].evidence_id))
    )
    sentiment_score = Decimal("0.5") + raw_direction * (confidence / Decimal("2"))

    return SentimentSnapshot(
        ticker=ticker,
        as_of=as_of,
        direction=direction,
        directional_score=_quantize(raw_direction),
        confidence=_quantize(confidence),
        horizon_days=horizon,
        evidence_ids=evidence_ids,
        sentiment_score=_quantize(_clamp(sentiment_score, ZERO, ONE)),
    )


def _weighted_contribution(item: SentimentEvidence) -> Decimal:
    return item.confidence * _source_weight(item.source_type)


def _source_weight(source_type: str) -> Decimal:
    return SOURCE_WEIGHTS.get(source_type.lower(), SOURCE_WEIGHTS["unknown"])


def _direction_label(score: Decimal) -> str:
    if score >= Decimal("0.15"):
        return "positive"
    if score <= Decimal("-0.15"):
        return "negative"
    return "neutral"


def _unit(value: Decimal, field_name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value < ZERO or decimal_value > ONE:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return decimal_value


def _clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return min(high, max(low, value))


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal(SCORE_QUANT), rounding=ROUND_HALF_UP).normalize()
