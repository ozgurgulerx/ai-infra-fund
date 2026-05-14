from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "apps" / "web"


def read_web(relative_path: str) -> str:
    return (WEB_ROOT / relative_path).read_text(encoding="utf-8")


def web_source_files() -> tuple[Path, ...]:
    return tuple(
        path
        for path in WEB_ROOT.rglob("*")
        if path.suffix in {".ts", ".tsx", ".css"}
        and "node_modules" not in path.parts
        and ".next" not in path.parts
    )


class TradeJournalUiTests(unittest.TestCase):
    def test_manual_trade_entry_form_posts_only_to_local_journal(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in web_source_files())
        required = [
            "Add Trade To Local Journal",
            "createTradeJournalEntry",
            "fetchTradeJournalEntries",
            "/internal/trade-journal/entries",
            "/api/trade-journal/entries",
            "Manual buy/sell journal entry",
            "Journal-only record",
            "Trade date",
            "Settlement date",
            "Account label",
            "Local journal only",
            "No broker connection",
        ]

        self.assertEqual([], [text for text in required if text not in combined])

    def test_trade_journal_page_mounts_manual_entry_form(self) -> None:
        page = read_web("app/trade-journal/page.tsx")
        api = read_web("lib/api.ts")
        proxy = read_web("app/api/trade-journal/entries/route.ts")

        self.assertIn("<TradeEntryForm />", page)
        self.assertIn("method: \"POST\"", api)
        self.assertIn("AI_INFRA_FUND_INTERNAL_API_BASE_URL", proxy)
        self.assertIn("NEXT_PUBLIC_API_BASE_URL", proxy)

    def test_trade_journal_ui_has_no_execution_controls(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in web_source_files())
        forbidden_label_patterns = [
            r">\s*Place\s+Order\s*<",
            r">\s*Submit\s+Order\s*<",
            r">\s*Execute\s+Order\s*<",
            r">\s*Connect\s+Broker\s*<",
            r">\s*Start\s+Live\s+Trading\s*<",
        ]

        offenders = [
            pattern
            for pattern in forbidden_label_patterns
            if re.search(pattern, combined, re.IGNORECASE)
        ]
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
