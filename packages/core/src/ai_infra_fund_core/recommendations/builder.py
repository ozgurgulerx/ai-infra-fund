from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from ai_infra_fund_core.audit.experiment_events import EventSink, build_event
from ai_infra_fund_core.contracts.common import (
    AdvisoryLabel,
    RecommendationAction,
    normalize_tuple,
    require_aware_datetime,
    require_non_empty_tuple,
    require_text,
    stable_hash_payload,
)
from ai_infra_fund_core.contracts.evidence import EvidenceClaim
from ai_infra_fund_core.contracts.recommendations import (
    RecommendationArtifact,
    RecommendationAudit,
)
from ai_infra_fund_core.contracts.signals import (
    FORBIDDEN_WEIGHT_GENERATORS,
    SignalBundle,
    TargetWeights,
)

from .policies import RecommendationPolicyContext, evaluate_publication_policy


ONE = Decimal("1")
ZERO = Decimal("0")
SCORE_QUANT = Decimal("0.0001")
WEIGHT_TOLERANCE = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class RecommendationBuildResult:
    artifact: RecommendationArtifact
    audit: RecommendationAudit
    should_publish: bool
    suppression_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _SignalSnapshot:
    signal_bundle_id: str
    ticker: str
    strategic_thesis_score: Decimal
    tactical_technical_score: Decimal
    forward_indicator_score: Decimal
    portfolio_risk_score: Decimal


@dataclass(frozen=True, slots=True)
class _TargetWeightsSnapshot:
    target_weights_id: str
    cash_weight: Decimal
    weights: dict[str, Decimal]
    source_signal_bundle_ids: tuple[str, ...]
    generated_by: str
    validation_status: str


def build_recommendation(
    *,
    signal_bundle: SignalBundle | Mapping[str, Any],
    target_weights: TargetWeights | Mapping[str, Any],
    evidence_claims: Sequence[EvidenceClaim],
    model_run_ids: Sequence[str],
    created_at: datetime,
    policy_context: RecommendationPolicyContext | None = None,
    event_sink: EventSink | None = None,
    run_id: str | None = None,
) -> RecommendationBuildResult:
    require_aware_datetime(created_at, "created_at")
    signal = _signal_snapshot(signal_bundle)
    target = _target_weights_snapshot(target_weights)
    claims = _evidence_claims(evidence_claims)
    evidence_ids = _evidence_ids(claims)
    model_ids = _model_run_ids(model_run_ids)

    score = _recommendation_score(signal)
    target_weight = target.weights.get(signal.ticker, ZERO)
    action = _recommendation_action(score, target_weight)
    context = policy_context or RecommendationPolicyContext()
    deterministic_checks = _deterministic_checks(
        signal=signal,
        target=target,
        claims=claims,
        context=context,
    )
    decision = evaluate_publication_policy(deterministic_checks, context)
    recommendation_id = _recommendation_id(
        signal=signal,
        target=target,
        evidence_ids=evidence_ids,
        model_run_ids=model_ids,
        action=action,
        score=score,
        suppression_reasons=decision.suppression_reasons,
        created_at=created_at,
    )
    status = "published" if decision.should_publish else "suppressed"

    artifact = RecommendationArtifact(
        recommendation_id=recommendation_id,
        ticker_or_portfolio=signal.ticker,
        advisory_label=AdvisoryLabel.ADVISORY_ONLY,
        action=action,
        horizon="medium_term",
        score_breakdown={
            "strategic_thesis_score": str(signal.strategic_thesis_score),
            "tactical_technical_score": str(signal.tactical_technical_score),
            "forward_indicator_score": str(signal.forward_indicator_score),
            "portfolio_risk_score": str(signal.portfolio_risk_score),
            "recommendation_score": str(score),
            "target_weight": str(target_weight),
            "cash_weight": str(target.cash_weight),
        },
        target_weights_id=target.target_weights_id,
        evidence_ids=evidence_ids,
        model_run_ids=model_ids,
        signal_bundle_id=signal.signal_bundle_id,
        risks=_risk_findings(claims),
        contradictions=_contradiction_findings(claims),
        final_payload={
            "summary": _deterministic_summary(
                action, signal.ticker, decision.suppression_reasons
            ),
            "publication_status": status,
            "suppression_reasons": decision.suppression_reasons,
            "narrative_source": "deterministic_placeholder_with_audited_model_runs",
            "audited_model_run_ids": model_ids,
            "advisory_only": True,
            "manual_trade_journal_only": True,
        },
        created_at=created_at,
    )
    audit = RecommendationAudit(
        audit_id=_audit_id(recommendation_id, deterministic_checks),
        recommendation_id=recommendation_id,
        target_weights_id=target.target_weights_id,
        signal_bundle_id=signal.signal_bundle_id,
        evidence_ids=evidence_ids,
        model_run_ids=model_ids,
        deterministic_checks={
            **deterministic_checks,
            "suppression_reasons": decision.suppression_reasons,
        },
        reviewer_findings={
            "status": "deterministic_placeholder",
            "model_run_ids": model_ids,
        },
        schema_valid=decision.should_publish,
        created_at=created_at,
    )
    if event_sink is not None:
        weights_event = build_event(
            kind="weights_generated",
            run_id=run_id,
            payload={
                "target_weights_id": target.target_weights_id,
                "ticker": signal.ticker,
                "cash_weight": str(target.cash_weight),
                "validation_status": target.validation_status,
            },
            occurred_at=created_at,
        )
        event_sink(weights_event)
        recommendation_event = build_event(
            kind="recommendation_issued",
            run_id=run_id,
            payload={
                "recommendation_id": recommendation_id,
                "ticker": signal.ticker,
                "action": action.value,
                "should_publish": decision.should_publish,
                "suppression_reasons": list(decision.suppression_reasons),
            },
            occurred_at=created_at,
        )
        event_sink(recommendation_event)
    return RecommendationBuildResult(
        artifact=artifact,
        audit=audit,
        should_publish=decision.should_publish,
        suppression_reasons=decision.suppression_reasons,
    )


