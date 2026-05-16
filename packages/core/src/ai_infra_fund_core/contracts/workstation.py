from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from .common import (
    AdvisoryLabel,
    DataClass,
    coerce_enum,
    normalize_tuple,
    require_aware_datetime,
    require_content_hash,
    require_decimal_range,
    require_non_empty_tuple,
    require_non_negative,
    require_positive,
    require_text,
)


class AnalystAction(str, Enum):
    WATCH = "watch"
    ACCUMULATE = "accumulate"
    HOLD = "hold"
    TRIM = "trim"
    AVOID = "avoid"
    REVIEW = "review"


class AdvisoryChangeDirection(str, Enum):
    STRENGTHENED = "strengthened"
    WEAKENED = "weakened"
    UNCHANGED = "unchanged"
    MIXED = "mixed"
    REVIEW_NEEDED = "review_needed"


class OutcomeLabel(str, Enum):
    OPEN = "open"
    WON = "won"
    LOST = "lost"
    NEUTRAL = "neutral"
    INVALIDATED = "invalidated"
    REVIEW_NEEDED = "review_needed"


class RiskRegimeType(str, Enum):
    MACRO_RATES = "macro_rates"
    LIQUIDITY = "liquidity"
    AI_CAPEX = "ai_capex"
    POWER_GRID = "power_grid"
    SUPPLY_CHAIN = "supply_chain"
    EXPORT_CONTROLS = "export_controls"
    VALUATION = "valuation"
    PORTFOLIO = "portfolio"
    GEOPOLITICAL = "geopolitical"


class RiskRegimeStatus(str, Enum):
    NORMAL = "normal"
    WATCH = "watch"
    ELEVATED = "elevated"
    STRESSED = "stressed"
    IMPROVING = "improving"
    REVIEW_NEEDED = "review_needed"


class TradePlanStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"
    INVALIDATED = "invalidated"
    RETIRED = "retired"


class TradePlanReadiness(str, Enum):
    READY = "ready"
    BLOCKED = "blocked"
    REVIEW_NEEDED = "review_needed"
    STALE_DATA = "stale_data"


class LLMNoteReviewStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


REQUIRED_SCENARIOS = frozenset({"bear", "base", "bull"})
FORBIDDEN_OBJECT_FIELD_TERMS = frozenset({"broker", "route", "exchange", "order", "execution", "auto_trade"})
ALLOWED_LLM_ANALYST_ROLES = frozenset(
    {
        "source_signal_monitor",
        "market_event_extractor",
        "market_event_reviewer",
        "fundamental_snapshot_reviewer",
        "valuation_context_analyst",
        "macro_regime_reviewer",
        "segment_mapper",
        "segment_mapping_reviewer",
        "equity_thesis_analyst",
        "risk_regime_reviewer",
        "trading_advisory_synthesizer",
        "trade_plan_critic",
        "portfolio_exposure_explainer",
        "brief_synthesizer",
        "outcome_reviewer",
        "llm_note_reviewer",
    }
)
FORBIDDEN_ACTION_PHRASES = frozenset(
    {
        "place an order",
        "submit an order",
        "execute a trade",
        "route to broker",
        "broker credentials",
        "order ticket",
        "start live trading",
    }
)


