from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from ai_infra_fund_core.contracts.common import require_aware_datetime, require_decimal_range, require_text

from .frontier import PriorityBoost


class EquityEventType(str, Enum):
    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    PRODUCT_LAUNCH = "product_launch"
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

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", require_text(self.event_id, "event_id").strip())
        object.__setattr__(self, "event_type", EquityEventType(self.event_type))
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        object.__setattr__(self, "source_uri", require_text(self.source_uri, "source_uri").strip())
        object.__setattr__(self, "confidence", require_decimal_range(self.confidence, "confidence", Decimal("0"), Decimal("1")))
        object.__setattr__(self, "summary", require_text(self.summary, "summary").strip())
        require_aware_datetime(self.observed_at, "observed_at")

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
