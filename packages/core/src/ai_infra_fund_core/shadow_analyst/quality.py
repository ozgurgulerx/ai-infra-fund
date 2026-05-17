from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Mapping, Sequence

from ai_infra_fund_core.contracts.common import normalize_tuple, require_text


class DraftQualityRecommendation(str, Enum):
    REJECT = "reject"
    KEEP_REVIEW_REQUIRED = "keep_review_required"
    ELIGIBLE_FOR_HUMAN_REVIEW = "eligible_for_human_review"


@dataclass(frozen=True, slots=True)
class DraftEvidenceReference:
    evidence_id: str
    text: str
    available_at: datetime | None = None
    source_uri: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", require_text(self.evidence_id, "evidence_id").strip())
        object.__setattr__(self, "text", require_text(self.text, "text").strip())
        if self.available_at is not None and (
            self.available_at.tzinfo is None
            or self.available_at.tzinfo.utcoffset(self.available_at) is None
        ):
            raise ValueError("available_at must be timezone-aware when provided")
        if self.source_uri is not None:
            object.__setattr__(self, "source_uri", self.source_uri.strip() or None)


@dataclass(frozen=True, slots=True)
class DraftQualityContext:
    evidence: tuple[DraftEvidenceReference, ...]
    known_tickers: tuple[str, ...] = ()
    known_segments: tuple[str, ...] = ()
    known_object_ids: tuple[str, ...] = ()
    as_of: datetime | None = None
    max_evidence_age_days: int = 30

    def __post_init__(self) -> None:
        evidence = tuple(self.evidence)
        if not all(isinstance(item, DraftEvidenceReference) for item in evidence):
            raise ValueError("evidence must contain DraftEvidenceReference instances")
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "known_tickers", tuple(item.upper() for item in _text_tuple(self.known_tickers)))
        object.__setattr__(self, "known_segments", tuple(item.lower() for item in _text_tuple(self.known_segments)))
        object.__setattr__(self, "known_object_ids", _text_tuple(self.known_object_ids))
        if self.as_of is not None and (
            self.as_of.tzinfo is None or self.as_of.tzinfo.utcoffset(self.as_of) is None
        ):
            raise ValueError("as_of must be timezone-aware when provided")
        if self.max_evidence_age_days <= 0:
            raise ValueError("max_evidence_age_days must be positive")


@dataclass(frozen=True, slots=True)
class DraftQualityEvaluation:
    draft_quality_score: int
    ticker_specificity_score: int
    evaluator_findings: tuple[str, ...]
    blocking_issues: tuple[str, ...]
    non_blocking_warnings: tuple[str, ...]
    recommendation: DraftQualityRecommendation

    def to_dict(self) -> dict[str, object]:
        return {
            "draft_quality_score": self.draft_quality_score,
            "ticker_specificity_score": self.ticker_specificity_score,
            "evaluator_findings": list(self.evaluator_findings),
            "blocking_issues": list(self.blocking_issues),
            "non_blocking_warnings": list(self.non_blocking_warnings),
            "recommendation": self.recommendation.value,
        }


FORBIDDEN_EXECUTION_PATTERNS = (
    r"\bplace\s+(?:an?\s+)?order\b",
    r"\bsubmit\s+(?:an?\s+)?order\b",
    r"\bexecute\s+(?:an?\s+)?trade\b",
    r"\bexecute\s+(?:an?\s+)?order\b",
    r"\border\s+ticket\b",
    r"\broute\s+to\s+broker\b",
    r"\bbroker\s+account\b",
    r"\bfill\s+status\b",
    r"\bautomated\s+trading\b",
)

GENERIC_TERMS = frozenset(
    {
        "conditions",
        "market",
        "markets",
        "mixed",
        "monitor",
        "monitored",
        "important",
        "uncertain",
        "uncertainty",
        "situation",
        "setup",
    }
)

STOPWORDS = frozenset(
    {
        "about",
        "after",
        "again",
        "also",
        "because",
        "before",
        "between",
        "could",
        "from",
        "have",
        "into",
        "more",
        "over",
        "should",
        "that",
        "their",
        "there",
        "this",
        "through",
        "while",
        "with",
        "would",
    }
)

NON_TICKER_ACRONYMS = frozenset(
    {
        "AI",
        "API",
        "ASIC",
        "CPU",
        "EDA",
        "EPS",
        "FRED",
        "GPU",
        "HBM",
        "IR",
        "LLM",
        "PPA",
        "SEC",
    }
)

