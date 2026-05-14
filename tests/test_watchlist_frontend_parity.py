"""Parity test: the TS mirror at apps/web/lib/watchlist-mirror.ts must match the
YAML source of truth at config/ai_equity_watchlist.yaml on tickers and themes.

The TS file is a temporary hand-mirror until a /internal/config/watchlist
endpoint is exposed. This test catches silent drift between the two.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))


class WatchlistFrontendParityTests(unittest.TestCase):
    def test_ts_mirror_matches_yaml_on_tickers_and_themes(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import (
            TICKER_PATTERN,
            load_ai_equity_watchlist,
        )

        yaml_path = ROOT / "config" / "ai_equity_watchlist.yaml"
        mirror_path = ROOT / "apps" / "web" / "lib" / "watchlist-mirror.ts"

        self.assertTrue(
            mirror_path.exists(),
            f"TS watchlist mirror not found at {mirror_path.relative_to(ROOT)}",
        )

        yaml_themes_by_ticker = {
            entry.ticker: tuple(sorted(entry.themes))
            for entry in load_ai_equity_watchlist(yaml_path).entries
        }

        mirror_text = mirror_path.read_text(encoding="utf-8")
        mirror_themes_by_ticker = _parse_mirror_themes(
            mirror_text, TICKER_PATTERN.pattern
        )

        missing_in_ts = set(yaml_themes_by_ticker) - set(mirror_themes_by_ticker)
        extra_in_ts = set(mirror_themes_by_ticker) - set(yaml_themes_by_ticker)
        self.assertFalse(
            missing_in_ts,
            f"tickers present in YAML but missing in TS mirror: {sorted(missing_in_ts)}",
        )
        self.assertFalse(
            extra_in_ts,
            f"tickers present in TS mirror but missing in YAML: {sorted(extra_in_ts)}",
        )

        theme_mismatches = {
            ticker: {
                "yaml": yaml_themes_by_ticker[ticker],
                "mirror": mirror_themes_by_ticker[ticker],
            }
            for ticker in yaml_themes_by_ticker
            if yaml_themes_by_ticker[ticker] != mirror_themes_by_ticker[ticker]
        }
        self.assertFalse(
            theme_mismatches,
            f"theme arrays differ between YAML and TS mirror: {theme_mismatches}",
        )


def _parse_mirror_themes(text: str, ticker_pattern: str) -> dict[str, tuple[str, ...]]:
    """Pull each `ticker: "XYZ"` block and its `themes: [...]` array out of the
    TS mirror. The mirror is hand-authored and formatted by prettier, so we
    parse pragmatically rather than running a full TS AST."""

    # Match entries of the form `{ ticker: "NVDA", ... themes: [ ... ], ... }`.
    # We rely on the prettier-normalised layout where ticker precedes themes
    # within the same object literal.
    entry_re = re.compile(
        r'ticker:\s*"(?P<ticker>' + ticker_pattern.strip("^$") + r')"'
        r"[^}]*?themes:\s*\[(?P<themes>[^\]]*)\]",
        re.DOTALL,
    )
    string_re = re.compile(r'"([^"\\]+)"')

    parsed: dict[str, tuple[str, ...]] = {}
    for match in entry_re.finditer(text):
        ticker = match.group("ticker")
        themes = tuple(sorted(string_re.findall(match.group("themes"))))
        parsed[ticker] = themes
    return parsed


if __name__ == "__main__":
    unittest.main()
