from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import math
from typing import Iterable, Protocol, Sequence

from ai_infra_fund_core.contracts.common import DataClass, coerce_enum, require_text

from .chunking import EvidenceChunk


LOCAL_ENDPOINT_TYPE = "local"


class EmbeddingPolicyError(ValueError):
    """Raised when an embedding request would violate local data policy."""


@dataclass(frozen=True, slots=True)
class EmbeddingContext:
    embedding_model: str
    provider: str
    endpoint_type: str
    dimension: int
    data_classes: tuple[DataClass, ...]

    @classmethod
    def from_model_profile(
        cls,
        profile: object,
        *,
        dimension: int,
        data_classes: Iterable[DataClass | str],
    ) -> "EmbeddingContext":
        return cls(
            embedding_model=require_text(getattr(profile, "model_id", None), "model_id"),
            provider=require_text(getattr(profile, "provider", None), "provider"),
            endpoint_type=require_text(getattr(profile, "endpoint_type", None), "endpoint_type"),
            dimension=dimension,
            data_classes=tuple(data_classes),
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "embedding_model", require_text(self.embedding_model, "embedding_model"))
        object.__setattr__(self, "provider", require_text(self.provider, "provider"))
        endpoint_type = require_text(self.endpoint_type, "endpoint_type")
        object.__setattr__(self, "endpoint_type", endpoint_type)

        if isinstance(self.dimension, bool) or not isinstance(self.dimension, int):
            raise ValueError("embedding dimension must be an integer")
        if self.dimension <= 0:
            raise ValueError("embedding dimension must be positive")

        data_classes = tuple(coerce_enum(item, DataClass, "data_classes") for item in self.data_classes)
        if not data_classes:
            raise ValueError("data_classes must not be empty")
        if DataClass.SECRETS in data_classes:
            raise EmbeddingPolicyError("embeddings cannot process secrets")
        if endpoint_type != LOCAL_ENDPOINT_TYPE:
            if DataClass.PRIVATE_RESEARCH in data_classes:
                raise EmbeddingPolicyError("private_research embeddings must use a local profile")
            raise EmbeddingPolicyError("chunk embeddings must use a local profile")
        object.__setattr__(self, "data_classes", data_classes)


class EmbeddingProvider(Protocol):
    def embed_texts(
        self,
        texts: Sequence[str],
        *,
        context: EmbeddingContext,
    ) -> tuple[tuple[float, ...], ...]:
        ...


class DeterministicEmbeddingProvider:
    def embed_texts(
        self,
        texts: Sequence[str],
        *,
        context: EmbeddingContext,
    ) -> tuple[tuple[float, ...], ...]:
        normalized_texts = tuple(_require_text_item(text) for text in texts)
        return tuple(_deterministic_vector(text, context=context) for text in normalized_texts)


def embed_evidence_chunks(
    chunks: Iterable[EvidenceChunk],
    *,
    provider: EmbeddingProvider,
    context: EmbeddingContext,
) -> tuple[EvidenceChunk, ...]:
    chunk_records = tuple(chunks)
    texts = tuple(chunk.chunk_text for chunk in chunk_records)
    vectors = provider.embed_texts(texts, context=context)
    if len(vectors) != len(chunk_records):
        raise ValueError("embedding provider returned the wrong number of vectors")

    validated_vectors = tuple(
        _validate_vector(vector, expected_dimension=context.dimension)
        for vector in vectors
    )
    return tuple(
        replace(
            chunk,
            embedding_model=context.embedding_model,
            embedding=vector,
        )
        for chunk, vector in zip(chunk_records, validated_vectors)
    )


def _require_text_item(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("embedding text must be text")
    return require_text(value, "embedding text")


def _deterministic_vector(text: str, *, context: EmbeddingContext) -> tuple[float, ...]:
    seed = f"{context.embedding_model}\0{context.provider}\0{text}".encode("utf-8")
    values: list[float] = []
    counter = 0
    while len(values) < context.dimension:
        digest = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        for offset in range(0, len(digest), 4):
            if len(values) == context.dimension:
                break
            integer = int.from_bytes(digest[offset : offset + 4], "big")
            values.append(round(integer / 0xFFFFFFFF, 8))
        counter += 1
    return tuple(values)


def _validate_vector(vector: Iterable[object], *, expected_dimension: int) -> tuple[float, ...]:
    if isinstance(vector, str):
        raise ValueError("embedding vector must be an iterable of finite numbers")

    try:
        raw_values = tuple(vector)
    except TypeError as exc:
        raise ValueError("embedding vector must be an iterable of finite numbers") from exc

    values: list[float] = []
    for item in raw_values:
        if isinstance(item, bool):
            raise ValueError("embedding vector entries must be finite numbers")
        try:
            value = float(item)
        except (TypeError, ValueError) as exc:
            raise ValueError("embedding vector entries must be finite numbers") from exc
        if not math.isfinite(value):
            raise ValueError("embedding vector entries must be finite numbers")
        values.append(value)

    if len(values) != expected_dimension:
        raise ValueError(
            f"embedding dimension mismatch: expected {expected_dimension}, got {len(values)}"
        )
    return tuple(values)


__all__ = [
    "DeterministicEmbeddingProvider",
    "EmbeddingContext",
    "EmbeddingPolicyError",
    "EmbeddingProvider",
    "embed_evidence_chunks",
]