@dataclass(frozen=True, slots=True)
class SourceSignal:
    signal_id: str
    source_type: str
    source_uri: str
    publisher: str
    captured_at: datetime
    available_at: datetime
    tickers: tuple[str, ...]
    themes: tuple[str, ...]
    segments: tuple[str, ...]
    raw_summary: str
    data_class: DataClass
    content_hash: str
    evidence_id: str
    confidence: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "signal_id", _required_text(self.signal_id, "signal_id"))
        object.__setattr__(self, "source_type", _required_text(self.source_type, "source_type"))
        object.__setattr__(self, "source_uri", _required_text(self.source_uri, "source_uri"))
        object.__setattr__(self, "publisher", _required_text(self.publisher, "publisher"))
        captured_at = require_aware_datetime(self.captured_at, "captured_at")
        available_at = require_aware_datetime(self.available_at, "available_at")
        if available_at < captured_at:
            raise ValueError("available_at must be greater than or equal to captured_at")
        object.__setattr__(self, "tickers", _required_text_tuple(self.tickers, "tickers", uppercase=True))
        object.__setattr__(self, "themes", _required_text_tuple(self.themes, "themes"))
        object.__setattr__(self, "segments", _required_text_tuple(self.segments, "segments"))
        object.__setattr__(self, "raw_summary", _required_text(self.raw_summary, "raw_summary"))
        object.__setattr__(self, "data_class", coerce_enum(self.data_class, DataClass, "data_class"))
        if self.data_class is DataClass.SECRETS:
            raise ValueError("SourceSignal cannot use secrets as data_class")
        object.__setattr__(self, "content_hash", require_content_hash(self.content_hash))
        object.__setattr__(self, "evidence_id", _required_text(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "confidence", _confidence(self.confidence))


@dataclass(frozen=True, slots=True)
class FinancialSnapshot:
    ticker: str
    as_of: datetime
    revenue_growth: Decimal
    gross_margin: Decimal
    operating_margin: Decimal
    free_cash_flow: Decimal
    capex: Decimal
    debt: Decimal
    cash: Decimal
    forward_pe: Decimal
    ev_sales: Decimal
    ev_ebitda: Decimal
    analyst_estimate_revision: Decimal
    source_evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", _required_text(self.ticker, "ticker").upper())
        require_aware_datetime(self.as_of, "as_of")
        for field_name in (
            "revenue_growth",
            "gross_margin",
            "operating_margin",
            "free_cash_flow",
            "capex",
            "debt",
            "cash",
            "forward_pe",
            "ev_sales",
            "ev_ebitda",
        ):
            object.__setattr__(self, field_name, Decimal(str(getattr(self, field_name))))
        object.__setattr__(
            self,
            "analyst_estimate_revision",
            require_decimal_range(self.analyst_estimate_revision, "analyst_estimate_revision", Decimal("-1"), Decimal("1")),
        )
        object.__setattr__(self, "source_evidence_ids", _required_text_tuple(self.source_evidence_ids, "source_evidence_ids"))


@dataclass(frozen=True, slots=True)
class ValuationContext:
    ticker: str
    as_of: datetime
    valuation_summary: str
    peer_group: tuple[str, ...]
    valuation_multiples: dict[str, Any]
    bear_case_assumptions: tuple[str, ...]
    base_case_assumptions: tuple[str, ...]
    bull_case_assumptions: tuple[str, ...]
    price_target_scenarios: dict[str, Any]
    key_sensitivities: tuple[str, ...]
    risk_flags: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    generated_by_model_run_id: str
    deterministic_inputs_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", _required_text(self.ticker, "ticker").upper())
        require_aware_datetime(self.as_of, "as_of")
        object.__setattr__(self, "valuation_summary", _required_text(self.valuation_summary, "valuation_summary"))
        object.__setattr__(self, "peer_group", _required_text_tuple(self.peer_group, "peer_group", uppercase=True))
        _require_non_empty_dict(self.valuation_multiples, "valuation_multiples")
        _reject_forbidden_payload_keys(self.valuation_multiples, "valuation_multiples")
        object.__setattr__(self, "bear_case_assumptions", _required_text_tuple(self.bear_case_assumptions, "bear_case_assumptions"))
        object.__setattr__(self, "base_case_assumptions", _required_text_tuple(self.base_case_assumptions, "base_case_assumptions"))
        object.__setattr__(self, "bull_case_assumptions", _required_text_tuple(self.bull_case_assumptions, "bull_case_assumptions"))
        _require_non_empty_dict(self.price_target_scenarios, "price_target_scenarios")
        _require_scenario_keys(self.price_target_scenarios, "price_target_scenarios")
        _reject_forbidden_payload_keys(self.price_target_scenarios, "price_target_scenarios")
        object.__setattr__(self, "key_sensitivities", _required_text_tuple(self.key_sensitivities, "key_sensitivities"))
        object.__setattr__(self, "risk_flags", _required_text_tuple(self.risk_flags, "risk_flags"))
        object.__setattr__(self, "evidence_ids", _required_text_tuple(self.evidence_ids, "evidence_ids"))
        object.__setattr__(self, "generated_by_model_run_id", _required_text(self.generated_by_model_run_id, "generated_by_model_run_id"))
        object.__setattr__(self, "deterministic_inputs_hash", require_content_hash(self.deterministic_inputs_hash, "deterministic_inputs_hash"))


@dataclass(frozen=True, slots=True)
class MacroRegimeSnapshot:
    as_of: datetime
    rates_regime: str
    liquidity_regime: str
    risk_appetite: str
    semiconductor_cycle: str
    ai_capex_cycle: str
    credit_conditions: str
    energy_price_context: str
    geopolitical_risk_level: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        require_aware_datetime(self.as_of, "as_of")
        for field_name in (
            "rates_regime",
            "liquidity_regime",
            "risk_appetite",
            "semiconductor_cycle",
            "ai_capex_cycle",
            "credit_conditions",
            "energy_price_context",
            "geopolitical_risk_level",
        ):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name))
        object.__setattr__(self, "evidence_ids", _required_text_tuple(self.evidence_ids, "evidence_ids"))


