from __future__ import annotations

import math
from typing import Iterable, Protocol, TypeVar

from ai_infra_fund_core.contracts.common import require_text


class Cursor(Protocol):
    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...

    def commit(self) -> None:
        ...


EvidenceChunkT = TypeVar("EvidenceChunkT")


UPDATE_CHUNK_EMBEDDING_SQL = """
UPDATE evidence.evidence_chunks
SET
    embedding_model = %s,
    embedding = %s::vector
WHERE chunk_id = %s;
"""


class EvidenceEmbeddingRepository:
    def __init__(self, connection: Connection, *, vector_dimension: int) -> None:
        if isinstance(vector_dimension, bool) or not isinstance(vector_dimension, int):
            raise ValueError("vector_dimension must be an integer")
        if vector_dimension <= 0:
            raise ValueError("vector_dimension must be positive")
        self._connection = connection
        self._vector_dimension = vector_dimension

    def save_chunk_embedding(self, chunk: EvidenceChunkT) -> EvidenceChunkT:
        saved = self.save_chunk_embeddings((chunk,))
        return saved[0]

    def save_chunk_embeddings(
        self,
        chunks: Iterable[EvidenceChunkT],
    ) -> tuple[EvidenceChunkT, ...]:
        chunk_records = tuple(chunks)
        params = tuple(
            _chunk_embedding_params(chunk, expected_dimension=self._vector_dimension)
            for chunk in chunk_records
        )
        if not params:
            return chunk_records

        with self._connection.cursor() as cursor:
            for item in params:
                cursor.execute(UPDATE_CHUNK_EMBEDDING_SQL, item)
        self._connection.commit()
        return chunk_records


def _chunk_embedding_params(chunk: object, *, expected_dimension: int) -> tuple[object, ...]:
    embedding_model = _required_text_attr(chunk, "embedding_model")
    chunk_id = _required_text_attr(chunk, "chunk_id")
    embedding = _embedding_vector(
        getattr(chunk, "embedding", None),
        expected_dimension=expected_dimension,
    )
    return (
        embedding_model,
        _pgvector_literal(embedding),
        chunk_id,
    )


def _required_text_attr(record: object, field_name: str) -> str:
    return require_text(getattr(record, field_name, None), field_name)


def _embedding_vector(value: object, *, expected_dimension: int) -> tuple[float, ...]:
    if value is None:
        raise ValueError("embedding is required")
    if isinstance(value, str):
        raise ValueError("embedding must be an iterable of finite numbers")

    try:
        raw_values = tuple(value)  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError("embedding must be an iterable of finite numbers") from exc

    values: list[float] = []
    for item in raw_values:
        if isinstance(item, bool):
            raise ValueError("embedding entries must be finite numbers")
        try:
            number = float(item)
        except (TypeError, ValueError) as exc:
            raise ValueError("embedding entries must be finite numbers") from exc
        if not math.isfinite(number):
            raise ValueError("embedding entries must be finite numbers")
        values.append(number)

    if len(values) != expected_dimension:
        raise ValueError(
            f"embedding dimension mismatch: expected {expected_dimension}, got {len(values)}"
        )
    return tuple(values)


def _pgvector_literal(embedding: tuple[float, ...]) -> str:
    return f"[{','.join(str(value) for value in embedding)}]"


__all__ = ["EvidenceEmbeddingRepository"]
