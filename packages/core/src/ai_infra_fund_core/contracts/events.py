from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from .common import (
    coerce_enum,
    normalize_tuple,
    require_aware_datetime,
    require_content_hash,
    require_decimal_range,
    require_non_empty_tuple,
    require_text,
)
from .segments import Segment, normalize_segment, segments_from_themes


class MarketEventType(str, Enum):
    EARNINGS_GUIDANCE_CHANGE = "earnings_guidance_change"
    CAPEX_SIGNAL = "capex_signal"
    AI_PRODUCT_LAUNCH = "ai_product_launch"
    ACCELERATOR_SUPPLY_SIGNAL = "accelerator_supply_signal"
    CLOUD_CAPACITY_SIGNAL = "cloud_capacity_signal"
    CUSTOMER_ADOPTION_SIGNAL = "customer_adoption_signal"
    REGULATORY_OR_EXPORT_CONTROL_SIGNAL = "regulatory_or_export_control_signal"
    PARTNERSHIP_SIGNAL = "partnership_signal"
    COMPETITIVE_POSITION_SIGNAL = "competitive_position_signal"
    DATA_CENTER_POWER_SIGNAL = "data_center_power_signal"
    ANALYST_RATING_CHANGE = "analyst_rating_change"
    SUPPLY_CHAIN_SIGNAL = "supply_chain_signal"
    VALUATION_RATING_CHANGE = "valuation_rating_change"
    TECHNICAL_BREAKOUT_BREAKDOWN = "technical_breakout_breakdown"
    RISK_CONTROVERSY = "risk_controversy"


class MarketEventDirection(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class MarketEventReviewStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    USABLE = "usable"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


@dataclass(frozen=True, slots=True)
class MarketEvent:
    event_id: str
    event_type: MarketEventType
    source_evidence_ids: tuple[str, ...]
    tickers: tuple[str, ...]
    companies: tuple[str, ...]
    themes: tuple[str, ...]
    catalyst: str
    ai_relevance: str
    direction: MarketEventDirection
    time_horizon: str
    confidence: Decimal
    occurred_at: datetime
    available_at: datetime
    content_hash: str
    extracted_by_model_run_id: str | None
    review_status: MarketEventReviewStatus

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", require_text(self.event_id, "event_id").strip())
        object.__setattr__(self, "event_type", coerce_enum(self.event_type, MarketEventType, "event_type"))
        object.__setattr__(self, "source_evidence_ids", _required_text_tuple(self.source_evidence_ids, "source_evidence_ids"))
        object.__setattr__(self, "tickers", _required_text_tuple(self.tickers, "tickers", uppercase=True))
        object.__setattr__(self, "companies", _required_text_tuple(self.companies, "companies"))
        object.__setattr__(self, "themes", _required_text_tuple(self.themes, "themes"))
        segments_from_themes(self.themes)
        object.__setattr__(self, "catalyst", require_text(self.catalyst, "catalyst").strip())
        object.__setattr__(self, "ai_relevance", require_text(self.ai_relevance, "ai_relevance").strip())
        object.__setattr__(self, "direction", coerce_enum(self.direction, MarketEventDirection, "direction"))
        object.__setattr__(self, "time_horizon", require_text(self.time_horizon, "time_horizon").strip())
        object.__setattr__(
            self,
            "confidence",
            require_decimal_range(self.confidence, "confidence", Decimal("0"), Decimal("1")),
        )
        if self.occurred_at is None:
            raise ValueError("occurred_at is required")
        if self.available_at is None:
            raise ValueError("available_at is required")
        occurred_at = require_aware_datetime(self.occurred_at, "occurred_at")
        available_at = require_aware_datetime(self.available_at, "available_at")
        if available_at < occurred_at:
            raise ValueError("available_at must be greater than or equal to occurred_at")
        object.__setattr__(self, "content_hash", require_content_hash(self.content_hash))
        object.__setattr__(
            self,
            "extracted_by_model_run_id",
            _optional_text(self.extracted_by_model_run_id, "extracted_by_model_run_id"),
        )
        object.__setattr__(self, "review_status", coerce_enum(self.review_status, MarketEventReviewStatus, "review_status"))

    @property
    def segments(self) -> tuple[Segment, ...]:
        return segments_from_themes(self.themes)


@dataclass(frozen=True, slots=True)
class SegmentImpact:
    segment_id: Segment
    segment_name: str
    linked_event_ids: tuple[str, ...]
    primary_tickers: tuple[str, ...]
    first_order_tickers: tuple[str, ...]
    second_order_tickers: tuple[str, ...]
    impact_direction: MarketEventDirection
    impact_summary: str
    confidence: Decimal
    time_horizon: str
    risk_flags: tuple[str, ...]
    invalidation_condition: str
    latest_evidence_at: datetime
    signal_bundle_id: str | None
    source_evidence_ids: tuple[str, ...]
    model_run_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "segment_id", normalize_segment(self.segment_id))
        object.__setattr__(self, "segment_name", require_text(self.segment_name, "segment_name").strip())
        object.__setattr__(self, "linked_event_ids", _required_text_tuple(self.linked_event_ids, "linked_event_ids"))
        object.__setattr__(self, "primary_tickers", _required_text_tuple(self.primary_tickers, "primary_tickers", uppercase=True))
        object.__setattr__(self, "first_order_tickers", _required_text_tuple(self.first_order_tickers, "first_order_tickers", uppercase=True))
        object.__setattr__(self, "second_order_tickers", _required_text_tuple(self.second_order_tickers, "second_order_tickers", uppercase=True))
        object.__setattr__(self, "impact_direction", coerce_enum(self.impact_direction, MarketEventDirection, "impact_direction"))
        object.__setattr__(self, "impact_summary", require_text(self.impact_summary, "impact_summary").strip())
        object.__setattr__(
            self,
            "confidence",
            require_decimal_range(self.confidence, "confidence", Decimal("0"), Decimal("1")),
        )
        object.__setattr__(self, "time_horizon", require_text(self.time_horizon, "time_horizon").strip())
        object.__setattr__(self, "risk_flags", _required_text_tuple(self.risk_flags, "risk_flags"))
        object.__setattr__(self, "invalidation_condition", require_text(self.invalidation_condition, "invalidation_condition").strip())
        object.__setattr__(self, "latest_evidence_at", require_aware_datetime(self.latest_evidence_at, "latest_evidence_at"))
        object.__setattr__(self, "signal_bundle_id", _optional_text(self.signal_bundle_id, "signal_bundle_id"))
        object.__setattr__(self, "source_evidence_ids", _required_text_tuple(self.source_evidence_ids, "source_evidence_ids"))
        object.__setattr__(self, "model_run_ids", _optional_text_tuple(self.model_run_ids, "model_run_ids"))


