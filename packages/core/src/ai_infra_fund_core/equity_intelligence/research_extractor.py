"""Deep-research extension point.

Defines the `LLMClaimExtractor` Protocol that a future LLM-driven claim
extractor must implement. v1 ships only the `StubLLMClaimExtractor` —
a no-op that returns empty draft buckets and no model_runs. This keeps
the worker pipeline structurally complete and the upgrade path obvious.

When a real extractor is wired (Phase 10b):
  - It MUST check ``capture.data_class`` is in the cloud-allowed set
    before any model call.
  - Each call MUST emit a ``ModelRun`` record (so audit lineage is intact).
  - It MUST emit only draft `EvidenceClaim`, `SourceSignal`, or `MarketEvent`
    records with citations from allowed public data classes plus audit metadata.
    Deterministic code owns scoring and portfolio decisions; this is enforced by
    ``AGENTS.md`` and ``docs/specs/0013``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol, runtime_checkable

from .extraction import ExtractedDocument, RssItem


ALLOWED_CLOUD_DATA_CLASSES = frozenset(
    {"public_market_data", "public_evidence", "derived_analytics"}
)

ALLOWED_MODEL_DRAFT_KEYS = frozenset(
    {
        "evidence_claims",
        "source_signal_drafts",
        "market_event_drafts",
        "model_runs",
        "reviewer_findings",
        "suppressed_outputs",
        "claim_id",
        "signal_id",
        "event_id",
        "statement",
        "summary",
        "ticker",
        "source_id",
        "capture_id",
        "evidence_capture_id",
        "citation_url",
        "event_type",
        "model_run_id",
        "task_role",
        "model_profile_id",
        "started_at",
        "completed_at",
        "status",
        "reason",
        "payload_key",
        "excerpt",
    }
)

FORBIDDEN_MODEL_DRAFT_KEY_TERMS = frozenset(
    {
        "score",
        "scoring",
        "weight",
        "constraint",
        "order",
        "execution",
        "broker",
        "route",
        "fill",
        "pnl",
    }
)

FORBIDDEN_MODEL_DRAFT_PHRASES = tuple(
    phrase.casefold()
    for phrase in (
        "place order",
        "submit order",
        "execute order",
        "route order",
        "live order",
        "buy shares",
        "sell shares",
        "buy 100 shares",
        "sell 100 shares",
        "portfolio weight",
        "target weight",
        "position weight",
        "risk limit",
        "hard constraint",
    )
)


@dataclass(frozen=True, slots=True)
class CaptureContext:
    ticker: str
    source_id: str
    capture_id: str
    url: str
    data_class: str
    extracted: ExtractedDocument | tuple[RssItem, ...]
    fetched_at: datetime

    def __post_init__(self) -> None:
        if self.data_class not in ALLOWED_CLOUD_DATA_CLASSES:
            raise ValueError(
                f"data_class {self.data_class!r} not eligible for deep research; "
                f"allowed: {sorted(ALLOWED_CLOUD_DATA_CLASSES)}"
            )


def validate_model_draft_payload(payload: Mapping[str, Any]) -> None:
    """Reject non-draft or deterministic fields from model-produced payloads."""

    _validate_model_draft_value(payload, path=())


def _validate_model_draft_value(value: Any, *, path: tuple[str, ...]) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            lowered_key = key_text.casefold()
            if any(term in lowered_key for term in FORBIDDEN_MODEL_DRAFT_KEY_TERMS):
                raise ValueError(
                    f"model draft payload contains forbidden key {'.'.join((*path, key_text))!r}"
                )
            if key_text not in ALLOWED_MODEL_DRAFT_KEYS:
                raise ValueError(
                    f"model draft payload contains unsupported key {'.'.join((*path, key_text))!r}"
                )
            _validate_model_draft_value(nested, path=(*path, key_text))
        return

    if isinstance(value, str):
        lowered_value = value.casefold()
        for phrase in FORBIDDEN_MODEL_DRAFT_PHRASES:
            if phrase in lowered_value:
                raise ValueError(
                    f"model draft payload contains forbidden phrase {phrase!r}"
                )
        return

    if isinstance(value, tuple | list):
        for index, nested in enumerate(value):
            _validate_model_draft_value(nested, path=(*path, str(index)))


@dataclass(frozen=True, slots=True)
class EvidenceClaimDraft:
    claim_id: str
    statement: str
    evidence_capture_id: str
    citation_url: str
    model_run_id: str | None


@dataclass(frozen=True, slots=True)
class SourceSignalDraft:
    signal_id: str
    ticker: str
    source_id: str
    summary: str
    evidence_capture_id: str
    model_run_id: str | None


@dataclass(frozen=True, slots=True)
class MarketEventDraft:
    event_id: str
    ticker: str
    event_type: str
    summary: str
    evidence_capture_id: str
    model_run_id: str | None


@dataclass(frozen=True, slots=True)
class ModelRunRecord:
    model_run_id: str
    task_role: str
    model_profile_id: str
    started_at: datetime
    completed_at: datetime | None
    status: str


@dataclass(frozen=True, slots=True)
class SuppressedModelOutput:
    reason: str
    payload_key: str
    excerpt: str


@dataclass(frozen=True, slots=True)
class ResearchExtractionResult:
    evidence_claims: tuple[EvidenceClaimDraft, ...] = ()
    source_signal_drafts: tuple[SourceSignalDraft, ...] = ()
    market_event_drafts: tuple[MarketEventDraft, ...] = ()
    model_runs: tuple[ModelRunRecord, ...] = ()
    reviewer_findings: tuple[str, ...] = ()
    suppressed_outputs: tuple[SuppressedModelOutput, ...] = ()


@runtime_checkable
class LLMClaimExtractor(Protocol):
    def extract_claims(
        self,
        *,
        capture: CaptureContext,
        model_router: object | None,
    ) -> ResearchExtractionResult: ...


@dataclass(frozen=True, slots=True)
class StubLLMClaimExtractor:
    """Deterministic-only path. Returns no claims, no model runs.

    Used as the v1 default. The worker calls this and proceeds to emit
    only the deterministic events from `event_extractor.extract_events`.
    """

    def extract_claims(
        self,
        *,
        capture: CaptureContext,
        model_router: object | None,
    ) -> ResearchExtractionResult:
        return ResearchExtractionResult()


__all__ = [
    "ALLOWED_CLOUD_DATA_CLASSES",
    "CaptureContext",
    "EvidenceClaimDraft",
    "LLMClaimExtractor",
    "MarketEventDraft",
    "ModelRunRecord",
    "ResearchExtractionResult",
    "SourceSignalDraft",
    "StubLLMClaimExtractor",
    "SuppressedModelOutput",
    "validate_model_draft_payload",
]
