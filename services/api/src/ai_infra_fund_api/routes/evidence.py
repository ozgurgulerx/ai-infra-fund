from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, Protocol
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Body, FastAPI
from fastapi.responses import JSONResponse

from ai_infra_fund_api.repositories.evidence import EvidenceRepository
from ai_infra_fund_core.contracts.common import DataClass
from ai_infra_fund_core.contracts.evidence import EvidenceClaim, EvidenceItem
from ai_infra_fund_core.evidence.chunking import EvidenceChunk, chunk_evidence_text
from ai_infra_fund_core.evidence.hashing import compute_content_hash
from ai_infra_fund_core.evidence.sources import normalize_evidence_source_metadata
from ai_infra_fund_core.runtime.config import RuntimeConfigError, RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]

ALLOWED_SOURCE_TYPES = frozenset({"manual_note", "manual_report", "manual_excerpt"})
ALLOWED_DATA_CLASSES = frozenset({DataClass.PUBLIC_EVIDENCE, DataClass.PRIVATE_RESEARCH})
ALLOWED_URI_SCHEMES = frozenset({"manual", "file", "http", "https"})
ALLOWED_FILE_SUFFIXES = frozenset({".csv", ".json", ".md", ".tsv", ".txt"})
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

    def save_evidence_with_claims(
        self,
        item: EvidenceItem,
        chunks: tuple[EvidenceChunk, ...],
        claims: tuple[EvidenceClaim, ...],
    ) -> EvidenceItem:
        ...


@dataclass(frozen=True, slots=True)
class ManualEvidenceSubmission:
    item: EvidenceItem
    chunks: tuple[EvidenceChunk, ...]
    claims: tuple[EvidenceClaim, ...]
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

    def save_evidence_with_claims(
        self,
        item: EvidenceItem,
        chunks: tuple[EvidenceChunk, ...],
        claims: tuple[EvidenceClaim, ...],
    ) -> EvidenceItem:
        import psycopg

        settings = self._settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            EvidenceRepository(connection).save_item_with_chunks_and_claims(item, chunks, claims)
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
            saved_item = _save_evidence_submission(repository, submission)
        except Exception:
            return _error_response(
                "evidence_persistence_failed",
                "manual evidence could not be persisted",
                500,
            )

        return _data_response(_submission_payload(saved_item, submission), status_code=201)

    @router.post("/internal/evidence/file")
    def submit_file_evidence(payload: dict[str, object] = Body(...)) -> JSONResponse:
        try:
            settings = settings_provider()
            submission = prepare_file_evidence(payload, allowed_root=settings.data_dir)
        except RuntimeConfigError as error:
            return _error_response("invalid_evidence", str(error), 422)
        except EvidenceValidationError as error:
            return _error_response("invalid_evidence", str(error), 422)

        try:
            saved_item = _save_evidence_submission(repository, submission)
        except Exception:
            return _error_response(
                "evidence_persistence_failed",
                "file evidence could not be persisted",
                500,
            )

        return _data_response(_submission_payload(saved_item, submission), status_code=201)

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

    return _prepare_evidence_submission(
        payload=payload,
        source_uri=source_uri,
        source_type=source_type,
        license_label=license_label,
        data_class=data_class,
        text=text,
        title=title,
        publisher=publisher,
        author=author,
        summary=summary,
        storage_uri=storage_uri,
        published_at=published_at,
        tickers=tickers,
        themes=themes,
        local_only=None,
        default_storage_uri=lambda content_hash: f"local://manual/{content_hash}",
    )


