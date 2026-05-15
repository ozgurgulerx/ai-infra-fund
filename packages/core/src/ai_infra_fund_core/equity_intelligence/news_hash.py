from __future__ import annotations

import re
from hashlib import sha256


_BODY_PREFIX_LEN = 500
_WHITESPACE = re.compile(r"\s+")
_TRAILING_PUNCT = re.compile(r"[\W_]+$")


def news_content_hash(*, title: str, body: str) -> str:
    """Stable hash for deduping the same news story across GDELT and Finnhub.

    Normalization (lowercase, collapsed whitespace, trimmed trailing
    punctuation) lets cross-aggregator duplicates collide on the
    `evidence_items.content_hash` unique constraint instead of slipping
    through as distinct rows.
    """
    normalized_title = _normalize(title)
    normalized_body = _normalize(body)[:_BODY_PREFIX_LEN]
    digest_seed = f"{normalized_title}\n{normalized_body}"
    return sha256(digest_seed.encode("utf-8")).hexdigest()


def _normalize(value: str) -> str:
    collapsed = _WHITESPACE.sub(" ", value.strip().lower())
    return _TRAILING_PUNCT.sub("", collapsed)


__all__ = ["news_content_hash"]