@dataclass(frozen=True, slots=True)
class RiskRegimeUpdate:
    regime_id: str
    risk_type: RiskRegimeType
    status: RiskRegimeStatus
    severity: str
    confidence: Decimal
    linked_event_ids: tuple[str, ...]
    affected_segments: tuple[str, ...]
    affected_tickers: tuple[str, ...]
    summary: str
    portfolio_monitoring_note: str
    relief_condition: str | None
    invalidation_condition: str | None
    as_of: datetime
    available_at: datetime
    source_evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "regime_id", _required_text(self.regime_id, "regime_id"))
        object.__setattr__(self, "risk_type", coerce_enum(self.risk_type, RiskRegimeType, "risk_type"))
        object.__setattr__(self, "status", coerce_enum(self.status, RiskRegimeStatus, "status"))
        object.__setattr__(self, "severity", _required_text(self.severity, "severity"))
        object.__setattr__(self, "confidence", _confidence(self.confidence))
        object.__setattr__(self, "linked_event_ids", _required_text_tuple(self.linked_event_ids, "linked_event_ids"))
        object.__setattr__(self, "affected_segments", _required_text_tuple(self.affected_segments, "affected_segments"))
        object.__setattr__(self, "affected_tickers", _required_text_tuple(self.affected_tickers, "affected_tickers", uppercase=True))
        object.__setattr__(self, "summary", _required_text(self.summary, "summary"))
        object.__setattr__(self, "portfolio_monitoring_note", _required_text(self.portfolio_monitoring_note, "portfolio_monitoring_note"))
        object.__setattr__(self, "relief_condition", _optional_text(self.relief_condition, "relief_condition"))
        object.__setattr__(self, "invalidation_condition", _optional_text(self.invalidation_condition, "invalidation_condition"))
        if self.status in {RiskRegimeStatus.ELEVATED, RiskRegimeStatus.STRESSED} and not (
            self.portfolio_monitoring_note or self.relief_condition or self.invalidation_condition
        ):
            raise ValueError("elevated or stressed risk regimes require monitoring, relief, or invalidation context")
        as_of = require_aware_datetime(self.as_of, "as_of")
        available_at = require_aware_datetime(self.available_at, "available_at")
        if available_at < as_of:
            raise ValueError("available_at must be greater than or equal to as_of")
        object.__setattr__(self, "source_evidence_ids", _required_text_tuple(self.source_evidence_ids, "source_evidence_ids"))


@dataclass(frozen=True, slots=True)
class AdvisoryReadinessCheck:
    check_id: str
    check_name: str
    passed: bool
    checked_at: datetime
    evidence_ids: tuple[str, ...]
    model_run_ids: tuple[str, ...]
    deterministic_checks: dict[str, Any]
    blocking_failures: tuple[str, ...]
    confidence: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "check_id", _required_text(self.check_id, "check_id"))
        object.__setattr__(self, "check_name", _required_text(self.check_name, "check_name"))
        if self.passed is not True:
            raise ValueError("AdvisoryReadinessCheck must pass before advisory publication")
        require_aware_datetime(self.checked_at, "checked_at")
        object.__setattr__(self, "evidence_ids", _required_text_tuple(self.evidence_ids, "evidence_ids"))
        object.__setattr__(self, "model_run_ids", _required_text_tuple(self.model_run_ids, "model_run_ids"))
        _require_non_empty_dict(self.deterministic_checks, "deterministic_checks")
        _reject_forbidden_payload_keys(self.deterministic_checks, "deterministic_checks")
        object.__setattr__(self, "blocking_failures", _optional_text_tuple(self.blocking_failures, "blocking_failures"))
        if self.blocking_failures:
            raise ValueError("AdvisoryReadinessCheck cannot contain blocking_failures")
        object.__setattr__(self, "confidence", _confidence(self.confidence))


