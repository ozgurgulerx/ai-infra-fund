from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.local_inputs.watchlist import load_ai_equity_watchlist  # noqa: E402
from ai_infra_fund_core.model_routing.profiles import load_model_profiles  # noqa: E402
from ai_infra_fund_core.model_routing.router import ModelRouter  # noqa: E402
from ai_infra_fund_core.equity_intelligence import (  # noqa: E402
    DynamicRatingInput,
    DynamicRatingLabel,
    build_research_monitoring_plan,
    derive_dynamic_rating,
)


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)

SITUATIONAL_AWARENESS_PUBLIC_EQUITIES = {
    "NVDA",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "AMD",
    "TSM",
    "INTC",
    "BIDU",
    "SMICY",
}


class EquityResearchMonitoringTests(unittest.TestCase):
    def test_situational_awareness_equities_are_grouped_and_deep_researched(self) -> None:
        watchlist = load_ai_equity_watchlist(ROOT / "config" / "ai_equity_watchlist.yaml")
        router = ModelRouter(load_model_profiles(ROOT / "config" / "model_profiles.yaml"))

        plan = build_research_monitoring_plan(watchlist, as_of=NOW, router=router)

        tickers = {equity.ticker for equity in plan.equities}
        self.assertTrue(SITUATIONAL_AWARENESS_PUBLIC_EQUITIES.issubset(tickers))
        self.assertTrue(
            all(
                equity.monitor_every <= timedelta(days=1)
                for equity in plan.equities
                if equity.ticker in SITUATIONAL_AWARENESS_PUBLIC_EQUITIES
            )
        )

        theme_groups = {group.theme: group for group in plan.theme_groups}
        self.assertTrue({"ai_accelerators", "hyperscaler_capex", "foundry_capacity"}.issubset(theme_groups))
        self.assertTrue({"NVDA", "AMD"}.issubset(theme_groups["ai_accelerators"].tickers))
        self.assertTrue(
            {"MSFT", "GOOGL", "AMZN", "META", "TSLA"}.issubset(
                theme_groups["hyperscaler_capex"].tickers
            )
        )
        self.assertTrue({"TSM", "SMICY"}.issubset(theme_groups["foundry_capacity"].tickers))

        tasks_by_ticker = {task.ticker: task for task in plan.deep_research_tasks}
        for ticker in SITUATIONAL_AWARENESS_PUBLIC_EQUITIES:
            task = tasks_by_ticker[ticker]
            self.assertEqual(("public_evidence",), tuple(data_class.value for data_class in task.data_classes))
            self.assertEqual(("evidence_summary", "adversarial_review"), task.task_roles)
            self.assertTrue(task.model_profile_ids)
            self.assertTrue(task.fallback_profile_ids)
            self.assertGreaterEqual(len(task.evidence_source_urls), 1)

        refresh_jobs_by_ticker = {job.ticker: job for job in plan.refresh_jobs}
        for ticker in SITUATIONAL_AWARENESS_PUBLIC_EQUITIES:
            job = refresh_jobs_by_ticker[ticker]
            self.assertEqual("queued", job.status)
            self.assertIn("continuous_monitoring", job.reason)
            self.assertGreater(job.priority_boost, 0)

    def test_dynamic_rating_update_uses_llm_lineage_but_keeps_scoring_deterministic(self) -> None:
        rating = derive_dynamic_rating(
            DynamicRatingInput(
                ticker="nvda",
                as_of=NOW,
                evidence_ids=("evidence-nvda-1",),
                model_run_ids=("model-run-summary-1", "model-run-review-1"),
                event_confidence=Decimal("0.90"),
                sentiment_score=Decimal("0.70"),
                technical_trend_label="uptrend",
                fundamental_rating_label="compounder",
                llm_review_status="model_extracted",
            )
        )

        self.assertEqual("NVDA", rating.ticker)
        self.assertEqual(DynamicRatingLabel.STRONG_POSITIVE, rating.rating_label)
        self.assertEqual(("evidence-nvda-1",), rating.evidence_ids)
        self.assertEqual(("model-run-summary-1", "model-run-review-1"), rating.model_run_ids)
        self.assertEqual("advisory_only", rating.advisory_label.value)
        self.assertEqual("deterministic_llm_lineage_policy_v1", rating.generated_by)
        self.assertFalse(hasattr(rating, "target_weight"))

        with self.assertRaisesRegex(ValueError, "model_run_ids"):
            derive_dynamic_rating(
                DynamicRatingInput(
                    ticker="NVDA",
                    as_of=NOW,
                    evidence_ids=("evidence-nvda-1",),
                    model_run_ids=(),
                    event_confidence=Decimal("0.90"),
                    sentiment_score=Decimal("0.70"),
                    technical_trend_label="uptrend",
                    fundamental_rating_label="compounder",
                    llm_review_status="model_extracted",
                )
            )


if __name__ == "__main__":
    unittest.main()
