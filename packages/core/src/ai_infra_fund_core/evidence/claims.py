from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Any

from ai_infra_fund_core.contracts.common import (
    DataClass,
    ModelRunStatus,
    coerce_enum,
    normalize_tuple,
    require_aware_datetime,
    require_decimal_range,
    require_non_empty_tuple,
    require_text,
    stable_hash_payload,
)
from ai_infra_fund_core.contracts.evidence import EvidenceClaim, EvidenceItem
from ai_infra_fund_core.contracts.model_runs import ModelRun

from .chunking import EvidenceChunk


LOCAL_ENDPOINT_TYPE = "local"
CLAIM_CONFIDENCE_LOCAL_STUB = Decimal("0.60")


@dataclass(frozen=True, slots=True)
class ClaimExtractionModelContext:
    model_id: str
    deployment: str
    provider: str
    endpoint_type: str
    prompt_version: str
    task_role: str
    allowed_data_classes: tuple[DataClass, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", require_text(self.model_id, "model_id"))
        object.__setattr__(self, "deployment", require_text(self.deployment, "deployment"))
        object.__setattr__(self, "provider", require_text(self.provider, "provider"))
        object.__setattr__(self, "endpoint_type", require_text(self.endpoint_type, "endpoint_type"))
        object.__setattr__(self, "prompt_version", require_text(self.prompt_version, "prompt_version"))
        object.__setattr__(self, "task_role", require_text(self.task_role, "task_role"))
        object.__setattr__(
            self,
            "allowed_data_classes",
            require_non_empty_tuple(
                tuple(
                    coerce_enum(data_class, DataClass, "allowed_data_classes")
                    for data_class in normalize_tuple(self.allowed_data_classes, "allowed_data_classes")
                ),
                "allowed_data_classes",
            ),
        )


@dataclass(frozen=True, slots=True)
class ClaimExtractionChunkInput:
    chunk_id: str
    span_ref: str
    text: str


@dataclass(frozen=True, slots=True)
class ClaimExtractionPrompt:
    task_role: str
    prompt_version: str
    evidence_id: str
    source_uri: str
    content_hash: str
    data_class: DataClass
    tickers: tuple[str, ...]
    themes: tuple[str, ...]
    chunks: tuple[ClaimExtractionChunkInput, ...]


@dataclass(frozen=True, slots=True)
class ClaimExtractionResult:
    claims: tuple[EvidenceClaim, ...]
    model_runs: tuple[ModelRun, ...]


ModelResponseProvider = Callable[[ClaimExtractionPrompt], Mapping[str, Any]]
ModelRunRecorder = Callable[[ModelRun], None]


def extract_claims_locally(
    *,
    evidence_item: EvidenceItem,
    chunks: Iterable[EvidenceChunk],
    created_at: datetime | None = None,
) -> tuple[EvidenceClaim, ...]:
    created = _resolve_created_at(created_at)
    chunk_records = tuple(chunks)
    claims: list[EvidenceClaim] = []

    for chunk in chunk_records:
        subject = _first_matching_subject(evidence_item, chunk.chunk_text)
        if subject is None:
            continue

        claim_type = _infer_claim_type(chunk.chunk_text)
        claims.append(
            _build_claim(
                evidence_item=evidence_item,
                chunk=chunk,
                ticker_or_theme=subject,
                claim_type=claim_type,
                direction=_infer_direction(claim_type, chunk.chunk_text),
                magnitude=None,
                time_horizon=_infer_time_horizon(chunk.chunk_text),
                confidence=CLAIM_CONFIDENCE_LOCAL_STUB,
                span_ref=chunk.span_ref,
                model_run_id=None,
                created_at=created,
            )
        )

    return tuple(claims)


def extract_claims_with_model(
    *,
    evidence_item: EvidenceItem,
    chunks: Iterable[EvidenceChunk],
    model_context: ClaimExtractionModelContext,
    model_response_provider: ModelResponseProvider,
    model_run_recorder: ModelRunRecorder | None = None,
    created_at: datetime | None = None,
) -> ClaimExtractionResult:
    created = _resolve_created_at(created_at)
    chunk_records = tuple(chunks)
    data_classes = (coerce_enum(evidence_item.data_class, DataClass, "data_class"),)
    input_hash = _input_hash(
        evidence_item=evidence_item,
        chunks=chunk_records,
        model_context=model_context,
    )

    denied_reason = _denied_reason(model_context=model_context, data_classes=data_classes)
    if denied_reason is not None:
        run = _model_run(
            model_context=model_context,
            status=ModelRunStatus.DENIED,
            input_hash=input_hash,
            output_hash=None,
            schema_valid=False,
            data_classes=data_classes,
            error_summary=denied_reason,
            created_at=created,
        )
        _record_model_run(run, model_run_recorder)
        return ClaimExtractionResult(claims=(), model_runs=(run,))

    prompt = _build_prompt(
        evidence_item=evidence_item,
        chunks=chunk_records,
        model_context=model_context,
    )

    try:
        response = model_response_provider(prompt)
        output_hash = _output_hash(response)
        model_run_id = _model_run_id(
            model_context=model_context,
            status=ModelRunStatus.SUCCESS,
            input_hash=input_hash,
            output_hash=output_hash,
            created_at=created,
        )
        claims = _claims_from_model_response(
            response=response,
            evidence_item=evidence_item,
            chunks=chunk_records,
            model_run_id=model_run_id,
            created_at=created,
        )
        run = _model_run(
            model_context=model_context,
            status=ModelRunStatus.SUCCESS,
            input_hash=input_hash,
            output_hash=output_hash,
            schema_valid=True,
            data_classes=data_classes,
            error_summary=None,
            created_at=created,
            model_run_id=model_run_id,
        )
        _record_model_run(run, model_run_recorder)
        return ClaimExtractionResult(claims=claims, model_runs=(run,))
    except Exception as exc:
        run = _model_run(
            model_context=model_context,
            status=ModelRunStatus.FAILURE,
            input_hash=input_hash,
            output_hash=None,
            schema_valid=False,
            data_classes=data_classes,
            error_summary=str(exc),
            created_at=created,
        )
        _record_model_run(run, model_run_recorder)
        return ClaimExtractionResult(claims=(), model_runs=(run,))


def _resolve_created_at(created_at: datetime | None) -> datetime:
    value = created_at or datetime.now(timezone.utc)
    return require_aware_datetime(value, "created_at")


def _first_matching_subject(evidence_item: EvidenceItem, text: str) -> str | None:
    upper_text = text.upper()
    for ticker in evidence_item.tickers:
        ticker_text = require_text(ticker, "ticker")
        if ticker_text.upper() in upper_text:
            return ticker_text.upper()

    lower_text = text.lower()
    for theme in evidence_item.themes:
        theme_text = require_text(theme, "theme")
        normalized_theme = theme_text.replace("_", " ").lower()
        if normalized_theme in lower_text or theme_text.lower() in lower_text:
            return theme_text

    return None


def _infer_claim_type(text: str) -> str:
    lower_text = text.lower()
    if "demand" in lower_text and _contains_any(lower_text, ("grew", "growth", "strong", "expanded", "increased")):
        return "demand_growth"
    if "supply" in lower_text and _contains_any(lower_text, ("constraint", "constrained", "shortage", "tight", "lead time")):
        return "supply_constraint"
    if _contains_any(lower_text, ("capex", "capital expenditure", "spending")):
        return "capex_signal"
    if _contains_any(lower_text, ("risk", "competition", "margin pressure", "delay")):
        return "risk"
    return "evidence_statement"


def _infer_direction(claim_type: str, text: str) -> str | None:
    lower_text = text.lower()
    if claim_type in {"demand_growth", "capex_signal"}:
        return "positive"
    if claim_type in {"supply_constraint", "risk"}:
        return "negative"
    if _contains_any(lower_text, ("grew", "growth", "expanded", "increased", "strong")):
        return "positive"
    if _contains_any(lower_text, ("declined", "decreased", "weak", "risk", "delay")):
        return "negative"
    return None


def _infer_time_horizon(text: str) -> str:
    match = re.search(r"\b20\d{2}\b", text)
    if match is not None:
        return match.group(0)
    lower_text = text.lower()
    if _contains_any(lower_text, ("next quarter", "near term", "near-term", "this quarter")):
        return "near_term"
    if _contains_any(lower_text, ("long term", "long-term", "multi-year")):
        return "long_term"
    return "unspecified"


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _build_claim(
    *,
    evidence_item: EvidenceItem,
    chunk: EvidenceChunk,
    ticker_or_theme: str,
    claim_type: str,
    direction: str | None,
    magnitude: Decimal | None,
    time_horizon: str,
    confidence: Decimal,
    span_ref: str,
    model_run_id: str | None,
    created_at: datetime,
) -> EvidenceClaim:
    linked_span_ref = _source_linked_span_ref(
        evidence_item=evidence_item,
        chunk=chunk,
        span_ref=span_ref,
    )
    claim_id = _claim_id(
        evidence_id=evidence_item.evidence_id,
        chunk_id=chunk.chunk_id,
        ticker_or_theme=ticker_or_theme,
        claim_type=claim_type,
        time_horizon=time_horizon,
        quote_or_span_ref=linked_span_ref,
        model_run_id=model_run_id,
    )
    return EvidenceClaim(
        claim_id=claim_id,
        evidence_id=evidence_item.evidence_id,
        chunk_id=chunk.chunk_id,
        ticker_or_theme=ticker_or_theme,
        claim_type=claim_type,
        direction=direction,
        magnitude=magnitude,
        time_horizon=time_horizon,
        confidence=confidence,
        quote_or_span_ref=linked_span_ref,
        extracted_by_model_run_id=model_run_id,
        validated_at=None,
        created_at=created_at,
    )


def _source_linked_span_ref(
    *,
    evidence_item: EvidenceItem,
    chunk: EvidenceChunk,
    span_ref: str,
) -> str:
    return "|".join(
        (
            f"chunk:{require_text(chunk.chunk_id, 'chunk_id')}",
            f"span:{require_text(span_ref, 'span_ref')}",
            f"source:{require_text(evidence_item.source_uri, 'source_uri')}",
            f"hash:{require_text(evidence_item.content_hash, 'content_hash')}",
        )
    )


def _claim_id(
    *,
    evidence_id: str,
    chunk_id: str,
    ticker_or_theme: str,
    claim_type: str,
    time_horizon: str,
    quote_or_span_ref: str,
    model_run_id: str | None,
) -> str:
    digest = stable_hash_payload(
        {
            "evidence_id": evidence_id,
            "chunk_id": chunk_id,
            "ticker_or_theme": ticker_or_theme,
            "claim_type": claim_type,
            "time_horizon": time_horizon,
            "quote_or_span_ref": quote_or_span_ref,
            "model_run_id": model_run_id,
        }
    )
    return f"claim:{digest[:16]}"


def _input_hash(
    *,
    evidence_item: EvidenceItem,
    chunks: tuple[EvidenceChunk, ...],
    model_context: ClaimExtractionModelContext,
) -> str:
    return stable_hash_payload(
        {
            "task_role": model_context.task_role,
            "prompt_version": model_context.prompt_version,
            "evidence_id": evidence_item.evidence_id,
            "source_uri": evidence_item.source_uri,
            "content_hash": evidence_item.content_hash,
            "data_class": evidence_item.data_class,
            "tickers": evidence_item.tickers,
            "themes": evidence_item.themes,
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "span_ref": chunk.span_ref,
                    "content_hash": chunk.content_hash,
                }
                for chunk in chunks
            ],
        }
    )