@dataclass(frozen=True, slots=True)
class TradingAdvisory:
    advisory_id: str
    ticker_or_portfolio: str
    advisory_label: AdvisoryLabel
    analyst_action: AnalystAction
    thesis_summary: str
    catalyst_summary: str
    valuation_context_id: str
    risk_regime_ids: tuple[str, ...]
    market_event_ids: tuple[str, ...]
    segment_impact_ids: tuple[str, ...]
    entry_zone: str | None
    add_zone: str | None
    invalidation_level: str
    target_scenarios: dict[str, Any]
    time_horizon: str
    risk_flags: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    model_run_ids: tuple[str, ...]
    deterministic_checks: dict[str, Any]
    readiness_checks: tuple[AdvisoryReadinessCheck, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "advisory_id", _required_text(self.advisory_id, "advisory_id"))
        object.__setattr__(self, "ticker_or_portfolio", _required_text(self.ticker_or_portfolio, "ticker_or_portfolio").upper())
        object.__setattr__(self, "advisory_label", coerce_enum(self.advisory_label, AdvisoryLabel, "advisory_label"))
        if self.advisory_label is not AdvisoryLabel.ADVISORY_ONLY:
            raise ValueError("TradingAdvisory must be advisory-only")
        object.__setattr__(self, "analyst_action", coerce_enum(self.analyst_action, AnalystAction, "analyst_action"))
        object.__setattr__(self, "thesis_summary", _required_text(self.thesis_summary, "thesis_summary"))
        object.__setattr__(self, "catalyst_summary", _required_text(self.catalyst_summary, "catalyst_summary"))
        object.__setattr__(self, "valuation_context_id", _required_text(self.valuation_context_id, "valuation_context_id"))
        object.__setattr__(self, "risk_regime_ids", _required_text_tuple(self.risk_regime_ids, "risk_regime_ids"))
        object.__setattr__(self, "market_event_ids", _required_text_tuple(self.market_event_ids, "market_event_ids"))
        object.__setattr__(self, "segment_impact_ids", _required_text_tuple(self.segment_impact_ids, "segment_impact_ids"))
        object.__setattr__(self, "entry_zone", _optional_text(self.entry_zone, "entry_zone"))
        object.__setattr__(self, "add_zone", _optional_text(self.add_zone, "add_zone"))
        object.__setattr__(self, "invalidation_level", _required_text(self.invalidation_level, "invalidation_level"))
        _require_non_empty_dict(self.target_scenarios, "target_scenarios")
        _require_scenario_keys(self.target_scenarios, "target_scenarios")
        _reject_forbidden_payload_keys(self.target_scenarios, "target_scenarios")
        object.__setattr__(self, "time_horizon", _required_text(self.time_horizon, "time_horizon"))
        object.__setattr__(self, "risk_flags", _required_text_tuple(self.risk_flags, "risk_flags"))
        object.__setattr__(self, "evidence_ids", _required_text_tuple(self.evidence_ids, "evidence_ids"))
        object.__setattr__(self, "model_run_ids", _required_text_tuple(self.model_run_ids, "model_run_ids"))
        _require_non_empty_dict(self.deterministic_checks, "deterministic_checks")
        _reject_forbidden_payload_keys(self.deterministic_checks, "deterministic_checks")
        object.__setattr__(self, "readiness_checks", _required_readiness_checks(self.readiness_checks))
        require_aware_datetime(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class TradePlan:
    trade_plan_id: str
    ticker: str
    company: str
    status: TradePlanStatus
    advisory_action: AnalystAction
    linked_event_ids: tuple[str, ...]
    linked_signal_bundle_id: str
    linked_recommendation_artifact_id: str
    entry_exit_levels_id: str | None
    price_target_scenario_id: str | None
    target_weights_id: str | None
    deterministic_check_ids: tuple[str, ...]
    readiness: TradePlanReadiness
    blocking_reasons: tuple[str, ...]
    manual_journal_only: bool
    last_reviewed_at: datetime | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "trade_plan_id", _required_text(self.trade_plan_id, "trade_plan_id"))
        object.__setattr__(self, "ticker", _required_text(self.ticker, "ticker").upper())
        object.__setattr__(self, "company", _required_text(self.company, "company"))
        object.__setattr__(self, "status", coerce_enum(self.status, TradePlanStatus, "status"))
        object.__setattr__(self, "advisory_action", coerce_enum(self.advisory_action, AnalystAction, "advisory_action"))
        object.__setattr__(self, "linked_event_ids", _required_text_tuple(self.linked_event_ids, "linked_event_ids"))
        object.__setattr__(
            self,
            "linked_signal_bundle_id",
            _required_text(self.linked_signal_bundle_id, "linked_signal_bundle_id"),
        )
        object.__setattr__(
            self,
            "linked_recommendation_artifact_id",
            _required_text(self.linked_recommendation_artifact_id, "linked_recommendation_artifact_id"),
        )
        object.__setattr__(self, "entry_exit_levels_id", _optional_text(self.entry_exit_levels_id, "entry_exit_levels_id"))
        object.__setattr__(
            self,
            "price_target_scenario_id",
            _optional_text(self.price_target_scenario_id, "price_target_scenario_id"),
        )
        object.__setattr__(self, "target_weights_id", _optional_text(self.target_weights_id, "target_weights_id"))
        object.__setattr__(self, "deterministic_check_ids", _required_text_tuple(self.deterministic_check_ids, "deterministic_check_ids"))
        _reject_forbidden_text_values(self.deterministic_check_ids, "deterministic_check_ids")
        object.__setattr__(self, "readiness", coerce_enum(self.readiness, TradePlanReadiness, "readiness"))
        object.__setattr__(self, "blocking_reasons", _optional_text_tuple(self.blocking_reasons, "blocking_reasons"))
        if self.readiness in {TradePlanReadiness.BLOCKED, TradePlanReadiness.STALE_DATA} and not self.blocking_reasons:
            raise ValueError("blocked or stale trade plans require blocking_reasons")
        if self.manual_journal_only is not True:
            raise ValueError("TradePlan must be manual_journal_only")
        if self.last_reviewed_at is not None:
            require_aware_datetime(self.last_reviewed_at, "last_reviewed_at")


