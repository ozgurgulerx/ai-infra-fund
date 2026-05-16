from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
from typing import cast

import feedparser  # type: ignore[import-untyped]
import trafilatura  # type: ignore[import-untyped]
from bs4 import BeautifulSoup


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    title: str | None
    published_at: datetime | None
    clean_text: str
    lang: str | None
    chars: int
    quality_score: float


@dataclass(frozen=True, slots=True)
class RssItem:
    guid: str
    title: str
    link: str | None
    published_at: datetime | None
    summary: str


_TRAFILATURA_MIN_CHARS = 200


def extract_html(body: bytes, *, base_url: str) -> ExtractedDocument:
    text = body.decode("utf-8", errors="replace")
    extracted = trafilatura.extract(
        text,
        url=base_url,
        include_comments=False,
        include_tables=False,
        favor_recall=True,
    )
    if not extracted or len(extracted) < _TRAFILATURA_MIN_CHARS:
        extracted = _bs_fallback(text)

    soup = BeautifulSoup(text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    published_at = _meta_published_at(soup)
    lang_tag = soup.find("html")
    lang = None
    if lang_tag is not None:
        lang_value = lang_tag.get("lang") if hasattr(lang_tag, "get") else None  # type: ignore[attr-defined]
        if isinstance(lang_value, str):
            lang = lang_value

    clean_text = extracted or ""
    chars = len(clean_text)
    return ExtractedDocument(
        title=title,
        published_at=published_at,
        clean_text=clean_text,
        lang=lang,
        chars=chars,
        quality_score=_quality_score(clean_text),
    )


def extract_rss(body: bytes) -> tuple[RssItem, ...]:
    parsed = feedparser.parse(body)
    items: list[RssItem] = []
    for entry in parsed.entries:
        guid = entry.get("id") or entry.get("guid") or entry.get("link")
        if not guid:
            continue
        published_at = _entry_published_at(entry)
        items.append(
            RssItem(
                guid=str(guid),
                title=str(entry.get("title") or "").strip(),
                link=str(entry.get("link") or "") or None,
                published_at=published_at,
                summary=str(
                    entry.get("summary") or entry.get("description") or ""
                ).strip(),
            )
        )
    return tuple(items)


def extract_pdf(body: bytes) -> ExtractedDocument:
    import fitz  # type: ignore[import-not-found]  # lazy: PyMuPDF heavy

    document = fitz.open(stream=body, filetype="pdf")
    try:
        pages = [page.get_text("text") for page in document]
    finally:
        document.close()
    clean_text = "\n\n".join(p.strip() for p in pages if p.strip())
    return ExtractedDocument(
        title=None,
        published_at=None,
        clean_text=clean_text,
        lang=None,
        chars=len(clean_text),
        quality_score=_quality_score(clean_text),
    )


def extract(
    content_type: str,
    body: bytes,
    *,
    base_url: str,
) -> ExtractedDocument | tuple[RssItem, ...]:
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype in (
        "application/rss+xml",
        "application/atom+xml",
        "text/xml",
        "application/xml",
    ):
        return extract_rss(body)
    if ctype == "application/pdf":
        return extract_pdf(body)
    if ctype == "application/json":
        return extract_json(body)
    return extract_html(body, base_url=base_url)


def extract_json(body: bytes) -> ExtractedDocument:
    text = body.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        clean_text = text.strip()
        return ExtractedDocument(
            title=None,
            published_at=None,
            clean_text=clean_text,
            lang=None,
            chars=len(clean_text),
            quality_score=_quality_score(clean_text),
        )
    article_titles = _json_article_titles(payload)
    provider_message = _json_provider_message(payload)
    clean_text = "\n".join(article_titles) or provider_message or ""
    return ExtractedDocument(
        title=article_titles[0] if article_titles else provider_message or None,
        published_at=None,
        clean_text=clean_text,
        lang=None,
        chars=len(clean_text),
        quality_score=_quality_score(clean_text),
    )


def _json_article_titles(payload: object) -> tuple[str, ...]:
    raw_articles = _json_records(payload)
    if not isinstance(raw_articles, list):
        return ()

    titles: list[str] = []
    for article in raw_articles:
        if not isinstance(article, dict):
            continue
        title = str(article.get("title") or article.get("headline") or "").strip()
        if title:
            titles.append(title)
    return tuple(titles)


def _json_records(payload: object) -> object:
    if isinstance(payload, dict):
        for key in ("articles", "data", "results", "items", "feed"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return ()
    return payload


def _json_provider_message(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("error", "errorMessage", "message", "detail", "status"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _bs_fallback(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    return soup.get_text(separator="\n", strip=True)


def _meta_published_at(soup: BeautifulSoup) -> datetime | None:
    for selector in (
        ("meta", {"property": "article:published_time"}),
        ("meta", {"name": "article:published_time"}),
        ("meta", {"name": "pubdate"}),
        ("meta", {"name": "date"}),
        ("time", {}),
    ):
        tag, attrs = selector
        node = soup.find(tag, attrs=attrs)
        if node is None:
            continue
        value = None
        if hasattr(node, "get"):
            value = node.get("content") or node.get("datetime")  # type: ignore[attr-defined]
        if not value and node.text:
            value = node.text.strip()
        if isinstance(value, str) and value:
            parsed = _parse_iso(value)
            if parsed is not None:
                return parsed
    return None


def _entry_published_at(entry: object) -> datetime | None:
    if isinstance(entry, dict):
        getter = entry.get
    else:
        getter = lambda key, default=None: getattr(entry, key, default)  # type: ignore[assignment]
    parsed_struct = getter("published_parsed") or getter("updated_parsed")
    if parsed_struct is not None:
        try:
            return datetime(*parsed_struct[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    published = getter("published") or getter("updated")
    if isinstance(published, str) and published:
        try:
            return parsedate_to_datetime(published)
        except (TypeError, ValueError):
            return _parse_iso(published)
    return None


def _parse_iso(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _quality_score(text: str) -> float:
    length = len(text)
    if length <= 0:
        return 0.0
    # Heuristic: length-saturating curve + paragraph density.
    paragraphs = max(1, text.count("\n\n") + 1)
    paragraph_signal = min(1.0, paragraphs / 8.0)
    length_signal = min(1.0, length / 4000.0)
    return round(cast(float, 0.4 * paragraph_signal + 0.6 * length_signal), 4)


__all__ = [
    "ExtractedDocument",
    "RssItem",
    "extract",
    "extract_json",
    "extract_html",
    "extract_pdf",
    "extract_rss",
]
