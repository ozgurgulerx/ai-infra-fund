from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_infra_fund_core.contracts.common import normalize_tuple, require_text


@dataclass(frozen=True, slots=True)
class RecommendationPolicyContext:
    stale_evidence_ids: tuple[str, ...] = ()
    quarantined_evidence_ids: tuple[str, ...] = ()
    incident_freeze_active: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "stale_evidence_ids", _normalize_ids(self.stale_evidence_ids, "stale_evidence_ids"))
        object.__setattr__(
            self,
            "quarantined_evidence_ids",
            _normalize_ids(self.quarantined_evidence_ids, "quarantined_evidence_ids"),
        )


@dataclass(frozen=True, slots=True)
class PublicationDecision:
    should_publish: bool
    suppression_reasons: tuple[str, ...]


def evaluate_publication_policy(
    deterministic_checks: dict[str, Any],
    policy_context: RecommendationPolicyContext | None = None,
) -> PublicationDecision:
    context = policy_context or RecommendationPolicyContext()
    reasons: list[str] = []

    if context.stale_evidence_ids:
        reasons.append("stale_evidence")
    if context.quarantined_evidence_ids:
        reasons.append("quarantined_evidence")
    if context.incident_freeze_active:
        reasons.append("incident_freeze_active")
    if not deterministic_checks.get("evidence_covers_signal", False):
        reasons.append("missing_evidence")
    if (
        not deterministic_checks.get("target_weights_generated_by_deterministic", False)
        or not deterministic_checks.get("target_weights_validated", False)
        or not deterministic_checks.get("target_weights_unit_bounds_valid", False)
    ):
        reasons.append("invalid_target_weights")
    if (
        not deterministic_checks.get("source_signal_bundle_linked", False)
        or not deterministic_checks.get("target_weights_sum_valid", False)
    ):
        reasons.append("deterministic_validation_failed")

    unique_reasons = tuple(dict.fromkeys(reasons))
    return PublicationDecision(should_publish=not unique_reasons, suppression_reasons=unique_reasons)


def _normalize_ids(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(require_text(value, field_name) for value in normalize_tuple(values, field_name)))