WHITELISTED_PUBLICATION_FIELDS = frozenset(
    {
        "advisory_label",
        "analyst_action",
        "context_used",
        "decision_rationale",
        "headline",
        "market_event_ids",
        "monitor_only_hypothesis",
        "rationale",
        "summary",
        "supported_claim",
        "ticker",
        "ticker_implications",
        "weak_inference",
    }
)

ALLOWED_TICKER_IMPLICATION_DIRECTIONS = frozenset(
    {"positive", "negative", "mixed", "neutral"}
)
ALLOWED_TICKER_IMPLICATION_STANCES = frozenset(
    {"watch", "accumulate", "hold", "trim", "avoid", "exit-candidate", "review"}
)
MIN_TICKER_IMPLICATIONS_FOR_DAILY_BRIEF = 5


def evaluate_shadow_analyst_draft(
    draft: object,
    context: DraftQualityContext,
) -> DraftQualityEvaluation:
    evidence_by_id = {item.evidence_id: item for item in context.evidence}
    draft_type = _field(draft, "draft_type") or type(draft).__name__
    evidence_ids = _field_tuple(draft, "evidence_ids")
    material_claims = _material_claims(draft)
    payload = _payload(draft)
    text = _draft_text(draft)
    visible_text = _visible_draft_text(draft)
    findings: list[str] = []
    blocking: list[str] = []
    warnings: list[str] = []
    score = 100
    ticker_specificity_score = 0

    if not evidence_ids:
        blocking.append("missing evidence IDs")
        score -= 35
    else:
        findings.append(f"{draft_type} cites {len(evidence_ids)} evidence ID(s).")

    unknown_evidence_ids = sorted(set(evidence_ids) - set(evidence_by_id))
    if unknown_evidence_ids:
        blocking.append(f"unknown evidence IDs: {', '.join(unknown_evidence_ids)}")
        score -= 30

    if not material_claims:
        blocking.append("missing material claims")
        score -= 20

    for claim_text, claim_evidence_ids in material_claims:
        if not claim_evidence_ids:
            blocking.append(f"claim has no evidence IDs: {claim_text[:80]}")
            score -= 20
            continue
        claim_not_top_level = sorted(set(claim_evidence_ids) - set(evidence_ids))
        if evidence_ids and claim_not_top_level:
            blocking.append(
                "claim evidence IDs must be a subset of top-level evidence IDs: "
                + ", ".join(claim_not_top_level)
            )
            score -= 25
            continue
        claim_unknown = sorted(set(claim_evidence_ids) - set(evidence_by_id))
        if claim_unknown:
            blocking.append(f"claim references unknown evidence IDs: {', '.join(claim_unknown)}")
            score -= 25
            continue
        if not _claim_supported_by_evidence(claim_text, claim_evidence_ids, evidence_by_id):
            if _is_generic_claim(claim_text):
                warnings.append(
                    f"generic claim lacks specific evidence support and should stay review_required: {claim_text[:80]}"
                )
                score -= 10
                continue
            blocking.append(f"unsupported claim-to-evidence link: {claim_text[:100]}")
            score -= 25

    forbidden_hits = _forbidden_execution_hits(text)
    if forbidden_hits:
        blocking.append(f"forbidden execution language: {', '.join(forbidden_hits)}")
        score -= 35

    if "advisory_only" in visible_text.lower() or "advisory-only" in visible_text.lower():
        findings.append("Draft uses advisory-only framing.")
    else:
        warnings.append("advisory-only framing is not explicit in draft text")
        score -= 5

    valid_ticker_implications, implication_blocking, implication_warnings = _ticker_implication_audit(
        draft,
        context,
        evidence_by_id,
        top_level_evidence_ids=evidence_ids,
    )
    ticker_specificity_score = _ticker_specificity_score(
        valid_count=len(valid_ticker_implications),
        total_count=len(_ticker_implications(draft)),
    )
    blocking.extend(implication_blocking)
    warnings.extend(implication_warnings)
    score -= 25 * len(implication_blocking)
    score -= 10 * len(implication_warnings)

    if _is_analyst_brief_draft(draft_type):
        ticker_implications = _ticker_implications(draft)
        required_implication_count = _required_ticker_implication_count(context)
        if not ticker_implications:
            warnings.append("analyst brief draft is missing ticker implications")
            score -= 20
        elif ticker_specificity_score < 80:
            warnings.append(
                "analyst brief draft lacks enough complete evidence-linked ticker implications "
                "with invalidation"
            )
            score -= 20
        elif required_implication_count and len(valid_ticker_implications) < required_implication_count:
            warnings.append(
                "analyst brief draft has fewer than "
                f"{required_implication_count} complete ticker implications"
            )
            score -= 15
        else:
            findings.append(
                f"Ticker implication specificity score is {ticker_specificity_score}."
            )
        missing_separation = _missing_claim_separation_fields(draft)
        if missing_separation:
            warnings.append(
                "analyst brief draft does not separate supported_claim, weak_inference, "
                f"and monitor_only_hypothesis: missing {', '.join(missing_separation)}"
            )
            score -= 5
        else:
            findings.append("Draft separates supported claim, weak inference, and monitor-only hypothesis.")

    specificity_score = _specificity_score(text, context, valid_ticker_implications)
    if specificity_score < 2:
        warnings.append("draft is too generic and lacks enough ticker or segment specificity")
        score -= 25
    elif specificity_score < 4:
        warnings.append("draft has limited specificity and should stay review_required")
        score -= 10
    else:
        findings.append("Draft has ticker or AI infrastructure segment specificity.")

    searchable_payload = {
        **payload,
        "ticker_implications": _jsonable(_ticker_implications(draft)),
    }
    unknown_tickers = _unknown_payload_tickers(searchable_payload, context.known_tickers)
    if unknown_tickers:
        blocking.append(f"unknown ticker references: {', '.join(unknown_tickers)}")
        score -= 25

    unknown_context_ids = _unknown_context_ids(draft, context, evidence_by_id)
    if unknown_context_ids:
        blocking.append(f"unknown context IDs: {', '.join(unknown_context_ids)}")
        score -= 20

    if not _has_uncertainty_language(text):
        warnings.append("uncertainty, risk, or invalidation language is weak")
        score -= 10
    else:
        findings.append("Draft includes risk, uncertainty, or invalidation framing.")

    if not _rationale_useful(draft):
        warnings.append("decision rationale is missing or not useful enough")
        score -= 15
    else:
        findings.append("Decision rationale is present and reviewable.")

    stale_ids = _stale_evidence_ids(evidence_ids, context)
    if stale_ids:
        blocking.append(f"stale evidence IDs: {', '.join(stale_ids)}")
        score -= 25

    score = max(0, min(100, score))
    recommendation = _recommendation(score, blocking, warnings)
    return DraftQualityEvaluation(
        draft_quality_score=score,
        ticker_specificity_score=ticker_specificity_score,
        evaluator_findings=tuple(findings),
        blocking_issues=tuple(dict.fromkeys(blocking)),
        non_blocking_warnings=tuple(dict.fromkeys(warnings)),
        recommendation=recommendation,
    )