@dataclass(frozen=True, slots=True)
class PortfolioPosition:
    ticker: str
    company: str
    segment_tags: tuple[str, ...]
    market_value: Decimal
    portfolio_weight: Decimal
    cost_basis: Decimal
    unrealized_pnl: Decimal
    open_trade_plan_id: str | None
    risk_flags: tuple[str, ...]
    last_price_timestamp: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", _required_text(self.ticker, "ticker").upper())
        object.__setattr__(self, "company", _required_text(self.company, "company"))
        object.__setattr__(self, "segment_tags", _required_text_tuple(self.segment_tags, "segment_tags"))
        object.__setattr__(self, "market_value", require_non_negative(self.market_value, "market_value"))
        object.__setattr__(self, "portfolio_weight", require_decimal_range(self.portfolio_weight, "portfolio_weight", Decimal("0"), Decimal("1")))
        object.__setattr__(self, "cost_basis", require_non_negative(self.cost_basis, "cost_basis"))
        object.__setattr__(self, "unrealized_pnl", Decimal(str(self.unrealized_pnl)))
        object.__setattr__(self, "open_trade_plan_id", _optional_text(self.open_trade_plan_id, "open_trade_plan_id"))
        object.__setattr__(self, "risk_flags", _optional_text_tuple(self.risk_flags, "risk_flags"))
        require_aware_datetime(self.last_price_timestamp, "last_price_timestamp")


