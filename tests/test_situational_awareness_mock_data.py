import json
import unittest
from pathlib import Path


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "mock_data"
    / "situational_awareness_brief.example.json"
)

REQUIRED_TICKERS = {
    "NVDA",
    "AMD",
    "AVGO",
    "TSM",
    "ASML",
    "MU",
    "ANET",
    "MRVL",
    "VRT",
    "ETN",
    "PWR",
    "CEG",
    "DLR",
    "EQIX",
    "ORCL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
}

REQUIRED_WORKSTATION_KEYS = {
    "portfolio_snapshot",
    "open_trade_plans",
    "watchlist_alerts",
    "suggested_actions",
    "trade_journal_summary",
    "pnl_summary",
    "price_target_scenarios",
    "entry_exit_levels",
    "correlation_exposures",
    "llm_analyst_notes",
}

FORBIDDEN_EXECUTION_KEYS = {
    "broker",
    "broker_id",
    "broker_account",
    "broker_account_id",
    "execution_id",
    "fill_id",
    "order",
    "order_id",
    "order_route",
    "route",
    "submit_order",
    "trade_execution",
}

ALLOWED_ADVISORY_LABELS = {
    "watch",
    "accumulate",
    "hold",
    "trim",
    "avoid",
}


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


class SituationalAwarenessMockDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FIXTURE_PATH.read_text())
        cls.evidence_ids = {
            item["evidence_id"] for item in cls.data.get("evidence_items", [])
        }
        cls.event_ids = {
            item["event_id"] for item in cls.data.get("market_events", [])
        }
        cls.segment_ids = {
            item["segment_id"] for item in cls.data.get("segment_impacts", [])
        }
        cls.advisory_ids = {
            item["advisory_id"] for item in cls.data.get("trading_advisories", [])
        }
        cls.model_run_ids = {
            item["model_run_id"] for item in cls.data.get("model_runs", [])
        }

    def test_workstation_feed_keys_exist(self):
        self.assertTrue(REQUIRED_WORKSTATION_KEYS.issubset(self.data.keys()))
        for key in REQUIRED_WORKSTATION_KEYS:
            self.assertTrue(self.data[key], f"{key} should not be empty")

    def test_required_ticker_coverage(self):
        seen = set()
        for node in _walk(self.data):
            tickers = node.get("tickers")
            if isinstance(tickers, list):
                seen.update(tickers)
            ticker = node.get("ticker")
            if isinstance(ticker, str):
                seen.add(ticker)
        self.assertTrue(REQUIRED_TICKERS.issubset(seen))

    def test_references_are_internally_consistent(self):
        for event in self.data.get("market_events", []):
            self.assertTrue(event.get("evidence_ids"))
            self.assertTrue(set(event["evidence_ids"]).issubset(self.evidence_ids))

        for impact in self.data.get("segment_impacts", []):
            self.assertTrue(set(impact["linked_event_ids"]).issubset(self.event_ids))
            self.assertTrue(set(impact.get("evidence_ids", [])).issubset(self.evidence_ids))

        for action in self.data.get("suggested_actions", []):
            self.assertIn(action["advisory_label"], ALLOWED_ADVISORY_LABELS)
            self.assertTrue(set(action["evidence_ids"]).issubset(self.evidence_ids))
            self.assertTrue(set(action["linked_event_ids"]).issubset(self.event_ids))
            self.assertIn(action["linked_advisory_id"], self.advisory_ids)
            self.assertTrue(action["risk_flags"])
            self.assertTrue(action["invalidation_condition"])

    def test_prompt_and_llm_notes_link_to_model_runs_or_evidence(self):
        for note in self.data.get("llm_analyst_notes", []):
            self.assertIn(note["model_run_id"], self.model_run_ids)
            self.assertTrue(set(note.get("evidence_ids", [])).issubset(self.evidence_ids))
            self.assertTrue(note.get("deterministic_fields_not_modified"))

    def test_no_broker_execution_fields_are_present(self):
        forbidden_seen = set()
        for node in _walk(self.data):
            forbidden_seen.update(FORBIDDEN_EXECUTION_KEYS.intersection(node.keys()))
        self.assertEqual(set(), forbidden_seen)


if __name__ == "__main__":
    unittest.main()