def build_sanitized_publication_payload(
    draft: object,
    evaluation: DraftQualityEvaluation,
    *,
    reviewer: str,
    accepted_at: datetime,
) -> dict[str, object]:
    if evaluation.recommendation is not DraftQualityRecommendation.ELIGIBLE_FOR_HUMAN_REVIEW:
        raise ValueError("draft is not eligible for human review acceptance")
    if evaluation.blocking_issues:
        raise ValueError("draft has blocking quality issues")
    if accepted_at.tzinfo is None or accepted_at.tzinfo.utcoffset(accepted_at) is None:
        raise ValueError("accepted_at must be timezone-aware")

    evidence_ids = list(_field_tuple(draft, "evidence_ids"))
    model_run_id = require_text(str(_field(draft, "model_run_id") or ""), "model_run_id")
    accepted_fields = _accepted_fields(draft)
    return {
        "advisory_label": "advisory_only",
        "source_draft_id": _field(draft, "draft_id"),
        "source_draft_type": _field(draft, "draft_type") or type(draft).__name__,
        "source_model_run_id": model_run_id,
        "evidence_ids": evidence_ids,
        "readiness_checks": [
            "quality_checks_passed",
            "human_manual_acceptance_recorded",
            "advisory_only_label_present",
            "evidence_ids_validated",
            "model_run_id_linked",
            "raw_draft_not_blindly_copied",
        ],
        "accepted_by": require_text(reviewer, "reviewer").strip(),
        "accepted_at": accepted_at.astimezone(timezone.utc).isoformat(),
        "draft_quality_score": evaluation.draft_quality_score,
        "evaluator_findings": list(evaluation.evaluator_findings),
        "accepted_fields": accepted_fields,
    }


