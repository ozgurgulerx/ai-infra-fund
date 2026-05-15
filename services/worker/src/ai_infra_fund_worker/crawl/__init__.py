"""Phase 10 crawl pipeline runtime.

Contains the worker-side glue around `core.equity_intelligence` and
the API repository so a long-running process can seed the frontier,
lease URLs, fetch them via httpx, capture bodies, extract events,
and persist runs — all watchlist-driven, advisory-only.
"""

from __future__ import annotations
