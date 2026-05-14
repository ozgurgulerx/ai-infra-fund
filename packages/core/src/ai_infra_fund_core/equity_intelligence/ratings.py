from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from ai_infra_fund_core.contracts.common import (
    AdvisoryLabel,
    require_aware_datetime,
    require_decimal_range,
    require_text,
)


class DynamicRatingLabel(str, Enum):
    STRONG_POSITIVE = "strong_positive"
    POSITIVE = "positive"
    NEUTRAL_WATCH = "neutral_watch"
    NEGATIVE_WATCH = "negative_watch"
    CRITICAL_REVIEW = "critical_review"


@dataclass(frozen=True, slots=True)
class DynamicRatingInput:
    ticker: str
    as_of: datetime
    evidence_ids: tuple[str, ...]
    model_run_ids: tuple[str, ...]
    event_confidence: Decimal
    sentiment_score: Decimal
    technical_trend_label: str
    fundamental_rating_label: str
    llm_review_status: str = "deterministic"

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        require_aware_datetime(self.as_of, "as_of")
        object.__setattr__(self, "evidence_ids", _text_tuple(self.evidence_ids, "evidence_ids"))
        object.__setattr__(
            self,
            "model_run_ids",
            _optional_text_tuple(self.model_run_ids, "model_run_ids"),
        )
        object.__setattr__(
            self,
            "event_confidence",
            require_decimal_range(self.event_confidence, "event_confidence", Decimal("0"), Decimal("1")),
        )
        object.__setattr__(
            self,
            "sentiment_score",
            require_decimal_range(self.sentiment_score, "sentiment_score", Decimal("-1"), Decimal("1")),
        )
        object.__setattr__(
            self,
            "technical_trend_label",
            require_text(self.technical_trend_label, "technical_trend_label").lower(),
        )
        object.__setattr__(
            self,
            "fundamental_rating_label",
            require_text(self.fundamental_rating_label, "fundamental_rating_label").lower(),
        )
        object.__setattr__(
            self,
            "llm_review_status",
            require_text(self.llm_review_status, "llm_review_status").strip(),
        )
        if self.llm_review_status == "model_extracted" and not self.model_run_ids:
            raise ValueError("model_run_ids are required for model_extracted rating inputs")


@dataclass(frozen=True, slots=True)
class DynamicRatingUpdate:
    ticker: str
    as_of: datetime
    rating_label: DynamicRatingLabel
    rating_score: Decimal
    drivers: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    model_run_ids: tuple[str, ...]
    advisory_label: AdvisoryLabel = AdvisoryLabel.ADVISORY_ONLY
    generated_by: str = "deterministic_llm_lineage_policy_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        require_aware_datetime(self.as_of, "as_of")
        object.__setattr__(self, "rating_label", DynamicRatingLabel(self.rating_label))
        object.__setattr__(
            self,
            "rating_score",
            require_decimal_range(self.rating_score, "rating_score", Decimal("0"), Decimal("1")),
        )
        object.__setattr__(self, "drivers", _text_tuple(self.drivers, "drivers"))
        object.__setattr__(self, "evidence_ids", _text_tuple(self.evidence_ids, "evidence_ids"))
        object.__setattr__(
            self,
            "model_run_ids",
            _optional_text_tuple(self.model_run_ids, "model_run_ids"),
        )
        object.__setattr__(self, "advisory_label", AdvisoryLabel(self.advisory_label))
        object.__setattr__(self, "generated_by", require_text(self.generated_by, "generated_by").strip())


def derive_dynamic_rating(rating_input: DynamicRatingInput) -> DynamicRatingUpdate:
    sentiment_component = (rating_input.sentiment_score + Decimal("1")) / Decimal("2")
    trend_component = _trend_component(rating_input.technical_trend_label)
    fundamental_component = _fundamental_component(rating_input.fundamental_rating_label)
    rating_score = (
        Decimal("0.35") * rating_input.event_confidence
        + Decimal("0.25") * sentiment_component
        + Decimal("0.20") * trend_component
        + Decimal("0.20") * fundamental_component
    ).quantize(Decimal("0.0001"))

    return DynamicRatingUpdate(
        ticker=rating_input.ticker,
        as_of=rating_input.as_of,
        rating_label=_label_for_score(rating_score),
        rating_score=rating_score,
        drivers=(
            f"event_confidence:{rating_input.event_confidence}",
            f"sentiment_score:{rating_input.sentiment_score}",
            f"technical_trend:{rating_input.technical_trend_label}",
            f"fundamental_rating:{rating_input.fundamental_rating_label}",
            f"llm_review_status:{rating_input.llm_review_status}",
        ),
        evidence_ids=rating_input.evidence_ids,
        model_run_ids=rating_input.model_run_ids,
    )


def _trend_component(label: str) -> Decimal:
    normalized = label.lower()
    if normalized in {"uptrend", "breakout", "positive", "bullish"}:
        return Decimal("0.85")
    if normalized in {"downtrend", "breakdown", "negative", "bearish"}:
        return Decimal("0.20")
    if normalized in {"risk", "volatile", "choppy"}:
        return Decimal("0.35")
    return Decimal("0.50")


def _fundamental_component(label: str) -> Decimal:
    normalized = label.lower()
    if normalized in {"compounder", "outperform", "strong_positive", "positive"}:
        return Decimal("0.85")
    if normalized in {"hold", "stable", "neutral", "neutral_watch"}:
        return Decimal("0.55")
    if normalized in {"watch", "mixed"}:
        return Decimal("0.45")
    if normalized in {"avoid", "negative", "critical_review", "risk"}:
        return Decimal("0.20")
    return Decimal("0.50")


def _label_for_score(score: Decimal) -> DynamicRatingLabel:
    if score >= Decimal("0.75"):
        return DynamicRatingLabel.STRONG_POSITIVE
    if score >= Decimal("0.60"):
        return DynamicRatingLabel.POSITIVE
    if score >= Decimal("0.45"):
        return DynamicRatingLabel.NEUTRAL_WATCH
    if score >= Decimal("0.30"):
        return DynamicRatingLabel.NEGATIVE_WATCH
    return DynamicRatingLabel.CRITICAL_REVIEW


def _text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    normalized = _optional_text_tuple(values, field_name)
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _optional_text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        raise ValueError(f"{field_name} must be an iterable, not a string")
    return tuple(require_text(str(value), field_name).strip() for value in values)