def _signal_snapshot(
    signal_bundle: SignalBundle | Mapping[str, Any],
) -> _SignalSnapshot:
    if isinstance(signal_bundle, SignalBundle):
        return _SignalSnapshot(
            signal_bundle_id=require_text(
                signal_bundle.signal_bundle_id, "signal_bundle_id"
            ),
            ticker=require_text(signal_bundle.ticker, "ticker").upper(),
            strategic_thesis_score=Decimal(str(signal_bundle.strategic_thesis_score)),
            tactical_technical_score=Decimal(
                str(signal_bundle.tactical_technical_score)
            ),
            forward_indicator_score=Decimal(str(signal_bundle.forward_indicator_score)),
            portfolio_risk_score=Decimal(str(signal_bundle.portfolio_risk_score)),
        )
    if not isinstance(signal_bundle, Mapping):
        raise ValueError(
            "signal_bundle must be a SignalBundle or persisted SignalBundle record"
        )
    required = {
        "signal_bundle_id",
        "ticker",
        "strategic_thesis_score",
        "tactical_technical_score",
        "forward_indicator_score",
        "portfolio_risk_score",
    }
    if not required <= set(signal_bundle):
        raise ValueError(
            "signal_bundle must be a SignalBundle or persisted SignalBundle record"
        )
    return _SignalSnapshot(
        signal_bundle_id=require_text(
            signal_bundle.get("signal_bundle_id"), "signal_bundle_id"
        ),
        ticker=require_text(signal_bundle.get("ticker"), "ticker").upper(),
        strategic_thesis_score=Decimal(str(signal_bundle["strategic_thesis_score"])),
        tactical_technical_score=Decimal(
            str(signal_bundle["tactical_technical_score"])
        ),
        forward_indicator_score=Decimal(str(signal_bundle["forward_indicator_score"])),
        portfolio_risk_score=Decimal(str(signal_bundle["portfolio_risk_score"])),
    )


