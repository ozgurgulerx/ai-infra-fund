from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping, Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Body, FastAPI
from fastapi.responses import JSONResponse

from ai_infra_fund_api.repositories.evidence import EvidenceRepository
from ai_infra_fund_core.contracts.common import DataClass
from ai_infra_fund_core.contracts.evidence import EvidenceItem
from ai_infra_fund_core.evidence.chunking import EvidenceChunk, chunk_evidence_text
from ai_infra_fund_core.evidence.hashing import compute_content_hash
from ai_infra_fund_core.evidence.sources import normalize_evidence_source_metadata
from ai_infra_fund_core.runtime.config import RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]

ALLOWED_SOURCE_TYPES = frozenset({"manual_note", "manual_report", "manual_excerpt"})
ALLOWED_DATA_CLASSES = frozenset({DataClass.PUBLIC_EVIDENCE, DataClass.PRIVATE_RESEARCH})
ALLOWED_URI_SCHEMES = frozenset({"manual", "file", "http", "https"})
MAX_TEXT_CHARS = 200_000
CHUNK_SIZE_CHARS = 2_000
LOCAL_PENDING_EMBEDDING_MODEL = "local_pending"


class ManualEvidenceRepository(Protocol):
    def save_manual_evidence(
        self,
        item: EvidenceItem,
        chunks: tuple[EvidenceChunk, ...],
    ) -> EvidenceItem:
        ...


@dataclass(frozen=True, slots=True)
class ManualEvidenceSubmission:
    item: EvidenceItem
    chunks: tuple[EvidenceChunk, ...]
    local_only: bool


class EvidenceValidationError(ValueError):
    pass


class PostgresManualEvidenceRepository:
    def __init__(self, settings_provider: SettingsProvider) -> None:
        self._settings_provider = settings_provider

    def save_manual_evidence(
        self,
        item: EvidenceItem,
        chunks: tuple[EvidenceChunk, ...],
    ) -> EvidenceItem:
        import psycopg

        settings = self._settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            EvidenceRepository(connection).save_item_with_chunks(item, chunks)
        return item


def register_evidence_routes(
    app: FastAPI,
    *,
    evidence_repository: ManualEvidenceRepository | None,
    settings_provider: SettingsProvider,
) -> None:
    repository = evidence_repository or PostgresManualEvidenceRepository(settings_provider)
    router = APIRouter()

    @router.post("/internal/evidence/manual")
    def submit_manual_evidence(payload: dict[str, object] = Body(...)) -> JSONResponse:
        try:
            submission = prepare_manual_evidence(payload)
        except EvidenceValidationError as error:
            return _error_response("invalid_evidence", str(error), 422)

        try:
            saved_item = repository.save_manual_evidence(submission.item, submission.chunks)
        except Exception:
            return _error_response(
                "evidence_persistence_failed",
                "manual evidence could not be persisted",
                500,
            )

        return _data_response(
            {
                "evidence_id": saved_item.evidence_id,
                "content_hash": saved_item.content_hash,
                "data_class": saved_item.data_class.value,
                "chunk_count": len(submission.chunks),
                "local_only": submission.local_only,
            },
            status_code=201,
        )

    app.include_router(router)


def prepare_manual_evidence(payload: Mapping[str, object]) -> ManualEvidenceSubmission:
    errors: list[str] = []

    source_uri = _normalize_source_uri(payload.get("source_uri"), errors)
    source_type = _normalize_source_type(payload.get("source_type"), errors)
    license_label = _normalize_required_text(payload.get("license_label"), "license_label", errors)
    data_class = _normalize_data_class(payload.get("data_class"), errors)
    text = _normalize_text(payload.get("text"), errors)
    title = _normalize_optional_text(payload.get("title"), "title", errors)
    publisher = _normalize_optional_text(payload.get("publisher"), "publisher", errors)
    author = _normalize_optional_text(payload.get("author"), "author", errors)
    summary = _normalize_optional_text(payload.get("summary"), "summary", errors)
    storage_uri = _normalize_optional_text(payload.get("storage_uri"), "storage_uri", errors)
    published_at = _parse_optional_datetime(payload.get("published_at"), "published_at", errors)
    tickers = _normalize_string_tuple(payload.get("tickers"), "tickers", errors, uppercase=True)
    themes = _normalize_string_tuple(payload.get("themes"), "themes", errors, uppercase=False)

    if errors:
        raise EvidenceValidationError("; ".join(errors))

    source_metadata = normalize_evidence_source_metadata(
        source_uri=source_uri,
        license_label=license_label,
        data_class=data_class,
    )
    content_hash = _compute_evidence_content_hash(
        text,
        source_uri=source_uri,
        source_type=source_type,
        license_label=license_label,
        data_class=data_class,
    )
    evidence_id = f"evidence-{content_hash[:16]}"
    now = datetime.now(timezone.utc)
    item = EvidenceItem(
        evidence_id=evidence_id,
        source_uri=source_uri,
        source_type=source_type,
        title=title,
        publisher=publisher,
        author=author,
        published_at=published_at,
        ingested_at=now,
        content_hash=content_hash,
        license_label=license_label,
        data_class=data_class,
        tickers=tickers,
        themes=themes,
        summary=summary,
        storage_uri=storage_uri or f"local://manual/{content_hash}",
        created_at=now,
    )
    chunks = _chunk_text(evidence_id=evidence_id, text=text)
    return ManualEvidenceSubmission(
        item=item,
        chunks=chunks,
        local_only=source_metadata.local_only,
    )