def _output_hash(response: Mapping[str, Any]) -> str:
    if not isinstance(response, Mapping):
        raise ValueError("model response must be a mapping")
    return stable_hash_payload({"model_response": dict(response)})


def _denied_reason(
    *,
    model_context: ClaimExtractionModelContext,
    data_classes: tuple[DataClass, ...],
) -> str | None:
    if DataClass.SECRETS in data_classes:
        return "data-class policy denied secrets route"
    if DataClass.PRIVATE_RESEARCH in data_classes and model_context.endpoint_type != LOCAL_ENDPOINT_TYPE:
        return "data-class policy denied cloud route"
    if any(data_class not in model_context.allowed_data_classes for data_class in data_classes):
        return "data-class policy denied route"
    return None


def _build_prompt(
    *,
    evidence_item: EvidenceItem,
    chunks: tuple[EvidenceChunk, ...],
    model_context: ClaimExtractionModelContext,
) -> ClaimExtractionPrompt:
    return ClaimExtractionPrompt(
        task_role=model_context.task_role,
        prompt_version=model_context.prompt_version,
        evidence_id=evidence_item.evidence_id,
        source_uri=evidence_item.source_uri,
        content_hash=evidence_item.content_hash,
        data_class=evidence_item.data_class,
        tickers=evidence_item.tickers,
        themes=evidence_item.themes,
        chunks=tuple(
            ClaimExtractionChunkInput(
                chunk_id=chunk.chunk_id,
                span_ref=chunk.span_ref,
                text=chunk.chunk_text,
            )
            for chunk in chunks
        ),
    )


