from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.signals.technical import MarketPoint, compute_technical_snapshot  # noqa: E402


class AdvancedTechnicalSignalTests(unittest.TestCase):
    def test_optional_advanced_technical_diagnostics_identify_mean_reversion_setup(self) -> None:
        points = [
            MarketPoint(
                as_of=datetime(2026, 5, day, tzinfo=timezone.utc),
                close=Decimal(str(close)),
                volume=Decimal("1000"),
            )
            for day, close in enumerate((100, 101, 100, 102, 101, 103, 102, 104, 103, 80), start=1)
        ]

        snapshot = compute_technical_snapshot(
            ticker="nvda",
            as_of=datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc),
            points=points,
            advanced_signals=True,
        )

        self.assertGreater(snapshot.mean_reversion_score, Decimal("0.80"))
        self.assertLess(snapshot.rsi_score, Decimal("0.35"))
        self.assertGreaterEqual(snapshot.volatility_regime_score, Decimal("0"))
        self.assertLessEqual(snapshot.volatility_regime_score, Decimal("1"))
        self.assertGreaterEqual(snapshot.return_consistency_score, Decimal("0"))
        self.assertLessEqual(snapshot.return_consistency_score, Decimal("1"))


if __name__ == "__main__":
    unittest.main()
