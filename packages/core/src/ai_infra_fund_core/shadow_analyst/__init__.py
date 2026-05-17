"""Governed shadow analyst context and draft pipeline."""

from .bundles import (
    AnalystContextBundle,
    AnalystContextScope,
    build_daily_analyst_context_bundle,
    build_ticker_analyst_context_bundle,
)
from .drafts import (
    AnalystBriefDraft,
    DraftReviewStatus,
    EquityImpactAssessmentDraft,
    MaterialClaimDraft,
    RejectedAnalystDraft,
    RiskRegimeUpdateDraft,
    SegmentImpactDraft,
    TickerImplicationDraft,
    TradingAdvisoryDraft,
    ValuationContextDraft,
)
from .pipeline import GovernedShadowAnalystPipeline, ShadowAnalystResult
from .quality import (
    DraftEvidenceReference,
    DraftQualityContext,
    DraftQualityEvaluation,
    DraftQualityRecommendation,
    build_sanitized_publication_payload,
    evaluate_shadow_analyst_draft,
)

__all__ = [
    "AnalystBriefDraft",
    "AnalystContextBundle",
    "AnalystContextScope",
    "DraftReviewStatus",
    "DraftEvidenceReference",
    "DraftQualityContext",
    "DraftQualityEvaluation",
    "DraftQualityRecommendation",
    "EquityImpactAssessmentDraft",
    "GovernedShadowAnalystPipeline",
    "MaterialClaimDraft",
    "RejectedAnalystDraft",
    "RiskRegimeUpdateDraft",
    "SegmentImpactDraft",
    "ShadowAnalystResult",
    "TickerImplicationDraft",
    "TradingAdvisoryDraft",
    "ValuationContextDraft",
    "build_sanitized_publication_payload",
    "build_daily_analyst_context_bundle",
    "build_ticker_analyst_context_bundle",
    "evaluate_shadow_analyst_draft",
]