def _claims_from_model_response(
    *,
    response: Mapping[str, Any],
    evidence_item: EvidenceItem,
    chunks: tuple[EvidenceChunk, ...],
    model_run_id: str,
    created_at: datetime,
) -> tuple[EvidenceClaim, ...]:
    raw_claims = response.get("claims")
    if not isinstance(raw_claims, list):
        raise ValueError("model response requires claims list")

    chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    claims: list[EvidenceClaim] = []
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, Mapping):
            raise ValueError("each model claim must be a mapping")
        chunk_id = require_text(str(raw_claim.get("chunk_id", "")), "claim.chunk_id")
        try:
            chunk = chunks_by_id[chunk_id]
        except KeyError as exc:
            raise ValueError(f"unknown claim chunk_id: {chunk_id}") from exc

        confidence = require_decimal_range(
            Decimal(str(raw_claim.get("confidence"))),
            "claim.confidence",
            Decimal("0"),
            Decimal("1"),
        )
        magnitude = _optional_decimal(raw_claim.get("magnitude"))
        direction = _optional_text(raw_claim.get("direction"))
        span_ref = _optional_text(raw_claim.get("quote_or_span_ref")) or chunk.span_ref
        claims.append(
            _build_claim(
                evidence_item=evidence_item,
                chunk=chunk,
                ticker_or_theme=require_text(str(raw_claim.get("ticker_or_theme", "")), "claim.ticker_or_theme"),
                claim_type=require_text(str(raw_claim.get("claim_type", "")), "claim.claim_type"),
                direction=direction,
                magnitude=magnitude,
                time_horizon=require_text(str(raw_claim.get("time_horizon", "")), "claim.time_horizon"),
                confidence=confidence,
                span_ref=span_ref,
                model_run_id=model_run_id,
                created_at=created_at,
            )
        )

    return tuple(claims)


