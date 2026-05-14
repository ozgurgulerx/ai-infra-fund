from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ai_infra_fund_core.contracts.common import (
    DataClass,
    require_aware_datetime,
    require_text,
    stable_hash_payload,
)
from ai_infra_fund_core.local_inputs.watchlist import AIEquityWatchlist
from ai_infra_fund_core.model_routing.router import ModelRouter


DEEP_RESEARCH_TASK_ROLES = ("evidence_summary", "adversarial_review")


@dataclass(frozen=True, slots=True)
class MonitoringCadencePolicy:
    critical: timedelta = timedelta(hours=6)
    high: timedelta = timedelta(hours=12)
    medium: timedelta = timedelta(hours=24)
    low: timedelta = timedelta(hours=24)

    def __post_init__(self) -> None:
        for field_name in ("critical", "high", "medium", "low"):
            if getattr(self, field_name) <= timedelta(0):
                raise ValueError(f"{field_name} cadence must be positive")

    def cadence_for_priority(self, priority: str) -> timedelta:
        normalized = require_text(priority, "priority").lower()
        try:
            return getattr(self, normalized)
        except AttributeError as exc:
            raise ValueError("priority must be one of critical, high, medium, low") from exc


@dataclass(frozen=True, slots=True)
class DeepResearchTask:
    ticker: str
    company_name: str
    themes: tuple[str, ...]
    task_roles: tuple[str, ...]
    data_classes: tuple[DataClass, ...]
    model_profile_ids: tuple[str, ...]
    fallback_profile_ids: tuple[str, ...]
    evidence_source_urls: tuple[str, ...]
    due_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        object.__setattr__(
            self,
            "company_name",
            require_text(self.company_name, "company_name").strip(),
        )
        object.__setattr__(self, "themes", _text_tuple(self.themes, "themes"))
        object.__setattr__(self, "task_roles", _text_tuple(self.task_roles, "task_roles"))
        object.__setattr__(
            self,
            "model_profile_ids",
            _text_tuple(self.model_profile_ids, "model_profile_ids"),
        )
        object.__setattr__(
            self,
            "fallback_profile_ids",
            _text_tuple(self.fallback_profile_ids, "fallback_profile_ids"),
        )
        object.__setattr__(
            self,
            "evidence_source_urls",
            _text_tuple(self.evidence_source_urls, "evidence_source_urls"),
        )
        require_aware_datetime(self.due_at, "due_at")
        if not self.data_classes:
            raise ValueError("data_classes must not be empty")


@dataclass(frozen=True, slots=True)
class MonitoredEquity:
    ticker: str
    company_name: str
    themes: tuple[str, ...]
    priority: str
    monitor_every: timedelta
    next_refresh_at: datetime
    refresh_reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        object.__setattr__(
            self,
            "company_name",
            require_text(self.company_name, "company_name").strip(),
        )
        object.__setattr__(self, "themes", _text_tuple(self.themes, "themes"))
        object.__setattr__(self, "priority", require_text(self.priority, "priority").lower())
        if self.monitor_every <= timedelta(0):
            raise ValueError("monitor_every must be positive")
        require_aware_datetime(self.next_refresh_at, "next_refresh_at")
        object.__setattr__(self, "refresh_reason", require_text(self.refresh_reason, "refresh_reason").strip())


@dataclass(frozen=True, slots=True)
class RefreshJobPlan:
    refresh_job_id: str
    ticker: str
    reason: str
    priority_boost: int
    requested_at: datetime
    status: str = "queued"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "refresh_job_id",
            require_text(self.refresh_job_id, "refresh_job_id").strip(),
        )
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        object.__setattr__(self, "reason", require_text(self.reason, "reason").strip())
        if self.priority_boost <= 0:
            raise ValueError("priority_boost must be positive")
        require_aware_datetime(self.requested_at, "requested_at")
        object.__setattr__(self, "status", require_text(self.status, "status").strip())


@dataclass(frozen=True, slots=True)
class ThemeResearchGroup:
    theme: str
    tickers: tuple[str, ...]
    priority: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "theme", require_text(self.theme, "theme").strip())
        object.__setattr__(
            self,
            "tickers",
            _text_tuple(tuple(ticker.upper() for ticker in self.tickers), "tickers"),
        )
        object.__setattr__(self, "priority", require_text(self.priority, "priority").lower())


@dataclass(frozen=True, slots=True)
class ResearchMonitoringPlan:
    as_of: datetime
    equities: tuple[MonitoredEquity, ...]
    theme_groups: tuple[ThemeResearchGroup, ...]
    deep_research_tasks: tuple[DeepResearchTask, ...]
    refresh_jobs: tuple[RefreshJobPlan, ...]

    def __post_init__(self) -> None:
        require_aware_datetime(self.as_of, "as_of")