@dataclass(frozen=True, slots=True)
class PortfolioExposureSnapshot:
    snapshot_id: str
    as_of: datetime
    currency: str
    source: str
    advisory_label: AdvisoryLabel
    total_market_value: Decimal
    cash_placeholder: Decimal
    gross_equity_exposure: Decimal
    position_count: int
    positions: tuple[PortfolioPosition, ...]
    correlation_exposure_ids: tuple[str, ...]
    pnl_summary_id: str | None
    target_weights_id: str | None
    concentration_flags: tuple[str, ...]
    stale_price_flags: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "snapshot_id", _required_text(self.snapshot_id, "snapshot_id"))
        require_aware_datetime(self.as_of, "as_of")
        object.__setattr__(self, "currency", _required_text(self.currency, "currency").upper())
        object.__setattr__(self, "source", _required_text(self.source, "source"))
        object.__setattr__(self, "advisory_label", coerce_enum(self.advisory_label, AdvisoryLabel, "advisory_label"))
        if self.advisory_label is not AdvisoryLabel.ADVISORY_ONLY:
            raise ValueError("PortfolioExposureSnapshot must be advisory-only")
        object.__setattr__(self, "total_market_value", require_non_negative(self.total_market_value, "total_market_value"))
        object.__setattr__(self, "cash_placeholder", require_non_negative(self.cash_placeholder, "cash_placeholder"))
        object.__setattr__(
            self,
            "gross_equity_exposure",
            require_decimal_range(self.gross_equity_exposure, "gross_equity_exposure", Decimal("0"), Decimal("1")),
        )
        if not isinstance(self.position_count, int) or self.position_count < 0:
            raise ValueError("position_count must be a non-negative integer")
        object.__setattr__(self, "positions", _required_positions(self.positions))
        if self.position_count != len(self.positions):
            raise ValueError("position_count must equal the number of positions")
        object.__setattr__(self, "correlation_exposure_ids", _optional_text_tuple(self.correlation_exposure_ids, "correlation_exposure_ids"))
        object.__setattr__(self, "pnl_summary_id", _optional_text(self.pnl_summary_id, "pnl_summary_id"))
        object.__setattr__(self, "target_weights_id", _optional_text(self.target_weights_id, "target_weights_id"))
        object.__setattr__(self, "concentration_flags", _optional_text_tuple(self.concentration_flags, "concentration_flags"))
        object.__setattr__(self, "stale_price_flags", _optional_text_tuple(self.stale_price_flags, "stale_price_flags"))


@dataclass(frozen=True, slots=True)
class AnalystBrief:
    brief_id: str
    ticker_or_portfolio: str
    advisory_label: AdvisoryLabel
    headline: str
    summary: str
    key_points: tuple[str, ...]
    risk_flags: tuple[str, ...]
    linked_advisory_id: str | None
    linked_valuation_context_id: str | None
    evidence_ids: tuple[str, ...]
    model_run_ids: tuple[str, ...]
    metadata: dict[str, Any]
    created_at: datetime
    confidence: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "brief_id", _required_text(self.brief_id, "brief_id"))
        object.__setattr__(self, "ticker_or_portfolio", _required_text(self.ticker_or_portfolio, "ticker_or_portfolio").upper())
        object.__setattr__(self, "advisory_label", coerce_enum(self.advisory_label, AdvisoryLabel, "advisory_label"))
        if self.advisory_label is not AdvisoryLabel.ADVISORY_ONLY:
            raise ValueError("AnalystBrief must be advisory-only")
        object.__setattr__(self, "headline", _required_text(self.headline, "headline"))
        object.__setattr__(self, "summary", _required_text(self.summary, "summary"))
        object.__setattr__(self, "key_points", _required_text_tuple(self.key_points, "key_points"))
        object.__setattr__(self, "risk_flags", _required_text_tuple(self.risk_flags, "risk_flags"))
        object.__setattr__(self, "linked_advisory_id", _optional_text(self.linked_advisory_id, "linked_advisory_id"))
        object.__setattr__(
            self,
            "linked_valuation_context_id",
            _optional_text(self.linked_valuation_context_id, "linked_valuation_context_id"),
        )
        object.__setattr__(self, "evidence_ids", _required_text_tuple(self.evidence_ids, "evidence_ids"))
        object.__setattr__(self, "model_run_ids", _required_text_tuple(self.model_run_ids, "model_run_ids"))
        _require_non_empty_dict(self.metadata, "metadata")
        _reject_forbidden_payload_keys(self.metadata, "metadata")
        require_aware_datetime(self.created_at, "created_at")
        object.__setattr__(self, "confidence", _confidence(self.confidence))