def _recommendation(
    score: int,
    blocking: Sequence[str],
    warnings: Sequence[str],
) -> DraftQualityRecommendation:
    if blocking:
        return DraftQualityRecommendation.REJECT
    if score >= 85 and not warnings:
        return DraftQualityRecommendation.ELIGIBLE_FOR_HUMAN_REVIEW
    return DraftQualityRecommendation.KEEP_REVIEW_REQUIRED


def _material_claims(draft: object) -> tuple[tuple[str, tuple[str, ...]], ...]:
    raw_claims = _field(draft, "material_claims")
    claims: list[tuple[str, tuple[str, ...]]] = []
    for raw_claim in normalize_tuple(raw_claims, "material_claims"):
        if isinstance(raw_claim, Mapping):
            claim_text = str(raw_claim.get("claim") or "")
            evidence_ids = _text_tuple(raw_claim.get("evidence_ids"))
        else:
            claim_text = str(getattr(raw_claim, "claim", ""))
            evidence_ids = _text_tuple(getattr(raw_claim, "evidence_ids", ()))
        if claim_text.strip():
            claims.append((claim_text.strip(), evidence_ids))
    return tuple(claims)


def _claim_supported_by_evidence(
    claim_text: str,
    claim_evidence_ids: Sequence[str],
    evidence_by_id: Mapping[str, DraftEvidenceReference],
) -> bool:
    claim_tokens = _meaningful_tokens(claim_text)
    if len(claim_tokens) < 2:
        return False
    for evidence_id in claim_evidence_ids:
        evidence = evidence_by_id[evidence_id]
        evidence_tokens = _meaningful_tokens(evidence.text)
        overlap = claim_tokens & evidence_tokens
        if len(overlap) >= 2:
            return True
    return False


def _is_generic_claim(claim_text: str) -> bool:
    tokens = _meaningful_tokens(claim_text)
    return bool(tokens) and len(tokens - GENERIC_TERMS) <= 2


def _meaningful_tokens(text: str) -> set[str]:
    tokens = set(re.findall(r"[A-Za-z][A-Za-z0-9_+-]{1,}", text.lower()))
    return {token for token in tokens if token not in STOPWORDS and len(token) > 2}


def _draft_text(draft: object) -> str:
    parts: list[str] = []
    for name in (
        "headline",
        "summary",
        "decision_rationale",
        "rationale",
        "assessment",
        "bull_case",
        "bear_case",
        "invalidation_condition",
        "supported_claim",
        "weak_inference",
        "monitor_only_hypothesis",
    ):
        value = _field(draft, name)
        if value:
            parts.append(str(value))
    for claim, _evidence_ids in _material_claims(draft):
        parts.append(claim)
    for implication in _ticker_implications(draft):
        parts.append(str(_jsonable(implication)))
    parts.append(str(_payload(draft)))
    return " ".join(parts)


def _visible_draft_text(draft: object) -> str:
    parts: list[str] = []
    for name in (
        "headline",
        "summary",
        "decision_rationale",
        "rationale",
        "assessment",
        "bull_case",
        "bear_case",
        "supported_claim",
        "weak_inference",
        "monitor_only_hypothesis",
    ):
        value = _field(draft, name)
        if value:
            parts.append(str(value))
    return " ".join(parts)


def _payload(draft: object) -> dict[str, Any]:
    payload = _field(draft, "payload")
    if isinstance(payload, Mapping):
        return dict(payload)
    if isinstance(draft, Mapping):
        payload_json = draft.get("payload_json")
        if isinstance(payload_json, Mapping):
            nested = payload_json.get("payload")
            if isinstance(nested, Mapping):
                return dict(nested)
            return dict(payload_json)
    return {}


def _forbidden_execution_hits(text: str) -> tuple[str, ...]:
    hits: list[str] = []
    for pattern in FORBIDDEN_EXECUTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(pattern.replace(r"\b", "").replace("\\s+", " "))
    return tuple(hits)


def _specificity_score(
    text: str,
    context: DraftQualityContext,
    valid_ticker_implications: Sequence[object],
) -> int:
    lowered = text.lower()
    tokens = _meaningful_tokens(text)
    score = 0
    score += sum(1 for ticker in context.known_tickers if re.search(rf"\b{re.escape(ticker)}\b", text))
    score += sum(1 for segment in context.known_segments if segment.replace("_", " ") in lowered or segment in lowered)
    score += len(
        {
            _implication_text(implication, "ticker").upper()
            for implication in valid_ticker_implications
            if _implication_text(implication, "ticker")
        }
    )
    if len(tokens - GENERIC_TERMS) >= 8:
        score += 1
    return score


def _unknown_payload_tickers(
    payload: Mapping[str, object],
    known_tickers: Sequence[str],
) -> tuple[str, ...]:
    if not known_tickers:
        return ()
    known = {ticker.upper() for ticker in known_tickers}
    discovered: set[str] = set()
    for key, value in _walk_payload(payload):
        if "ticker" in key.lower() or key.lower() in {"focus", "tickers"}:
            discovered.update(_ticker_tokens(str(value)))
    return tuple(sorted(token for token in discovered if token not in known))


def _ticker_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"\b[A-Z]{2,5}\b", text)
        if token not in NON_TICKER_ACRONYMS
    }


def _walk_payload(value: object, key: str = "") -> tuple[tuple[str, object], ...]:
    rows: list[tuple[str, object]] = []
    if isinstance(value, Mapping):
        for nested_key, nested_value in value.items():
            nested_key_text = str(nested_key)
            rows.extend(_walk_payload(nested_value, nested_key_text))
    elif isinstance(value, (list, tuple)):
        for item in value:
            rows.extend(_walk_payload(item, key))
    else:
        rows.append((key, value))
    return tuple(rows)


def _unknown_context_ids(
    draft: object,
    context: DraftQualityContext,
    evidence_by_id: Mapping[str, DraftEvidenceReference],
) -> tuple[str, ...]:
    known = set(evidence_by_id) | set(context.known_object_ids)
    context_ids = _field_tuple(draft, "context_used")
    if not context_ids:
        return ()
    return tuple(sorted(context_id for context_id in context_ids if context_id not in known))


def _has_uncertainty_language(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "risk",
            "uncertain",
            "uncertainty",
            "invalidation",
            "monitor",
            "review-required",
            "review required",
            "contradiction",
            "stale",
            "policy",
            "valuation",
        )
    )


def _rationale_useful(draft: object) -> bool:
    rationale = str(_field(draft, "decision_rationale") or _field(draft, "rationale") or "")
    if len(rationale.split()) < 12:
        return False
    return bool(_field_tuple(draft, "context_used") or _field_tuple(draft, "evidence_ids"))


def _stale_evidence_ids(
    evidence_ids: Sequence[str],
    context: DraftQualityContext,
) -> tuple[str, ...]:
    if context.as_of is None:
        return ()
    evidence_by_id = {item.evidence_id: item for item in context.evidence}
    stale: list[str] = []
    for evidence_id in evidence_ids:
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None or evidence.available_at is None:
            continue
        age_days = (context.as_of - evidence.available_at).days
        if age_days > context.max_evidence_age_days:
            stale.append(evidence_id)
    return tuple(stale)


def _accepted_fields(draft: object) -> dict[str, object]:
    fields: dict[str, object] = {}
    for name in WHITELISTED_PUBLICATION_FIELDS:
        value = _field(draft, name)
        if value is not None:
            fields[name] = _jsonable(value)
    payload = _payload(draft)
    for name in WHITELISTED_PUBLICATION_FIELDS:
        if name in payload and name not in fields:
            fields[name] = _jsonable(payload[name])
    fields["material_claims"] = [
        {"claim": claim, "evidence_ids": list(evidence_ids)}
        for claim, evidence_ids in _material_claims(draft)
    ]
    return fields


def _ticker_implication_audit(
    draft: object,
    context: DraftQualityContext,
    evidence_by_id: Mapping[str, DraftEvidenceReference],
    *,
    top_level_evidence_ids: Sequence[str],
) -> tuple[tuple[object, ...], tuple[str, ...], tuple[str, ...]]:
    valid: list[object] = []
    blocking: list[str] = []
    warnings: list[str] = []
    known_tickers = set(context.known_tickers)
    top_level_set = set(top_level_evidence_ids)

    for index, implication in enumerate(_ticker_implications(draft), start=1):
        label = f"ticker implication {index}"
        ticker = _implication_text(implication, "ticker").upper()
        direction = _implication_text(implication, "direction").lower()
        stance = _implication_text(implication, "advisory_stance").lower()
        evidence_ids = _text_tuple(_implication_value(implication, "evidence_ids"))
        required_text_fields = (
            "theme_or_segment",
            "confidence_delta",
            "time_horizon",
            "what_changed",
            "why_it_matters",
            "invalidation_signal",
        )
        missing_fields = [
            field_name
            for field_name in required_text_fields
            if not _implication_text(implication, field_name)
        ]
        if not ticker:
            missing_fields.append("ticker")
        if not evidence_ids:
            missing_fields.append("evidence_ids")
        if not _text_tuple(_implication_value(implication, "risk_flags")):
            missing_fields.append("risk_flags")
        if missing_fields:
            warnings.append(f"{label} missing required fields: {', '.join(missing_fields)}")
            continue
        if known_tickers and ticker not in known_tickers:
            blocking.append(f"{label} references unknown ticker: {ticker}")
            continue
        if direction not in ALLOWED_TICKER_IMPLICATION_DIRECTIONS:
            warnings.append(f"{label} has invalid direction: {direction}")
            continue
        if stance not in ALLOWED_TICKER_IMPLICATION_STANCES:
            warnings.append(f"{label} has invalid advisory stance: {stance}")
            continue
        not_top_level = sorted(set(evidence_ids) - top_level_set)
        if top_level_set and not_top_level:
            blocking.append(
                f"{label} evidence IDs must be a subset of top-level evidence IDs: "
                + ", ".join(not_top_level)
            )
            continue
        unknown_evidence = sorted(set(evidence_ids) - set(evidence_by_id))
        if unknown_evidence:
            blocking.append(f"{label} references unknown evidence IDs: {', '.join(unknown_evidence)}")
            continue

        support_text = " ".join(
            _implication_text(implication, field_name)
            for field_name in ("ticker", "theme_or_segment", "what_changed", "why_it_matters")
        )
        if not _claim_supported_by_evidence(support_text, evidence_ids, evidence_by_id):
            warnings.append(f"{label} is not clearly supported by cited evidence")
            continue
        valid.append(implication)

    return tuple(valid), tuple(blocking), tuple(warnings)


def _ticker_specificity_score(*, valid_count: int, total_count: int) -> int:
    if total_count <= 0:
        return 0
    return max(0, min(100, round((valid_count / total_count) * 100)))


def _required_ticker_implication_count(context: DraftQualityContext) -> int:
    if len(context.known_tickers) >= MIN_TICKER_IMPLICATIONS_FOR_DAILY_BRIEF:
        return MIN_TICKER_IMPLICATIONS_FOR_DAILY_BRIEF
    return len(context.known_tickers)


def _missing_claim_separation_fields(draft: object) -> tuple[str, ...]:
    missing: list[str] = []
    for field_name in ("supported_claim", "weak_inference", "monitor_only_hypothesis"):
        if not str(_field(draft, field_name) or "").strip():
            missing.append(field_name)
    return tuple(missing)


def _ticker_implications(draft: object) -> tuple[object, ...]:
    raw = _field(draft, "ticker_implications")
    if raw is None:
        payload = _payload(draft)
        raw = payload.get("ticker_implications")
    return tuple(normalize_tuple(raw, "ticker_implications"))


def _implication_value(implication: object, field_name: str) -> object | None:
    if isinstance(implication, Mapping):
        return implication.get(field_name)
    return getattr(implication, field_name, None)


def _implication_text(implication: object, field_name: str) -> str:
    value = _implication_value(implication, field_name)
    if value is None:
        return ""
    return str(value).strip()


def _is_analyst_brief_draft(draft_type: object) -> bool:
    return str(draft_type).lower() in {"analystbriefdraft", "analyst_brief_draft"}


def _jsonable(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _field_tuple(draft: object, field_name: str) -> tuple[str, ...]:
    return _text_tuple(_field(draft, field_name))


def _text_tuple(value: object) -> tuple[str, ...]:
    return tuple(str(item).strip() for item in normalize_tuple(value, "value") if str(item).strip())


def _field(draft: object, field_name: str) -> object | None:
    if isinstance(draft, Mapping):
        if field_name in draft:
            return draft[field_name]
        payload_json = draft.get("payload_json")
        if isinstance(payload_json, Mapping) and field_name in payload_json:
            return payload_json[field_name]
    return getattr(draft, field_name, None)