def build_research_monitoring_plan(
    watchlist: AIEquityWatchlist,
    *,
    as_of: datetime,
    router: ModelRouter,
    cadence_policy: MonitoringCadencePolicy | None = None,
) -> ResearchMonitoringPlan:
    require_aware_datetime(as_of, "as_of")
    policy = cadence_policy or MonitoringCadencePolicy()
    equities = tuple(
        _monitored_equity(entry, as_of=as_of, cadence_policy=policy)
        for entry in watchlist.entries
    )
    tasks = tuple(_deep_research_task(entry, as_of=as_of, router=router) for entry in watchlist.entries)
    refresh_jobs = tuple(_refresh_job(entry, as_of=as_of) for entry in watchlist.entries)
    groups = _theme_groups(equities)
    return ResearchMonitoringPlan(
        as_of=as_of,
        equities=equities,
        theme_groups=groups,
        deep_research_tasks=tasks,
        refresh_jobs=refresh_jobs,
    )


def _monitored_equity(
    entry: object,
    *,
    as_of: datetime,
    cadence_policy: MonitoringCadencePolicy,
) -> MonitoredEquity:
    return MonitoredEquity(
        ticker=getattr(entry, "ticker"),
        company_name=getattr(entry, "company_name"),
        themes=getattr(entry, "themes"),
        priority=getattr(entry, "priority"),
        monitor_every=cadence_policy.cadence_for_priority(getattr(entry, "priority")),
        next_refresh_at=as_of,
        refresh_reason=f"watchlist_{getattr(entry, 'priority')}_continuous_monitoring",
    )


def _deep_research_task(entry: object, *, as_of: datetime, router: ModelRouter) -> DeepResearchTask:
    data_classes = (DataClass.PUBLIC_EVIDENCE,)
    routes = tuple(router.resolve(role, data_classes=data_classes) for role in DEEP_RESEARCH_TASK_ROLES)
    return DeepResearchTask(
        ticker=getattr(entry, "ticker"),
        company_name=getattr(entry, "company_name"),
        themes=getattr(entry, "themes"),
        task_roles=DEEP_RESEARCH_TASK_ROLES,
        data_classes=data_classes,
        model_profile_ids=_unique(route.profile.profile_id for route in routes),
        fallback_profile_ids=_unique(
            profile.profile_id
            for route in routes
            for profile in route.fallback_chain
        ),
        evidence_source_urls=getattr(entry, "source_urls"),
        due_at=as_of,
    )


def _refresh_job(entry: object, *, as_of: datetime) -> RefreshJobPlan:
    ticker = require_text(getattr(entry, "ticker"), "ticker").upper()
    priority = require_text(getattr(entry, "priority"), "priority").lower()
    reason = f"continuous_monitoring:{priority}:deep_research"
    job_hash = stable_hash_payload({"as_of": as_of, "reason": reason, "ticker": ticker})
    return RefreshJobPlan(
        refresh_job_id=f"refresh-{ticker.lower()}-{job_hash[:16]}",
        ticker=ticker,
        reason=reason,
        priority_boost=_priority_boost(priority),
        requested_at=as_of,
    )


def _theme_groups(equities: tuple[MonitoredEquity, ...]) -> tuple[ThemeResearchGroup, ...]:
    tickers_by_theme: dict[str, set[str]] = {}
    priority_by_theme: dict[str, str] = {}
    for equity in equities:
        for theme in equity.themes:
            tickers_by_theme.setdefault(theme, set()).add(equity.ticker)
            priority_by_theme[theme] = _higher_priority(priority_by_theme.get(theme), equity.priority)
    return tuple(
        ThemeResearchGroup(theme=theme, tickers=tuple(sorted(tickers)), priority=priority_by_theme[theme])
        for theme, tickers in sorted(tickers_by_theme.items())
    )


def _higher_priority(current: str | None, candidate: str) -> str:
    if current is None:
        return candidate
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    return candidate if order[candidate] > order[current] else current


def _priority_boost(priority: str) -> int:
    boosts = {"critical": 40, "high": 25, "medium": 15, "low": 5}
    try:
        return boosts[priority]
    except KeyError as exc:
        raise ValueError("priority must be one of critical, high, medium, low") from exc


def _unique(values: object) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = require_text(str(value), "value").strip()
        if text not in seen:
            ordered.append(text)
            seen.add(text)
    return tuple(ordered)


def _text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ValueError(f"{field_name} must be an iterable, not a string")
    normalized = tuple(require_text(str(value), field_name).strip() for value in values)
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized
