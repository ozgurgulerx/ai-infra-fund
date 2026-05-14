from __future__ import annotations

from dataclasses import dataclass

from ai_infra_fund_core.contracts.common import require_text

from .hashing import compute_content_hash


@dataclass(frozen=True, slots=True)
class EvidenceChunk:
    chunk_id: str
    evidence_id: str
    chunk_index: int
    chunk_text: str
    span_ref: str
    content_hash: str
    embedding_model: str
    embedding: tuple[float, ...] | None


def chunk_evidence_text(
    *,
    evidence_id: str,
    text: str,
    max_chars: int,
    embedding_model: str,
    overlap_chars: int = 0,
) -> tuple[EvidenceChunk, ...]:
    evidence_id = require_text(evidence_id, "evidence_id")
    embedding_model = require_text(embedding_model, "embedding_model")
    normalized_text = _normalize_text(require_text(text, "text"))
    _validate_chunk_sizes(max_chars=max_chars, overlap_chars=overlap_chars)

    chunks: list[EvidenceChunk] = []
    start = 0
    while start < len(normalized_text):
        end = min(start + max_chars, len(normalized_text))
        chunk_text = normalized_text[start:end]
        span_ref = f"char:{start}-{end}"
        content_hash = compute_content_hash(
            chunk_text,
            metadata={
                "evidence_id": evidence_id,
                "chunk_index": len(chunks),
                "span_ref": span_ref,
            },
        )
        chunks.append(
            EvidenceChunk(
                chunk_id=f"chunk:{content_hash}",
                evidence_id=evidence_id,
                chunk_index=len(chunks),
                chunk_text=chunk_text,
                span_ref=span_ref,
                content_hash=content_hash,
                embedding_model=embedding_model,
                embedding=None,
            )
        )
        if end == len(normalized_text):
            break
        start = end - overlap_chars

    return tuple(chunks)


def _validate_chunk_sizes(*, max_chars: int, overlap_chars: int) -> None:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap_chars < 0:
        raise ValueError("overlap_chars must be non-negative")
    if overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be smaller than max_chars")


def _normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


__all__ = ["EvidenceChunk", "chunk_evidence_text"]
