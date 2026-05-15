"""Deep-research extension point.

Defines the `LLMClaimExtractor` Protocol that a future LLM-driven claim
extractor must implement. v1 ships only the `StubLLMClaimExtractor` —
a no-op that returns no claims and no model_runs. This keeps the worker
pipeline structurally complete and the upgrade path obvious.

When a real extractor is wired (Phase 10b):
  - It MUST check ``capture.data_class`` is in the cloud-allowed set
    before any model call.
  - Each call MUST emit a ``ModelRun`` record (so audit lineage is intact).
  - It MUST NOT produce scores, weights, or any deterministic output —
    only `EvidenceClaim` records with citations. Deterministic code owns
    scoring; this is enforced by ``AGENTS.md`` and ``docs/specs/0013``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from .extraction import ExtractedDocument, RssItem


ALLOWED_CLOUD_DATA_CLASSES = frozenset(
    {"public_market_data", "public_evidence", "derived_analytics"}
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


@dataclass(frozen=True, slots=True)
class ClaimRecord:
    claim_id: str
    statement: str
    evidence_capture_id: str
    confidence: float
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
class ResearchExtractionResult:
    claims: tuple[ClaimRecord, ...]
    model_runs: tuple[ModelRunRecord, ...]


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
        return ResearchExtractionResult(claims=(), model_runs=())


__all__ = [
    "ALLOWED_CLOUD_DATA_CLASSES",
    "CaptureContext",
    "ClaimRecord",
    "LLMClaimExtractor",
    "ModelRunRecord",
    "ResearchExtractionResult",
    "StubLLMClaimExtractor",
]