@dataclass(frozen=True, slots=True)
class AdvisoryUpdate:
    update_id: str
    previous_advisory_id: str
    new_advisory_id: str
    what_changed: str
    thesis_change_direction: AdvisoryChangeDirection
    risk_change_direction: AdvisoryChangeDirection
    valuation_change_direction: AdvisoryChangeDirection
    confidence_change: AdvisoryChangeDirection
    evidence_ids: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "update_id", _required_text(self.update_id, "update_id"))
        object.__setattr__(self, "previous_advisory_id", _required_text(self.previous_advisory_id, "previous_advisory_id"))
        object.__setattr__(self, "new_advisory_id", _required_text(self.new_advisory_id, "new_advisory_id"))
        object.__setattr__(self, "what_changed", _required_text(self.what_changed, "what_changed"))
        object.__setattr__(
            self,
            "thesis_change_direction",
            coerce_enum(self.thesis_change_direction, AdvisoryChangeDirection, "thesis_change_direction"),
        )
        object.__setattr__(
            self,
            "risk_change_direction",
            coerce_enum(self.risk_change_direction, AdvisoryChangeDirection, "risk_change_direction"),
        )
        object.__setattr__(
            self,
            "valuation_change_direction",
            coerce_enum(self.valuation_change_direction, AdvisoryChangeDirection, "valuation_change_direction"),
        )
        object.__setattr__(
            self,
            "confidence_change",
            coerce_enum(self.confidence_change, AdvisoryChangeDirection, "confidence_change"),
        )
        object.__setattr__(self, "evidence_ids", _required_text_tuple(self.evidence_ids, "evidence_ids"))
        require_aware_datetime(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class OutcomeJournalEntry:
    outcome_entry_id: str
    trade_entry_id: str
    ticker: str
    entry_type: str
    local_only: bool
    linked_trade_plan_id: str
    advisory_label_at_time: AdvisoryLabel
    recorded_price: Decimal | None
    recorded_quantity: Decimal | None
    recorded_at: datetime
    evidence_available_ids: tuple[str, ...]
    market_event_ids_available_at_decision: tuple[str, ...]
    pnl_id: str | None
    realized_pnl: Decimal | None
    unrealized_pnl: Decimal | None
    plan_adherence_status: str | None
    outcome_label: OutcomeLabel
    analyst_note: str | None
    llm_review_note_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcome_entry_id", _required_text(self.outcome_entry_id, "outcome_entry_id"))
        object.__setattr__(self, "trade_entry_id", _required_text(self.trade_entry_id, "trade_entry_id"))
        object.__setattr__(self, "ticker", _required_text(self.ticker, "ticker").upper())
        object.__setattr__(self, "entry_type", _required_text(self.entry_type, "entry_type"))
        if self.local_only is not True:
            raise ValueError("OutcomeJournalEntry must be local_only")
        object.__setattr__(self, "linked_trade_plan_id", _required_text(self.linked_trade_plan_id, "linked_trade_plan_id"))
        object.__setattr__(
            self,
            "advisory_label_at_time",
            coerce_enum(self.advisory_label_at_time, AdvisoryLabel, "advisory_label_at_time"),
        )
        if self.advisory_label_at_time is not AdvisoryLabel.ADVISORY_ONLY:
            raise ValueError("OutcomeJournalEntry advisory_label_at_time must be advisory-only")
        if self.recorded_price is not None:
            object.__setattr__(self, "recorded_price", require_positive(self.recorded_price, "recorded_price"))
        if self.recorded_quantity is not None:
            object.__setattr__(self, "recorded_quantity", require_positive(self.recorded_quantity, "recorded_quantity"))
        require_aware_datetime(self.recorded_at, "recorded_at")
        object.__setattr__(self, "evidence_available_ids", _required_text_tuple(self.evidence_available_ids, "evidence_available_ids"))
        object.__setattr__(
            self,
            "market_event_ids_available_at_decision",
            _required_text_tuple(self.market_event_ids_available_at_decision, "market_event_ids_available_at_decision"),
        )
        object.__setattr__(self, "pnl_id", _optional_text(self.pnl_id, "pnl_id"))
        if self.realized_pnl is not None:
            object.__setattr__(self, "realized_pnl", Decimal(str(self.realized_pnl)))
        if self.unrealized_pnl is not None:
            object.__setattr__(self, "unrealized_pnl", Decimal(str(self.unrealized_pnl)))
        object.__setattr__(self, "plan_adherence_status", _optional_text(self.plan_adherence_status, "plan_adherence_status"))
        object.__setattr__(self, "outcome_label", coerce_enum(self.outcome_label, OutcomeLabel, "outcome_label"))
        object.__setattr__(self, "analyst_note", _optional_text(self.analyst_note, "analyst_note"))
        object.__setattr__(self, "llm_review_note_id", _optional_text(self.llm_review_note_id, "llm_review_note_id"))


@dataclass(frozen=True, slots=True)
class LLMAnalystNote:
    note_id: str
    model_run_id: str
    scope: str
    allowed_role: str
    reviewed_object_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    note: str
    deterministic_fields_not_modified: tuple[str, ...]
    created_at: datetime
    review_status: LLMNoteReviewStatus

    def __post_init__(self) -> None:
        object.__setattr__(self, "note_id", _required_text(self.note_id, "note_id"))
        object.__setattr__(self, "model_run_id", _required_text(self.model_run_id, "model_run_id"))
        object.__setattr__(self, "scope", _required_text(self.scope, "scope"))
        allowed_role = _required_text(self.allowed_role, "allowed_role")
        if allowed_role not in ALLOWED_LLM_ANALYST_ROLES:
            raise ValueError("allowed_role must be a governed LLM analyst role")
        object.__setattr__(self, "allowed_role", allowed_role)
        object.__setattr__(self, "reviewed_object_ids", _optional_text_tuple(self.reviewed_object_ids, "reviewed_object_ids"))
        object.__setattr__(self, "evidence_ids", _optional_text_tuple(self.evidence_ids, "evidence_ids"))
        if not self.reviewed_object_ids and not self.evidence_ids:
            raise ValueError("LLMAnalystNote requires reviewed_object_ids or evidence_ids")
        note = _required_text(self.note, "note")
        _reject_forbidden_action_language(note, "note")
        object.__setattr__(self, "note", note)
        object.__setattr__(
            self,
            "deterministic_fields_not_modified",
            _required_text_tuple(self.deterministic_fields_not_modified, "deterministic_fields_not_modified"),
        )
        require_aware_datetime(self.created_at, "created_at")
        object.__setattr__(self, "review_status", coerce_enum(self.review_status, LLMNoteReviewStatus, "review_status"))


def _required_text(value: object, field_name: str) -> str:
    return require_text(str(value) if value is not None else None, field_name).strip()


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)