@dataclass(frozen=True, slots=True)
class EquityImpactAssessment:
    assessment_id: str
    ticker: str
    company: str
    linked_event_ids: tuple[str, ...]
    segment_ids: tuple[Segment, ...]
    assessment: str
    bull_case: str
    base_case: str
    bear_case: str
    risk_flags: tuple[str, ...]
    invalidation_condition: str
    watch_items: tuple[str, ...]
    advisory_implication: str
    confidence: Decimal
    as_of: datetime
    source_evidence_ids: tuple[str, ...]
    linked_signal_bundle_id: str | None
    linked_recommendation_artifact_id: str | None
    model_run_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "assessment_id", require_text(self.assessment_id, "assessment_id").strip())
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").strip().upper())
        object.__setattr__(self, "company", require_text(self.company, "company").strip())
        object.__setattr__(self, "linked_event_ids", _required_text_tuple(self.linked_event_ids, "linked_event_ids"))
        object.__setattr__(self, "segment_ids", _required_segment_tuple(self.segment_ids, "segment_ids"))
        object.__setattr__(self, "assessment", require_text(self.assessment, "assessment").strip())
        object.__setattr__(self, "bull_case", require_text(self.bull_case, "bull_case").strip())
        object.__setattr__(self, "base_case", require_text(self.base_case, "base_case").strip())
        object.__setattr__(self, "bear_case", require_text(self.bear_case, "bear_case").strip())
        object.__setattr__(self, "risk_flags", _required_text_tuple(self.risk_flags, "risk_flags"))
        object.__setattr__(self, "invalidation_condition", require_text(self.invalidation_condition, "invalidation_condition").strip())
        object.__setattr__(self, "watch_items", _required_text_tuple(self.watch_items, "watch_items"))
        object.__setattr__(self, "advisory_implication", require_text(self.advisory_implication, "advisory_implication").strip())
        object.__setattr__(
            self,
            "confidence",
            require_decimal_range(self.confidence, "confidence", Decimal("0"), Decimal("1")),
        )
        object.__setattr__(self, "as_of", require_aware_datetime(self.as_of, "as_of"))
        object.__setattr__(self, "source_evidence_ids", _required_text_tuple(self.source_evidence_ids, "source_evidence_ids"))
        object.__setattr__(self, "linked_signal_bundle_id", _optional_text(self.linked_signal_bundle_id, "linked_signal_bundle_id"))
        object.__setattr__(
            self,
            "linked_recommendation_artifact_id",
            _optional_text(self.linked_recommendation_artifact_id, "linked_recommendation_artifact_id"),
        )
        object.__setattr__(self, "model_run_ids", _required_text_tuple(self.model_run_ids, "model_run_ids"))


def _required_text_tuple(values: object, field_name: str, *, uppercase: bool = False) -> tuple[str, ...]:
    normalized = require_non_empty_tuple(normalize_tuple(values, field_name), field_name)
    text_values = tuple(require_text(str(value), field_name).strip() for value in normalized)
    if uppercase:
        return tuple(value.upper() for value in text_values)
    return text_values


def _required_segment_tuple(values: object, field_name: str) -> tuple[Segment, ...]:
    normalized = require_non_empty_tuple(normalize_tuple(values, field_name), field_name)
    return tuple(normalize_segment(value) for value in normalized)


def _optional_text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    return tuple(require_text(str(value), field_name).strip() for value in normalize_tuple(values, field_name))


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return require_text(str(value), field_name).strip()
