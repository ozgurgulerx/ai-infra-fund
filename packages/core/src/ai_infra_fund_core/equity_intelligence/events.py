from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from ai_infra_fund_core.contracts.common import normalize_tuple, require_aware_datetime, require_decimal_range, require_text

from .frontier import PriorityBoost


class EquityEventType(str, Enum):
    EARNINGS_GUIDANCE = "earnings_guidance"
    ANALYST_RATING_CHANGE = "analyst_rating_change"
    AI_CAPEX_DATA_CENTER_DEMAND = "ai_capex_data_center_demand"
    GPU_ACCELERATOR_SUPPLY_CHAIN = "gpu_accelerator_supply_chain"
    PRODUCT_LAUNCH = "product_launch"
    SEMICONDUCTOR_CAPACITY = "semiconductor_capacity"
    HYPERSCALER_SPENDING = "hyperscaler_spending"
    REGULATION_EXPORT_CONTROLS = "regulation_export_controls"
    POWER_COOLING_CONSTRAINTS = "power_cooling_constraints"
    VALUATION_RATING_CHANGE = "valuation_rating_change"
    TECHNICAL_BREAKOUT_BREAKDOWN = "technical_breakout_breakdown"
    RISK_CONTROVERSY = "risk_controversy"
    EARNINGS_GUIDANCE_CHANGE = "earnings_guidance_change"
    CAPEX_SIGNAL = "capex_signal"
    ACCELERATOR_SUPPLY_SIGNAL = "accelerator_supply_signal"
    CLOUD_CAPACITY_SIGNAL = "cloud_capacity_signal"
    CUSTOMER_ADOPTION_SIGNAL = "customer_adoption_signal"
    REGULATORY_OR_EXPORT_CONTROL_SIGNAL = "regulatory_or_export_control_signal"
    PARTNERSHIP_SIGNAL = "partnership_signal"
    COMPETITIVE_POSITION_SIGNAL = "competitive_position_signal"
    DATA_CENTER_POWER_SIGNAL = "data_center_power_signal"
    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    CAPEX = "capex"
    CUSTOMER_WIN = "customer_win"
    REGULATORY = "regulatory"
    MANAGEMENT = "management"


@dataclass(frozen=True, slots=True)
class EquityEvent:
    event_id: str
    event_type: EquityEventType
    ticker: str
    source_uri: str
    observed_at: datetime
    confidence: Decimal
    summary: str
    available_at: datetime | None = None
    source_capture_id: str | None = None
    evidence_ids: tuple[str, ...] = ()
    evidence_claim_ids: tuple[str, ...] = ()
    extracted_by_model_run_id: str | None = None
    review_status: str = "deterministic"

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", require_text(self.event_id, "event_id").strip())
        object.__setattr__(self, "event_type", EquityEventType(self.event_type))
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        object.__setattr__(self, "source_uri", require_text(self.source_uri, "source_uri").strip())
        object.__setattr__(self, "confidence", require_decimal_range(self.confidence, "confidence", Decimal("0"), Decimal("1")))
        object.__setattr__(self, "summary", require_text(self.summary, "summary").strip())
        require_aware_datetime(self.observed_at, "observed_at")
        available_at = self.available_at or self.observed_at
        require_aware_datetime(available_at, "available_at")
        object.__setattr__(self, "available_at", available_at)
        object.__setattr__(self, "source_capture_id", _optional_text(self.source_capture_id, "source_capture_id"))
        object.__setattr__(self, "evidence_ids", _text_tuple(self.evidence_ids, "evidence_ids"))
        object.__setattr__(self, "evidence_claim_ids", _text_tuple(self.evidence_claim_ids, "evidence_claim_ids"))
        object.__setattr__(
            self,
            "extracted_by_model_run_id",
            _optional_text(self.extracted_by_model_run_id, "extracted_by_model_run_id"),
        )
        object.__setattr__(self, "review_status", require_text(self.review_status, "review_status").strip())

    def to_priority_boost(
        self,
        *,
        url_prefix: str,
        priority_delta: int,
        available_at: datetime,
    ) -> PriorityBoost:
        return PriorityBoost(
            reason=f"event:{self.event_type.value}:{self.event_id}",
            ticker=self.ticker,
            url_prefix=url_prefix,
            priority_delta=priority_delta,
            available_at=available_at,
        )


def _text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    return tuple(require_text(str(value), field_name).strip() for value in normalize_tuple(values, field_name))


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    text = require_text(str(value), field_name).strip()
    return text or None
