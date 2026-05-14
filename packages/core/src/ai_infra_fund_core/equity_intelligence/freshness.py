from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from ai_infra_fund_core.contracts.common import require_aware_datetime


class FreshnessStatus(str, Enum):
    NEW = "new"
    FRESH = "fresh"
    DUE = "due"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    max_age: timedelta
    stale_after: timedelta

    def __post_init__(self) -> None:
        if self.max_age <= timedelta(0):
            raise ValueError("max_age must be positive")
        if self.stale_after < self.max_age:
            raise ValueError("stale_after must be greater than or equal to max_age")


@dataclass(frozen=True, slots=True)
class FreshnessAssessment:
    status: FreshnessStatus
    age: timedelta | None
    due: bool


def assess_freshness(
    *,
    last_crawled_at: datetime | None,
    next_crawl_at: datetime | None,
    as_of: datetime,
    policy: FreshnessPolicy,
) -> FreshnessAssessment:
    require_aware_datetime(as_of, "as_of")
    if last_crawled_at is None:
        return FreshnessAssessment(status=FreshnessStatus.NEW, age=None, due=True)

    require_aware_datetime(last_crawled_at, "last_crawled_at")
    if next_crawl_at is not None:
        require_aware_datetime(next_crawl_at, "next_crawl_at")

    age = as_of - last_crawled_at
    due = next_crawl_at is None or next_crawl_at <= as_of or age >= policy.max_age
    if age >= policy.stale_after:
        status = FreshnessStatus.STALE
    elif due:
        status = FreshnessStatus.DUE
    else:
        status = FreshnessStatus.FRESH
    return FreshnessAssessment(status=status, age=age, due=due)
