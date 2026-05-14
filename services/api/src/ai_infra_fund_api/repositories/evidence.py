from __future__ import annotations

from datetime import datetime
from typing import Iterable, Protocol, TypeVar

from ai_infra_fund_core.contracts.common import (
    DataClass,
    coerce_enum,
    require_aware_datetime,
    require_content_hash,
    require_text,
)
from ai_infra_fund_core.evidence.chunking import EvidenceChunk


class Cursor(Protocol):
    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...

    def commit(self) -> None:
        ...


EvidenceItemT = TypeVar("EvidenceItemT")
EvidenceChunkT = TypeVar("EvidenceChunkT")


INSERT_EVIDENCE_ITEM_SQL = """
INSERT INTO evidence.evidence_items (
    evidence_id,
    source_uri,
    source_type,
    title,
    publisher,
    author,
    published_at,
    ingested_at,
    content_hash,
    license_label,
    data_class,
    tickers,
    themes,
    summary,
    storage_uri,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (content_hash) DO NOTHING;
"""


INSERT_EVIDENCE_CHUNK_SQL = """
INSERT INTO evidence.evidence_chunks (
    chunk_id,
    evidence_id,
    chunk_index,
    chunk_text,
    span_ref,
    content_hash,
    embedding_model,
    embedding
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (content_hash) DO NOTHING;
"""


class EvidenceRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def save_item(self, item: EvidenceItemT) -> EvidenceItemT:
        with self._connection.cursor() as cursor:
            cursor.execute(INSERT_EVIDENCE_ITEM_SQL, _item_params(item))
        self._connection.commit()
        return item

    def save_chunk(self, chunk: EvidenceChunkT) -> EvidenceChunkT:
        with self._connection.cursor() as cursor:
            cursor.execute(INSERT_EVIDENCE_CHUNK_SQL, _chunk_params(chunk))
        self._connection.commit()
        return chunk

    def save_item_with_chunks(
        self,
        item: EvidenceItemT,
        chunks: Iterable[EvidenceChunkT],
    ) -> tuple[EvidenceItemT, tuple[EvidenceChunkT, ...]]:
        chunk_records = tuple(chunks)
        item_params = _item_params(item)
        chunk_params = tuple(_chunk_params(chunk) for chunk in chunk_records)
        item_id = item_params[0]
        for params in chunk_params:
            if params[1] != item_id:
                raise ValueError("chunk evidence_id must match item evidence_id")

        with self._connection.cursor() as cursor:
            cursor.execute(INSERT_EVIDENCE_ITEM_SQL, item_params)
            for params in chunk_params:
                cursor.execute(INSERT_EVIDENCE_CHUNK_SQL, params)
        self._connection.commit()
        return item, chunk_records


def _item_params(item: object) -> tuple[object, ...]:
    evidence_id = _required_text_attr(item, "evidence_id")
    source_uri = _required_text_attr(item, "source_uri")
    source_type = _required_text_attr(item, "source_type")
    published_at = getattr(item, "published_at", None)
    ingested_at = _required_aware_datetime_attr(item, "ingested_at")
    content_hash = require_content_hash(getattr(item, "content_hash", None))
    license_label = _required_text_attr(item, "license_label")
    data_class = coerce_enum(getattr(item, "data_class", None), DataClass, "data_class")
    storage_uri = _optional_text_attr(item, "storage_uri")
    if _requires_storage_uri(source_uri, data_class):
        storage_uri = require_text(storage_uri, "storage_uri")
    created_at = _required_aware_datetime_attr(item, "created_at")

    if published_at is not None:
        require_aware_datetime(published_at, "published_at")

    return (
        evidence_id,
        source_uri,
        source_type,
        getattr(item, "title", None),
        getattr(item, "publisher", None),
        getattr(item, "author", None),
        published_at,
        ingested_at,
        content_hash,
        license_label,
        data_class.value,
        _text_array(getattr(item, "tickers", ()), "tickers"),
        _text_array(getattr(item, "themes", ()), "themes"),
        getattr(item, "summary", None),
        storage_uri,
        created_at,
    )


def _chunk_params(chunk: object) -> tuple[object, ...]:
    embedding = getattr(chunk, "embedding", None)
    if embedding is not None:
        raise ValueError("embedding must be None until the embedding persistence pipeline exists")

    chunk_index = getattr(chunk, "chunk_index", None)
    if not isinstance(chunk_index, int):
        raise ValueError("chunk_index is required")
    if chunk_index < 0:
        raise ValueError("chunk_index must be non-negative")

    return (
        _required_text_attr(chunk, "chunk_id"),
        _required_text_attr(chunk, "evidence_id"),
        chunk_index,
        _required_text_attr(chunk, "chunk_text"),
        _required_text_attr(chunk, "span_ref"),
        require_content_hash(getattr(chunk, "content_hash", None)),
        _required_text_attr(chunk, "embedding_model"),
        None,
    )


def _required_text_attr(record: object, field_name: str) -> str:
    return require_text(getattr(record, field_name, None), field_name)


def _required_aware_datetime_attr(record: object, field_name: str) -> datetime:
    value = getattr(record, field_name, None)
    if value is None:
        raise ValueError(f"{field_name} is required")
    return require_aware_datetime(value, field_name)


def _optional_text_attr(record: object, field_name: str) -> str | None:
    value = getattr(record, field_name, None)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _text_array(values: object, field_name: str) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        raise ValueError(f"{field_name} must be an iterable, not a string")
    return [require_text(str(value), field_name) for value in values]


def _requires_storage_uri(source_uri: str, data_class: DataClass) -> bool:
    return source_uri.startswith("file://") or data_class is DataClass.PRIVATE_RESEARCH
