from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .common import (
    AdvisoryLabel,
    RecommendationAction,
    coerce_enum,
    normalize_tuple,
    require_aware_datetime,
    require_non_empty_tuple,
    require_text,
)


@dataclass(frozen=True, slots=True)
class RecommendationArtifact:
    recommendation_id: str
    ticker_or_portfolio: str
    advisory_label: AdvisoryLabel
    action: RecommendationAction
    horizon: str
    score_breakdown: dict[str, Any]
    target_weights_id: str
    evidence_ids: tuple[str, ...]
    model_run_ids: tuple[str, ...]
    signal_bundle_id: str
    risks: tuple[str, ...]
    contradictions: tuple[str, ...]
    final_payload: dict[str, Any]
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "recommendation_id", require_text(self.recommendation_id, "recommendation_id"))
        object.__setattr__(self, "ticker_or_portfolio", require_text(self.ticker_or_portfolio, "ticker_or_portfolio"))
        object.__setattr__(self, "advisory_label", coerce_enum(self.advisory_label, AdvisoryLabel, "advisory_label"))
        if self.advisory_label is not AdvisoryLabel.ADVISORY_ONLY:
            raise ValueError("RecommendationArtifact must be advisory-only")
        object.__setattr__(self, "action", coerce_enum(self.action, RecommendationAction, "action"))
        object.__setattr__(self, "horizon", require_text(self.horizon, "horizon"))
        if not self.score_breakdown:
            raise ValueError("score_breakdown must not be empty")
        object.__setattr__(self, "target_weights_id", require_text(self.target_weights_id, "target_weights_id"))
        object.__setattr__(
            self,
            "evidence_ids",
            require_non_empty_tuple(normalize_tuple(self.evidence_ids, "evidence_ids"), "evidence_ids"),
        )
        object.__setattr__(
            self,
            "model_run_ids",
            require_non_empty_tuple(normalize_tuple(self.model_run_ids, "model_run_ids"), "model_run_ids"),
        )
        object.__setattr__(self, "signal_bundle_id", require_text(self.signal_bundle_id, "signal_bundle_id"))
        object.__setattr__(self, "risks", normalize_tuple(self.risks, "risks"))
        object.__setattr__(self, "contradictions", normalize_tuple(self.contradictions, "contradictions"))
        if not self.final_payload:
            raise ValueError("final_payload must not be empty")
        require_aware_datetime(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class RecommendationAudit:
    audit_id: str
    recommendation_id: str
    target_weights_id: str
    signal_bundle_id: str
    evidence_ids: tuple[str, ...]
    model_run_ids: tuple[str, ...]
    deterministic_checks: dict[str, Any]
    reviewer_findings: dict[str, Any] | None
    schema_valid: bool
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "audit_id", require_text(self.audit_id, "audit_id"))
        object.__setattr__(self, "recommendation_id", require_text(self.recommendation_id, "recommendation_id"))
        object.__setattr__(self, "target_weights_id", require_text(self.target_weights_id, "target_weights_id"))
        object.__setattr__(self, "signal_bundle_id", require_text(self.signal_bundle_id, "signal_bundle_id"))
        object.__setattr__(
            self,
            "evidence_ids",
            require_non_empty_tuple(normalize_tuple(self.evidence_ids, "evidence_ids"), "evidence_ids"),
        )
        object.__setattr__(
            self,
            "model_run_ids",
            require_non_empty_tuple(normalize_tuple(self.model_run_ids, "model_run_ids"), "model_run_ids"),
        )
        if not self.deterministic_checks:
            raise ValueError("deterministic_checks must not be empty")
        require_aware_datetime(self.created_at, "created_at")