def _required_text_tuple(values: object, field_name: str, *, uppercase: bool = False) -> tuple[str, ...]:
    normalized = require_non_empty_tuple(normalize_tuple(values, field_name), field_name)
    text_values = tuple(_required_text(value, field_name) for value in normalized)
    if uppercase:
        return tuple(value.upper() for value in text_values)
    return text_values


def _optional_text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    return tuple(_required_text(value, field_name) for value in normalize_tuple(values, field_name))


def _required_readiness_checks(values: object) -> tuple[AdvisoryReadinessCheck, ...]:
    checks = require_non_empty_tuple(normalize_tuple(values, "readiness_checks"), "readiness_checks")
    if not all(isinstance(check, AdvisoryReadinessCheck) for check in checks):
        raise ValueError("readiness_checks must contain AdvisoryReadinessCheck instances")
    return checks


def _required_positions(values: object) -> tuple[PortfolioPosition, ...]:
    positions = require_non_empty_tuple(normalize_tuple(values, "positions"), "positions")
    if not all(isinstance(position, PortfolioPosition) for position in positions):
        raise ValueError("positions must contain PortfolioPosition instances")
    return positions


def _confidence(value: Decimal) -> Decimal:
    return require_decimal_range(value, "confidence", Decimal("0"), Decimal("1"))


def _require_non_empty_dict(values: dict[str, Any], field_name: str) -> None:
    if not isinstance(values, dict) or not values:
        raise ValueError(f"{field_name} must not be empty")


def _require_scenario_keys(values: dict[str, Any], field_name: str) -> None:
    missing = REQUIRED_SCENARIOS.difference(str(key).strip().lower() for key in values)
    if missing:
        raise ValueError(f"{field_name} must include bear, base, and bull scenarios")


def _reject_forbidden_payload_keys(values: Any, field_name: str) -> None:
    if isinstance(values, dict):
        for key, value in values.items():
            normalized_key = str(key).strip().lower()
            if any(term in normalized_key for term in FORBIDDEN_OBJECT_FIELD_TERMS):
                raise ValueError(
                    f"{field_name} cannot include broker, route, exchange, order, execution, or auto_trade fields"
                )
            _reject_forbidden_payload_keys(value, field_name)
    elif isinstance(values, (list, tuple)):
        for value in values:
            _reject_forbidden_payload_keys(value, field_name)


def _reject_forbidden_text_values(values: tuple[str, ...], field_name: str) -> None:
    for value in values:
        lowered = value.lower()
        if any(term in lowered for term in FORBIDDEN_OBJECT_FIELD_TERMS):
            raise ValueError(
                f"{field_name} cannot include broker, route, exchange, order, execution, or auto_trade terms"
            )


def _reject_forbidden_action_language(value: str, field_name: str) -> None:
    lowered = value.lower()
    if any(phrase in lowered for phrase in FORBIDDEN_ACTION_PHRASES):
        raise ValueError(f"{field_name} cannot include executable market-action language")
