from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from ai_infra_fund_core.contracts.common import normalize_tuple, require_non_empty_tuple, require_text


class DraftReviewStatus(str, Enum):
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"


FORBIDDEN_LLM_OWNED_PAYLOAD_KEYS = frozenset(
    {
        "accounting",
        "deterministic_checks",
        "entry_exit_levels",
        "portfolio_weight",
        "position_size",
        "price_target_scenarios",
        "pnl",
        "target_weight",
        "target_weights",
    }
)


@dataclass(frozen=True, slots=True)
class MaterialClaimDraft:
    claim: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim", require_text(self.claim, "claim").strip())
        object.__setattr__(self, "evidence_ids", _required_text_tuple(self.evidence_ids, "evidence_ids"))


@dataclass(frozen=True, slots=True)
class BaseAnalystDraft:
    draft_id: str
    draft_type: str
    evidence_ids: tuple[str, ...]
    material_claims: tuple[MaterialClaimDraft, ...]
    payload: dict[str, Any]
    model_run_id: str
    review_status: DraftReviewStatus
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "draft_id", require_text(self.draft_id, "draft_id").strip())
        object.__setattr__(self, "draft_type", require_text(self.draft_type, "draft_type").strip())
        object.__setattr__(self, "evidence_ids", _required_text_tuple(self.evidence_ids, "evidence_ids"))
        claims = require_non_empty_tuple(normalize_tuple(self.material_claims, "material_claims"), "material_claims")
        if not all(isinstance(claim, MaterialClaimDraft) for claim in claims):
            raise ValueError("material_claims must contain MaterialClaimDraft instances")
        object.__setattr__(self, "material_claims", claims)
        if not isinstance(self.payload, dict) or not self.payload:
            raise ValueError("payload must be a non-empty mapping")
        _reject_forbidden_payload_keys(self.payload, "payload")
        object.__setattr__(self, "model_run_id", require_text(self.model_run_id, "model_run_id").strip())
        object.__setattr__(self, "review_status", DraftReviewStatus(self.review_status))
        object.__setattr__(self, "rejection_reasons", _optional_text_tuple(self.rejection_reasons, "rejection_reasons"))
        if self.review_status is DraftReviewStatus.REJECTED and not self.rejection_reasons:
            raise ValueError("rejected drafts require rejection_reasons")
        if self.review_status is DraftReviewStatus.REVIEW_REQUIRED and self.rejection_reasons:
            raise ValueError("review_required drafts cannot include rejection_reasons")

    @property
    def can_publish_directly(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class SegmentImpactDraft(BaseAnalystDraft):
    segment_name: str = ""
    linked_event_ids: tuple[str, ...] = ()
    first_order_tickers: tuple[str, ...] = ()
    second_order_tickers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        BaseAnalystDraft.__post_init__(self)
        object.__setattr__(self, "segment_name", require_text(self.segment_name, "segment_name").strip())
        object.__setattr__(self, "linked_event_ids", _required_text_tuple(self.linked_event_ids, "linked_event_ids"))
        object.__setattr__(self, "first_order_tickers", _required_text_tuple(self.first_order_tickers, "first_order_tickers", uppercase=True))
        object.__setattr__(self, "second_order_tickers", _required_text_tuple(self.second_order_tickers, "second_order_tickers", uppercase=True))


@dataclass(frozen=True, slots=True)
class EquityImpactAssessmentDraft(BaseAnalystDraft):
    ticker: str = ""
    assessment: str = ""
    bull_case: str = ""
    bear_case: str = ""
    risk_flags: tuple[str, ...] = ()
    invalidation_condition: str = ""

    def __post_init__(self) -> None:
        BaseAnalystDraft.__post_init__(self)
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        object.__setattr__(self, "assessment", require_text(self.assessment, "assessment").strip())
        object.__setattr__(self, "bull_case", require_text(self.bull_case, "bull_case").strip())
        object.__setattr__(self, "bear_case", require_text(self.bear_case, "bear_case").strip())
        object.__setattr__(self, "risk_flags", _required_text_tuple(self.risk_flags, "risk_flags"))
        object.__setattr__(self, "invalidation_condition", require_text(self.invalidation_condition, "invalidation_condition").strip())


@dataclass(frozen=True, slots=True)
class ValuationContextDraft(BaseAnalystDraft):
    ticker: str = ""
    valuation_summary: str = ""

    def __post_init__(self) -> None:
        BaseAnalystDraft.__post_init__(self)
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        object.__setattr__(self, "valuation_summary", require_text(self.valuation_summary, "valuation_summary").strip())


@dataclass(frozen=True, slots=True)
class RiskRegimeUpdateDraft(BaseAnalystDraft):
    risk_type: str = ""
    affected_tickers: tuple[str, ...] = ()
    summary: str = ""

    def __post_init__(self) -> None:
        BaseAnalystDraft.__post_init__(self)
        object.__setattr__(self, "risk_type", require_text(self.risk_type, "risk_type").strip())
        object.__setattr__(self, "affected_tickers", _required_text_tuple(self.affected_tickers, "affected_tickers", uppercase=True))
        object.__setattr__(self, "summary", require_text(self.summary, "summary").strip())


@dataclass(frozen=True, slots=True)
class TradingAdvisoryDraft(BaseAnalystDraft):
    ticker: str = ""
    analyst_action: str = ""
    rationale: str = ""
    market_event_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        BaseAnalystDraft.__post_init__(self)
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        object.__setattr__(self, "analyst_action", require_text(self.analyst_action, "analyst_action").strip())
        object.__setattr__(self, "rationale", require_text(self.rationale, "rationale").strip())
        object.__setattr__(self, "market_event_ids", _required_text_tuple(self.market_event_ids, "market_event_ids"))


@dataclass(frozen=True, slots=True)
class AnalystBriefDraft(BaseAnalystDraft):
    headline: str = ""
    summary: str = ""

    def __post_init__(self) -> None:
        BaseAnalystDraft.__post_init__(self)
        object.__setattr__(self, "headline", require_text(self.headline, "headline").strip())
        object.__setattr__(self, "summary", require_text(self.summary, "summary").strip())


@dataclass(frozen=True, slots=True)
class RejectedAnalystDraft:
    draft_id: str
    draft_type: str
    evidence_ids: tuple[str, ...]
    model_run_id: str
    rejection_reasons: tuple[str, ...]
    raw_payload: dict[str, Any]
    review_status: DraftReviewStatus = DraftReviewStatus.REJECTED

    def __post_init__(self) -> None:
        object.__setattr__(self, "draft_id", require_text(self.draft_id, "draft_id").strip())
        object.__setattr__(self, "draft_type", require_text(self.draft_type, "draft_type").strip())
        object.__setattr__(self, "evidence_ids", _required_text_tuple(self.evidence_ids, "evidence_ids"))
        object.__setattr__(self, "model_run_id", require_text(self.model_run_id, "model_run_id").strip())
        object.__setattr__(self, "rejection_reasons", _required_text_tuple(self.rejection_reasons, "rejection_reasons"))
        if not isinstance(self.raw_payload, dict) or not self.raw_payload:
            raise ValueError("raw_payload must be a non-empty mapping")
        object.__setattr__(self, "review_status", DraftReviewStatus.REJECTED)

    @property
    def can_publish_directly(self) -> bool:
        return False


def make_material_claims(
    raw_claims: object,
    *,
    allowed_evidence_ids: Sequence[str],
) -> tuple[MaterialClaimDraft, ...]:
    claims: list[MaterialClaimDraft] = []
    for raw_claim in normalize_tuple(raw_claims, "material_claims"):
        if not isinstance(raw_claim, Mapping):
            raise ValueError("material_claims entries must be mappings")
        claim = MaterialClaimDraft(
            claim=str(raw_claim.get("claim") or ""),
            evidence_ids=_required_text_tuple(raw_claim.get("evidence_ids"), "material_claims.evidence_ids"),
        )
        unknown = [evidence_id for evidence_id in claim.evidence_ids if evidence_id not in allowed_evidence_ids]
        if unknown:
            raise ValueError(f"material_claim references unknown evidence IDs: {', '.join(unknown)}")
        claims.append(claim)
    return tuple(require_non_empty_tuple(tuple(claims), "material_claims"))


def extract_evidence_ids(raw_item: Mapping[str, Any]) -> tuple[str, ...]:
    return _required_text_tuple(raw_item.get("evidence_ids"), "evidence_ids")


def reject_forbidden_payload(raw_item: Mapping[str, Any]) -> None:
    _reject_forbidden_payload_keys(raw_item, "draft")


def _reject_forbidden_payload_keys(value: Any, field_name: str) -> None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            key_text = str(key).strip().lower()
            if key_text in FORBIDDEN_LLM_OWNED_PAYLOAD_KEYS:
                raise ValueError(f"{field_name} cannot include LLM-owned deterministic field: {key_text}")
            _reject_forbidden_payload_keys(nested_value, field_name)
    elif isinstance(value, (list, tuple)):
        for nested_value in value:
            _reject_forbidden_payload_keys(nested_value, field_name)


def _required_text_tuple(values: object, field_name: str, *, uppercase: bool = False) -> tuple[str, ...]:
    normalized = require_non_empty_tuple(normalize_tuple(values, field_name), field_name)
    text_values = tuple(require_text(str(value), field_name).strip() for value in normalized)
    if uppercase:
        return tuple(value.upper() for value in text_values)
    return text_values


def _optional_text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    return tuple(require_text(str(value), field_name).strip() for value in normalize_tuple(values, field_name))