def _optional_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _model_run(
    *,
    model_context: ClaimExtractionModelContext,
    status: ModelRunStatus,
    input_hash: str,
    output_hash: str | None,
    schema_valid: bool,
    data_classes: tuple[DataClass, ...],
    error_summary: str | None,
    created_at: datetime,
    model_run_id: str | None = None,
) -> ModelRun:
    return ModelRun(
        model_run_id=model_run_id
        or _model_run_id(
            model_context=model_context,
            status=status,
            input_hash=input_hash,
            output_hash=output_hash,
            created_at=created_at,
        ),
        task_role=model_context.task_role,
        model_id=model_context.model_id,
        deployment=model_context.deployment,
        provider=model_context.provider,
        prompt_version=model_context.prompt_version,
        input_hash=input_hash,
        output_hash=output_hash,
        latency_ms=None,
        token_estimate_input=None,
        token_estimate_output=None,
        schema_valid=schema_valid,
        retry_count=0,
        data_classes=data_classes,
        status=status,
        error_summary=error_summary,
        created_at=created_at,
    )


def _model_run_id(
    *,
    model_context: ClaimExtractionModelContext,
    status: ModelRunStatus,
    input_hash: str,
    output_hash: str | None,
    created_at: datetime,
) -> str:
    digest = stable_hash_payload(
        {
            "task_role": model_context.task_role,
            "model_id": model_context.model_id,
            "deployment": model_context.deployment,
            "provider": model_context.provider,
            "prompt_version": model_context.prompt_version,
            "status": status,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "created_at": created_at,
        }
    )
    return f"model-run:{digest[:16]}"


def _record_model_run(run: ModelRun, recorder: ModelRunRecorder | None) -> None:
    if recorder is not None:
        recorder(run)


__all__ = [
    "ClaimExtractionChunkInput",
    "ClaimExtractionModelContext",
    "ClaimExtractionPrompt",
    "ClaimExtractionResult",
    "ModelRunRecorder",
    "extract_claims_locally",
    "extract_claims_with_model",
]