def _normalize_source_uri(value: object, errors: list[str]) -> str:
    raw = _normalize_required_text(value, "source_uri", errors)
    if not raw:
        return ""

    parts = urlsplit(raw)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    if scheme not in ALLOWED_URI_SCHEMES:
        errors.append(f"source_uri scheme must be one of {sorted(ALLOWED_URI_SCHEMES)}")
        return raw
    if scheme in {"http", "https", "manual"} and not netloc:
        errors.append("source_uri must include a host or manual namespace")
        return raw
    if scheme == "file" and not parts.path.startswith("/"):
        errors.append("file source_uri must use an absolute path")
        return raw

    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    return urlunsplit((scheme, netloc, parts.path, query, ""))


def _normalize_source_type(value: object, errors: list[str]) -> str:
    source_type = _normalize_required_text(value, "source_type", errors).lower()
    if source_type and source_type not in ALLOWED_SOURCE_TYPES:
        errors.append(f"source_type must be one of {sorted(ALLOWED_SOURCE_TYPES)}")
    return source_type


def _normalize_data_class(value: object, errors: list[str]) -> DataClass:
    data_class_text = _normalize_required_text(value, "data_class", errors)
    allowed_values = [item.value for item in sorted(ALLOWED_DATA_CLASSES, key=lambda item: item.value)]
    try:
        data_class = DataClass(data_class_text)
    except ValueError:
        errors.append(f"data_class must be one of {allowed_values}")
        return DataClass.PRIVATE_RESEARCH
    if data_class not in ALLOWED_DATA_CLASSES:
        errors.append(f"data_class must be one of {allowed_values}")
    return data_class


def _normalize_text(value: object, errors: list[str]) -> str:
    text = _normalize_required_text(value, "text", errors)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n")).strip()
    if not text:
        errors.append("text is required")
    if len(text) > MAX_TEXT_CHARS:
        errors.append(f"text must be {MAX_TEXT_CHARS} characters or fewer")
    return text


def _normalize_required_text(value: object, field_name: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field_name} is required")
        return ""
    return value.strip()


def _normalize_optional_text(value: object, field_name: str, errors: list[str]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(f"{field_name} must be text")
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_string_tuple(
    value: object,
    field_name: str,
    errors: list[str],
    *,
    uppercase: bool,
) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str) or not isinstance(value, list):
        errors.append(f"{field_name} must be a list")
        return ()

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            errors.append(f"{field_name} entries must be text")
            continue
        item_text = item.strip()
        if item_text:
            normalized.append(item_text.upper() if uppercase else item_text)
    return tuple(normalized)


def _parse_optional_datetime(value: object, field_name: str, errors: list[str]) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field_name} must be an ISO-8601 datetime")
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field_name} must be an ISO-8601 datetime")
        return None
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        errors.append(f"{field_name} must include a timezone")
        return None
    return parsed


def _chunk_text(
    *,
    evidence_id: str,
    text: str,
) -> tuple[EvidenceChunk, ...]:
    return chunk_evidence_text(
        evidence_id=evidence_id,
        text=text,
        max_chars=CHUNK_SIZE_CHARS,
        embedding_model=LOCAL_PENDING_EMBEDDING_MODEL,
    )


def _compute_evidence_content_hash(
    text: str,
    *,
    source_uri: str,
    source_type: str,
    license_label: str,
    data_class: DataClass,
) -> str:
    metadata = {
        "data_class": data_class,
        "license_label": license_label,
        "source_type": source_type,
        "source_uri": source_uri,
    }
    return compute_content_hash(text, metadata=metadata)


def _data_response(payload: dict[str, object], status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"data": payload})


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )
