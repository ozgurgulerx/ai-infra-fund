from __future__ import annotations

from dataclasses import dataclass
from posixpath import normpath
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

from ai_infra_fund_core.contracts.common import require_text


TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


@dataclass(frozen=True, slots=True)
class CanonicalUrl:
    raw_url: str
    canonical_url: str
    domain: str
    path: str


def canonicalize_url(raw_url: str) -> CanonicalUrl:
    normalized_raw = require_text(raw_url, "raw_url").strip()
    parsed = urlparse(normalized_raw)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("url must use http or https scheme")
    if not parsed.hostname:
        raise ValueError("url must include a hostname")

    domain = parsed.hostname.lower().rstrip(".")
    netloc = _netloc_for(domain=domain, scheme=scheme, port=parsed.port)
    path = _canonical_path(parsed.path)
    query = _canonical_query(parsed.query)
    canonical = urlunparse((scheme, netloc, path, "", query, ""))
    return CanonicalUrl(
        raw_url=normalized_raw,
        canonical_url=canonical,
        domain=domain,
        path=path,
    )


def _netloc_for(*, domain: str, scheme: str, port: int | None) -> str:
    if port is None or (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        return domain
    return f"{domain}:{port}"


def _canonical_path(path: str) -> str:
    if not path or path == "/":
        return "/"
    compact = normpath(path)
    if not compact.startswith("/"):
        compact = f"/{compact}"
    return quote(compact, safe="/:@-._~")


def _canonical_query(query: str) -> str:
    pairs = parse_qsl(query, keep_blank_values=True)
    kept = (
        (key, value)
        for key, value in pairs
        if key.lower() not in TRACKING_QUERY_KEYS
        and not key.lower().startswith(TRACKING_QUERY_PREFIXES)
    )
    return urlencode(sorted(kept), doseq=True)
