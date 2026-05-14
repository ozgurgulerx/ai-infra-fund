"""Parity test: the TS mirror at apps/web/lib/watchlist-mirror.ts must list the
same tickers as the YAML source of truth at config/ai_equity_watchlist.yaml.

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
    def test_ts_mirror_lists_same_tickers_as_yaml(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import load_ai_equity_watchlist

        yaml_path = ROOT / "config" / "ai_equity_watchlist.yaml"
        mirror_path = ROOT / "apps" / "web" / "lib" / "watchlist-mirror.ts"

        yaml_tickers = {
            entry.ticker for entry in load_ai_equity_watchlist(yaml_path).entries
        }

        mirror_text = mirror_path.read_text(encoding="utf-8")
        mirror_tickers = set(
            re.findall(r'ticker:\s*"([A-Z][A-Z0-9.\-]{0,9})"', mirror_text)
        )

        missing_in_ts = yaml_tickers - mirror_tickers
        extra_in_ts = mirror_tickers - yaml_tickers

        self.assertFalse(
            missing_in_ts,
            f"tickers present in YAML but missing in TS mirror: {sorted(missing_in_ts)}",
        )
        self.assertFalse(
            extra_in_ts,
            f"tickers present in TS mirror but missing in YAML: {sorted(extra_in_ts)}",
        )


if __name__ == "__main__":
    unittest.main()
