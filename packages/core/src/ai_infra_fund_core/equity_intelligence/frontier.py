from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from ai_infra_fund_core.contracts.common import require_aware_datetime, require_text

from .sources import SourcePolicy
from .urls import canonicalize_url


BLOCKED_AVAILABLE_AT = datetime.max.replace(tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class FrontierPolicy:
    batch_size: int = 20
    domain_cap: int = 2
    lease_duration: timedelta = timedelta(minutes=15)
    max_retries: int = 3
    backoff_base: timedelta = timedelta(minutes=5)

    def __post_init__(self) -> None:
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.domain_cap <= 0:
            raise ValueError("domain_cap must be positive")
        if self.lease_duration <= timedelta(0):
            raise ValueError("lease_duration must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.backoff_base <= timedelta(0):
            raise ValueError("backoff_base must be positive")


@dataclass(frozen=True, slots=True)
class PriorityBoost:
    reason: str
    ticker: str | None
    url_prefix: str
    priority_delta: int
    available_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason", require_text(self.reason, "reason").strip())
        object.__setattr__(self, "ticker", None if self.ticker is None else require_text(self.ticker, "ticker").upper())
        object.__setattr__(self, "url_prefix", canonicalize_url(self.url_prefix).canonical_url)
        if self.priority_delta <= 0:
            raise ValueError("priority_delta must be positive")
        require_aware_datetime(self.available_at, "available_at")


@dataclass(frozen=True, slots=True)
class CrawlTarget:
    raw_url: str
    canonical_url: str
    domain: str
    path: str
    source_policy: SourcePolicy
    page_type: str
    priority_score: int
    discovered_at: datetime
    next_crawl_at: datetime | None = None
    content_hash: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    last_status_code: int | None = None
    last_fetch_method: str | None = None
    quality_score: float | None = None
    failure_count: int = 0
    blocked: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw_url", require_text(self.raw_url, "raw_url").strip())
        object.__setattr__(self, "canonical_url", require_text(self.canonical_url, "canonical_url").strip())
        object.__setattr__(self, "domain", require_text(self.domain, "domain").strip())
        object.__setattr__(self, "path", require_text(self.path, "path").strip())
        object.__setattr__(self, "page_type", require_text(self.page_type, "page_type").strip())
        if self.priority_score < 0:
            raise ValueError("priority_score must be non-negative")
        if self.failure_count < 0:
            raise ValueError("failure_count must be non-negative")
        require_aware_datetime(self.discovered_at, "discovered_at")
        if self.next_crawl_at is not None:
            require_aware_datetime(self.next_crawl_at, "next_crawl_at")


@dataclass(frozen=True, slots=True)
class CrawlQueueItem:
    canonical_url: str
    domain: str
    available_at: datetime
    priority_score: int = 0
    leased_at: datetime | None = None
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    lease_attempts: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_url", require_text(self.canonical_url, "canonical_url").strip())
        object.__setattr__(self, "domain", require_text(self.domain, "domain").strip())
        require_aware_datetime(self.available_at, "available_at")
        if self.priority_score < 0:
            raise ValueError("priority_score must be non-negative")
        if self.leased_at is not None:
            require_aware_datetime(self.leased_at, "leased_at")
        if self.lease_expires_at is not None:
            require_aware_datetime(self.lease_expires_at, "lease_expires_at")
        if self.lease_attempts < 0:
            raise ValueError("lease_attempts must be non-negative")

    @classmethod
    def from_target(cls, target: CrawlTarget, *, available_at: datetime | None = None) -> CrawlQueueItem:
        return cls(
            canonical_url=target.canonical_url,
            domain=target.domain,
            available_at=available_at or target.next_crawl_at or target.discovered_at,
            priority_score=target.priority_score,
        )

    def lease(self, *, owner: str, leased_at: datetime, lease_duration: timedelta) -> CrawlQueueItem:
        require_aware_datetime(leased_at, "leased_at")
        return replace(
            self,
            leased_at=leased_at,
            lease_owner=require_text(owner, "lease_owner").strip(),
            lease_expires_at=leased_at + lease_duration,
            lease_attempts=self.lease_attempts + 1,
        )

    def release(self, *, available_at: datetime) -> CrawlQueueItem:
        require_aware_datetime(available_at, "available_at")
        return replace(
            self,
            available_at=available_at,
            leased_at=None,
            lease_owner=None,
            lease_expires_at=None,
        )

    def is_due(self, as_of: datetime) -> bool:
        require_aware_datetime(as_of, "as_of")
        if self.available_at > as_of:
            return False
        if self.lease_owner is None:
            return True
        return self.lease_expires_at is not None and self.lease_expires_at <= as_of


@dataclass(frozen=True, slots=True)
class ClaimResult:
    items: tuple[CrawlQueueItem, ...]
    queue: tuple[CrawlQueueItem, ...]


def seed_crawl_target(
    raw_url: str,
    *,
    source_policy: SourcePolicy,
    page_type: str,
    base_priority: int,
    discovered_at: datetime,
) -> CrawlTarget:
    canonical = canonicalize_url(raw_url)
    return CrawlTarget(
        raw_url=canonical.raw_url,
        canonical_url=canonical.canonical_url,
        domain=canonical.domain,
        path=canonical.path,
        source_policy=source_policy,
        page_type=page_type,
        priority_score=base_priority,
        discovered_at=discovered_at,
        next_crawl_at=discovered_at,
    )


def apply_priority_boosts(
    targets: tuple[CrawlTarget, ...],
    boosts: tuple[PriorityBoost, ...],
) -> tuple[CrawlTarget, ...]:
    boosted_targets: list[CrawlTarget] = []
    for target in targets:
        priority_delta = sum(
            boost.priority_delta
            for boost in boosts
            if target.canonical_url.startswith(boost.url_prefix)
        )
        available_at = min(
            (boost.available_at for boost in boosts if target.canonical_url.startswith(boost.url_prefix)),
            default=target.next_crawl_at,
        )
        boosted_targets.append(
            replace(
                target,
                priority_score=target.priority_score + priority_delta,
                next_crawl_at=available_at,
            )
        )
    return tuple(boosted_targets)


def claim_due_targets(
    queue: tuple[CrawlQueueItem, ...],
    *,
    as_of: datetime,
    lease_owner: str,
    policy: FrontierPolicy,
) -> ClaimResult:
    require_aware_datetime(as_of, "as_of")
    claimed_by_url: dict[str, CrawlQueueItem] = {}
    domain_counts: dict[str, int] = {}
    due_rows = sorted(
        (row for row in queue if row.is_due(as_of)),
        key=lambda item: (-item.priority_score, item.available_at, item.domain, item.canonical_url),
    )
    for row in due_rows:
        if len(claimed_by_url) >= policy.batch_size:
            continue
        if domain_counts.get(row.domain, 0) >= policy.domain_cap:
            continue
        leased = row.lease(owner=lease_owner, leased_at=as_of, lease_duration=policy.lease_duration)
        claimed_by_url[row.canonical_url] = leased
        domain_counts[row.domain] = domain_counts.get(row.domain, 0) + 1

    updated_queue = tuple(claimed_by_url.get(row.canonical_url, row) for row in queue)
    return ClaimResult(items=tuple(claimed_by_url.values()), queue=updated_queue)


def record_crawl_success(
    target: CrawlTarget,
    queue_item: CrawlQueueItem,
    *,
    fetched_at: datetime,
    content_hash: str,
    status_code: int,
    recrawl_after: timedelta,
    fetch_method: str = "stub",
) -> tuple[CrawlTarget, CrawlQueueItem]:
    require_aware_datetime(fetched_at, "fetched_at")
    if recrawl_after <= timedelta(0):
        raise ValueError("recrawl_after must be positive")
    updated_target = replace(
        target,
        content_hash=require_text(content_hash, "content_hash").strip(),
        last_status_code=status_code,
        last_fetch_method=require_text(fetch_method, "fetch_method").strip(),
        next_crawl_at=fetched_at + recrawl_after,
        failure_count=0,
        blocked=False,
    )
    return updated_target, queue_item.release(available_at=updated_target.next_crawl_at)


def record_crawl_failure(
    target: CrawlTarget,
    queue_item: CrawlQueueItem,
    *,
    failed_at: datetime,
    status_code: int | None,
    error_code: str,
    policy: FrontierPolicy,
) -> tuple[CrawlTarget, CrawlQueueItem]:
    require_aware_datetime(failed_at, "failed_at")
    require_text(error_code, "error_code")
    failure_count = target.failure_count + 1
    blocked = failure_count >= policy.max_retries
    available_at = BLOCKED_AVAILABLE_AT if blocked else failed_at + policy.backoff_base * (2 ** (failure_count - 1))
    updated_target = replace(
        target,
        failure_count=failure_count,
        last_status_code=status_code,
        last_fetch_method=f"error:{error_code}",
        blocked=blocked,
        next_crawl_at=available_at,
    )
    return updated_target, queue_item.release(available_at=available_at)