def prepare_file_evidence(
    payload: Mapping[str, object],
    *,
    allowed_root: str | Path,
) -> ManualEvidenceSubmission:
    errors: list[str] = []

    if "text" in payload:
        errors.append("text is not accepted for file evidence; use the manual endpoint")

    source_uri, file_path = _normalize_local_file_source_uri(
        payload.get("source_uri"),
        allowed_root=allowed_root,
        errors=errors,
    )
    source_type = _normalize_source_type(payload.get("source_type"), errors)
    license_label = _normalize_required_text(payload.get("license_label"), "license_label", errors)
    data_class = _normalize_data_class(payload.get("data_class"), errors)
    title = _normalize_optional_text(payload.get("title"), "title", errors)
    publisher = _normalize_optional_text(payload.get("publisher"), "publisher", errors)
    author = _normalize_optional_text(payload.get("author"), "author", errors)
    summary = _normalize_optional_text(payload.get("summary"), "summary", errors)
    storage_uri = _normalize_optional_text(payload.get("storage_uri"), "storage_uri", errors)
    published_at = _parse_optional_datetime(payload.get("published_at"), "published_at", errors)
    tickers = _normalize_string_tuple(payload.get("tickers"), "tickers", errors, uppercase=True)
    themes = _normalize_string_tuple(payload.get("themes"), "themes", errors, uppercase=False)
    text = _read_local_file_text(file_path, errors) if file_path is not None else ""

    if errors:
        raise EvidenceValidationError("; ".join(errors))

    return _prepare_evidence_submission(
        payload=payload,
        source_uri=source_uri,
        source_type=source_type,
        license_label=license_label,
        data_class=data_class,
        text=text,
        title=title,
        publisher=publisher,
        author=author,
        summary=summary,
        storage_uri=storage_uri,
        published_at=published_at,
        tickers=tickers,
        themes=themes,
        local_only=True,
        default_storage_uri=lambda _content_hash: source_uri,
    )


def _prepare_evidence_submission(
    *,
    payload: Mapping[str, object],
    source_uri: str,
    source_type: str,
    license_label: str,
    data_class: DataClass,
    text: str,
    title: str | None,
    publisher: str | None,
    author: str | None,
    summary: str | None,
    storage_uri: str | None,
    published_at: datetime | None,
    tickers: tuple[str, ...],
    themes: tuple[str, ...],
    local_only: bool | None,
    default_storage_uri: Callable[[str], str],
) -> ManualEvidenceSubmission:
    source_metadata = normalize_evidence_source_metadata(
        source_uri=source_uri,
        license_label=license_label,
        data_class=data_class,
        local_only=local_only,
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
        storage_uri=storage_uri or default_storage_uri(content_hash),
        created_at=now,
    )
    chunks = _chunk_text(evidence_id=evidence_id, text=text)
    errors: list[str] = []
    claims = _normalize_claims(
        payload.get("claims"),
        evidence_id=evidence_id,
        chunks=chunks,
        now=now,
        errors=errors,
    )
    if errors:
        raise EvidenceValidationError("; ".join(errors))

    return ManualEvidenceSubmission(
        item=item,
        chunks=chunks,
        claims=claims,
        local_only=source_metadata.local_only,
    )


def _save_evidence_submission(
    repository: ManualEvidenceRepository,
    submission: ManualEvidenceSubmission,
) -> EvidenceItem:
    if not submission.claims:
        return repository.save_manual_evidence(submission.item, submission.chunks)

    return repository.save_evidence_with_claims(
        submission.item,
        submission.chunks,
        submission.claims,
    )


def _submission_payload(
    saved_item: EvidenceItem,
    submission: ManualEvidenceSubmission,
) -> dict[str, object]:
    return {
        "evidence_id": saved_item.evidence_id,
        "content_hash": saved_item.content_hash,
        "data_class": saved_item.data_class.value,
        "chunk_count": len(submission.chunks),
        "claim_count": len(submission.claims),
        "local_only": submission.local_only,
    }