def _target_weights_snapshot(
    target_weights: TargetWeights | Mapping[str, Any],
) -> _TargetWeightsSnapshot:
    if isinstance(target_weights, TargetWeights):
        return _make_target_snapshot(
            target_weights_id=target_weights.target_weights_id,
            cash_weight=target_weights.cash_weight,
            weights=target_weights.weights,
            source_signal_bundle_ids=target_weights.source_signal_bundle_ids,
            generated_by=target_weights.generated_by,
            validation_status=target_weights.validation_status,
        )
    if not isinstance(target_weights, Mapping):
        raise ValueError(
            "target_weights must be a TargetWeights instance or persisted TargetWeights record"
        )
    required = {
        "target_weights_id",
        "cash_weight",
        "weights",
        "source_signal_bundle_ids",
        "generated_by",
        "validation_status",
    }
    if not required <= set(target_weights):
        raise ValueError(
            "target_weights must be a TargetWeights instance or persisted TargetWeights record"
        )
    return _make_target_snapshot(
        target_weights_id=target_weights.get("target_weights_id"),
        cash_weight=target_weights["cash_weight"],
        weights=target_weights["weights"],
        source_signal_bundle_ids=target_weights["source_signal_bundle_ids"],
        generated_by=target_weights.get("generated_by"),
        validation_status=target_weights.get("validation_status"),
    )


def _make_target_snapshot(
    *,
    target_weights_id: Any,
    cash_weight: Any,
    weights: Any,
    source_signal_bundle_ids: Any,
    generated_by: Any,
    validation_status: Any,
) -> _TargetWeightsSnapshot:
    generated_by_text = require_text(generated_by, "generated_by")
    if generated_by_text.lower() in FORBIDDEN_WEIGHT_GENERATORS:
        raise ValueError(
            "TargetWeights must be generated by deterministic portfolio code"
        )
    if not isinstance(weights, Mapping) or not weights:
        raise ValueError("weights must not be empty")
    normalized_weights = {
        require_text(ticker, "weights ticker").upper(): Decimal(str(weight))
        for ticker, weight in weights.items()
    }
    source_ids = tuple(
        dict.fromkeys(
            require_text(source_id, "source_signal_bundle_ids")
            for source_id in require_non_empty_tuple(
                normalize_tuple(source_signal_bundle_ids, "source_signal_bundle_ids"),
                "source_signal_bundle_ids",
            )
        )
    )
    return _TargetWeightsSnapshot(
        target_weights_id=require_text(target_weights_id, "target_weights_id"),
        cash_weight=Decimal(str(cash_weight)),
        weights=normalized_weights,
        source_signal_bundle_ids=source_ids,
        generated_by=generated_by_text,
        validation_status=require_text(validation_status, "validation_status"),
    )


def _evidence_claims(
    evidence_claims: Sequence[EvidenceClaim],
) -> tuple[EvidenceClaim, ...]:
    claims = require_non_empty_tuple(
        normalize_tuple(evidence_claims, "evidence_claims"), "evidence_claims"
    )
    for claim in claims:
        if not isinstance(claim, EvidenceClaim):
            raise ValueError("evidence_claims must contain EvidenceClaim records")
        require_text(claim.evidence_id, "evidence_id")
    return claims


def _evidence_ids(claims: Sequence[EvidenceClaim]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            require_text(claim.evidence_id, "evidence_id") for claim in claims
        )
    )


def _model_run_ids(model_run_ids: Sequence[str]) -> tuple[str, ...]:
    ids = tuple(
        dict.fromkeys(
            require_text(model_run_id, "model_run_ids")
            for model_run_id in require_non_empty_tuple(
                normalize_tuple(model_run_ids, "model_run_ids"), "model_run_ids"
            )
        )
    )
    return require_non_empty_tuple(ids, "model_run_ids")


def _deterministic_checks(
    *,
    signal: _SignalSnapshot,
    target: _TargetWeightsSnapshot,
    claims: Sequence[EvidenceClaim],
    context: RecommendationPolicyContext,
) -> dict[str, Any]:
    evidence_claim_tickers = {claim.ticker_or_theme.upper() for claim in claims}
    total_weight = target.cash_weight + sum(target.weights.values(), ZERO)
    weights_in_unit_bounds = ZERO <= target.cash_weight <= ONE and all(
        ZERO <= weight <= ONE for weight in target.weights.values()
    )
    return {
        "advisory_only": True,
        "signal_bundle_id_present": bool(signal.signal_bundle_id),
        "target_weights_id_present": bool(target.target_weights_id),
        "evidence_ids_present": bool(_evidence_ids(claims)),
        "target_weights_generated_by_deterministic": "deterministic"
        in target.generated_by.lower(),
        "target_weights_validated": target.validation_status == "validated",
        "target_weights_unit_bounds_valid": weights_in_unit_bounds,
        "source_signal_bundle_linked": signal.signal_bundle_id
        in target.source_signal_bundle_ids,
        "target_weights_sum_valid": abs(total_weight - ONE) <= WEIGHT_TOLERANCE,
        "evidence_covers_signal": signal.ticker in evidence_claim_tickers,
        "stale_evidence_ids": context.stale_evidence_ids,
        "quarantined_evidence_ids": context.quarantined_evidence_ids,
        "incident_freeze_active": context.incident_freeze_active,
    }


def _recommendation_score(signal: _SignalSnapshot) -> Decimal:
    return _quantize(
        signal.strategic_thesis_score * Decimal("0.45")
        + signal.tactical_technical_score * Decimal("0.25")
        + signal.forward_indicator_score * Decimal("0.20")
        + (ONE - signal.portfolio_risk_score) * Decimal("0.10")
    )


def _recommendation_action(
    score: Decimal, target_weight: Decimal
) -> RecommendationAction:
    if score >= Decimal("0.75") and target_weight >= Decimal("0.25"):
        return RecommendationAction.CORE_BUY
    if score >= Decimal("0.60") and target_weight > ZERO:
        return RecommendationAction.ACCUMULATE
    if score >= Decimal("0.45") and target_weight > ZERO:
        return RecommendationAction.HOLD
    if score >= Decimal("0.35"):
        return RecommendationAction.WATCH
    return RecommendationAction.AVOID


def _risk_findings(claims: Sequence[EvidenceClaim]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                claim.claim_type
                for claim in claims
                if (claim.direction or "").lower() == "negative"
                or "risk" in claim.claim_type.lower()
            }
        )
    )


def _contradiction_findings(claims: Sequence[EvidenceClaim]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                claim.claim_type
                for claim in claims
                if "contradiction" in claim.claim_type.lower()
            }
        )
    )


def _deterministic_summary(
    action: RecommendationAction,
    ticker: str,
    suppression_reasons: tuple[str, ...],
) -> str:
    if suppression_reasons:
        reasons = ", ".join(suppression_reasons)
        return f"Advisory-only {action.value} for {ticker}; publication suppressed by deterministic policy: {reasons}."
    return f"Advisory-only {action.value} for {ticker}; deterministic signals, target weights, evidence, and audited model runs are linked."


def _recommendation_id(
    *,
    signal: _SignalSnapshot,
    target: _TargetWeightsSnapshot,
    evidence_ids: tuple[str, ...],
    model_run_ids: tuple[str, ...],
    action: RecommendationAction,
    score: Decimal,
    suppression_reasons: tuple[str, ...],
    created_at: datetime,
) -> str:
    digest = stable_hash_payload(
        {
            "signal_bundle_id": signal.signal_bundle_id,
            "ticker": signal.ticker,
            "target_weights_id": target.target_weights_id,
            "evidence_ids": evidence_ids,
            "model_run_ids": model_run_ids,
            "action": action,
            "score": score,
            "suppression_reasons": suppression_reasons,
            "created_at": created_at,
        }
    )
    return f"recommendation-{digest[:16]}"


def _audit_id(recommendation_id: str, deterministic_checks: dict[str, Any]) -> str:
    digest = stable_hash_payload(
        {
            "recommendation_id": recommendation_id,
            "deterministic_checks": deterministic_checks,
        }
    )
    return f"recommendation-audit-{digest[:16]}"


def _quantize(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(SCORE_QUANT, rounding=ROUND_HALF_UP).normalize()