def _normalize_local_file_source_uri(
    value: object,
    *,
    allowed_root: str | Path,
    errors: list[str],
) -> tuple[str, Path | None]:
    raw = _normalize_required_text(value, "source_uri", errors)
    if not raw:
        return "", None

    try:
        root = Path(allowed_root).expanduser().resolve(strict=True)
    except OSError:
        errors.append("file evidence root is unavailable")
        return raw, None

    parts = urlsplit(raw)
    if parts.scheme.lower() != "file":
        errors.append("source_uri must use file scheme for file evidence")
        return raw, None
    if parts.netloc and parts.netloc.lower() != "localhost":
        errors.append("file source_uri must reference a local file")
        return raw, None
    if parts.query or parts.fragment:
        errors.append("file source_uri must not include query or fragment")
        return raw, None

    decoded_path = unquote(parts.path)
    if "\x00" in decoded_path:
        errors.append("file source_uri path is invalid")
        return raw, None

    path = Path(decoded_path)
    if not path.is_absolute():
        errors.append("file source_uri must use an absolute path")
        return raw, None

    try:
        resolved_path = path.resolve(strict=True)
    except OSError:
        errors.append("file source_uri must point to an existing local file")
        return raw, None

    if not resolved_path.is_file():
        errors.append("file source_uri must point to a regular file")
        return raw, None
    try:
        resolved_path.relative_to(root)
    except ValueError:
        errors.append("file source_uri must stay within configured data_dir")
        return raw, None
    if resolved_path.suffix.lower() not in ALLOWED_FILE_SUFFIXES:
        errors.append(f"file evidence suffix must be one of {sorted(ALLOWED_FILE_SUFFIXES)}")
        return raw, None

    try:
        size_bytes = resolved_path.stat().st_size
    except OSError:
        errors.append("file source_uri could not be inspected")
        return raw, None
    if size_bytes > MAX_TEXT_CHARS * 4:
        errors.append(f"file evidence must be {MAX_TEXT_CHARS} characters or fewer")
        return raw, None

    return resolved_path.as_uri(), resolved_path


def _read_local_file_text(file_path: Path, errors: list[str]) -> str:
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append("file evidence must be UTF-8 text")
        return ""
    except OSError:
        errors.append("file evidence could not be read")
        return ""

    return _normalize_text(raw_text, errors)


def _normalize_claims(
    value: object,
    *,
    evidence_id: str,
    chunks: tuple[EvidenceChunk, ...],
    now: datetime,
    errors: list[str],
) -> tuple[EvidenceClaim, ...]:
    if value is None:
        return ()
    if isinstance(value, str) or not isinstance(value, list):
        errors.append("claims must be a list")
        return ()

    chunk_ids_by_index = {chunk.chunk_index: chunk.chunk_id for chunk in chunks}
    valid_chunk_ids = frozenset(chunk_ids_by_index.values())
    claims: list[EvidenceClaim] = []

    for index, raw_claim in enumerate(value):
        field_prefix = f"claims[{index}]"
        if not isinstance(raw_claim, Mapping):
            errors.append(f"{field_prefix} must be an object")
            continue

        error_count = len(errors)
        claim = _normalize_claim(
            raw_claim,
            field_prefix=field_prefix,
            evidence_id=evidence_id,
            chunk_ids_by_index=chunk_ids_by_index,
            valid_chunk_ids=valid_chunk_ids,
            now=now,
            errors=errors,
        )
        if claim is not None and len(errors) == error_count:
            claims.append(claim)

    return tuple(claims)


def _normalize_claim(
    payload: Mapping[str, object],
    *,
    field_prefix: str,
    evidence_id: str,
    chunk_ids_by_index: dict[int, str],
    valid_chunk_ids: frozenset[str],
    now: datetime,
    errors: list[str],
) -> EvidenceClaim | None:
    payload_evidence_id = _normalize_optional_text(payload.get("evidence_id"), f"{field_prefix}.evidence_id", errors)
    if payload_evidence_id is not None and payload_evidence_id != evidence_id:
        errors.append(f"{field_prefix}.evidence_id must match the generated evidence_id")

    extracted_by_model_run_id = _normalize_optional_text(
        payload.get("extracted_by_model_run_id"),
        f"{field_prefix}.extracted_by_model_run_id",
        errors,
    )
    if extracted_by_model_run_id is not None:
        errors.append(f"{field_prefix}.extracted_by_model_run_id is not accepted for manual/file evidence")

    chunk_id = _normalize_claim_chunk_id(
        payload,
        field_prefix=field_prefix,
        chunk_ids_by_index=chunk_ids_by_index,
        valid_chunk_ids=valid_chunk_ids,
        errors=errors,
    )
    ticker_or_theme = _normalize_required_text(payload.get("ticker_or_theme"), f"{field_prefix}.ticker_or_theme", errors)
    claim_type = _normalize_required_text(payload.get("claim_type"), f"{field_prefix}.claim_type", errors)
    direction = _normalize_optional_text(payload.get("direction"), f"{field_prefix}.direction", errors)
    magnitude = _normalize_optional_decimal(payload.get("magnitude"), f"{field_prefix}.magnitude", errors)
    time_horizon = _normalize_required_text(payload.get("time_horizon"), f"{field_prefix}.time_horizon", errors)
    confidence = _normalize_required_confidence(payload.get("confidence"), f"{field_prefix}.confidence", errors)
    quote_or_span_ref = _normalize_required_text(
        payload.get("quote_or_span_ref"),
        f"{field_prefix}.quote_or_span_ref",
        errors,
    )
    validated_at = _parse_optional_datetime(payload.get("validated_at"), f"{field_prefix}.validated_at", errors)
    claim_id = _normalize_optional_text(payload.get("claim_id"), f"{field_prefix}.claim_id", errors)

    if chunk_id is None or confidence is None or len(errors) > 0:
        return None

    return EvidenceClaim(
        claim_id=claim_id
        or _claim_id_for(
            evidence_id=evidence_id,
            chunk_id=chunk_id,
            ticker_or_theme=ticker_or_theme,
            claim_type=claim_type,
            quote_or_span_ref=quote_or_span_ref,
        ),
        evidence_id=evidence_id,
        chunk_id=chunk_id,
        ticker_or_theme=ticker_or_theme,
        claim_type=claim_type,
        direction=direction,
        magnitude=magnitude,
        time_horizon=time_horizon,
        confidence=confidence,
        quote_or_span_ref=quote_or_span_ref,
        extracted_by_model_run_id=None,
        validated_at=validated_at,
        created_at=now,
    )


def _normalize_claim_chunk_id(
    payload: Mapping[str, object],
    *,
    field_prefix: str,
    chunk_ids_by_index: dict[int, str],
    valid_chunk_ids: frozenset[str],
    errors: list[str],
) -> str | None:
    explicit_chunk_id = _normalize_optional_text(payload.get("chunk_id"), f"{field_prefix}.chunk_id", errors)
    chunk_index = payload.get("chunk_index")
    indexed_chunk_id: str | None = None

    if explicit_chunk_id is None and chunk_index is None:
        errors.append(f"{field_prefix} must include chunk_index or chunk_id")
        return None

    if chunk_index is not None:
        if isinstance(chunk_index, bool) or not isinstance(chunk_index, int):
            errors.append(f"{field_prefix}.chunk_index must be an integer")
        elif chunk_index not in chunk_ids_by_index:
            errors.append(f"{field_prefix}.chunk_index must reference an existing chunk")
        else:
            indexed_chunk_id = chunk_ids_by_index[chunk_index]

    if explicit_chunk_id is not None and explicit_chunk_id not in valid_chunk_ids:
        errors.append(f"{field_prefix}.chunk_id must reference an existing chunk")
    if explicit_chunk_id is not None and indexed_chunk_id is not None and explicit_chunk_id != indexed_chunk_id:
        errors.append(f"{field_prefix}.chunk_id must match chunk_index")

    return explicit_chunk_id or indexed_chunk_id


def _normalize_optional_decimal(value: object, field_name: str, errors: list[str]) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    decimal_value = _parse_decimal(value, field_name, errors)
    return decimal_value


def _normalize_required_confidence(value: object, field_name: str, errors: list[str]) -> Decimal | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        errors.append(f"{field_name} is required")
        return None

    decimal_value = _parse_decimal(value, field_name, errors)
    if decimal_value is None:
        return None
    if decimal_value < Decimal("0") or decimal_value > Decimal("1"):
        errors.append(f"{field_name} must be between 0 and 1")
        return None
    return decimal_value


def _parse_decimal(value: object, field_name: str, errors: list[str]) -> Decimal | None:
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        errors.append(f"{field_name} must be numeric")
        return None


def _claim_id_for(
    *,
    evidence_id: str,
    chunk_id: str,
    ticker_or_theme: str,
    claim_type: str,
    quote_or_span_ref: str,
) -> str:
    content_hash = compute_content_hash(
        quote_or_span_ref,
        metadata={
            "claim_type": claim_type,
            "chunk_id": chunk_id,
            "evidence_id": evidence_id,
            "ticker_or_theme": ticker_or_theme,
        },
    )
    return f"claim-{content_hash[:16]}"


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
