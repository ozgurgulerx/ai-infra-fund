from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))


class LocalInputValidatorTests(unittest.TestCase):
    def test_portfolio_csv_validation_normalizes_positions(self) -> None:
        from ai_infra_fund_core.local_inputs.csv_validators import load_portfolio_positions_csv

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "portfolio_positions.csv"
            path.write_text(
                "\n".join(
                    [
                        "ticker,quantity,cost_basis,market_price,currency,asset_type,account_label,as_of,available_at",
                        "nvda,3,200,900,usd,equity,brokerage,2026-05-14T10:00:00+00:00,2026-05-14T10:05:00+00:00",
                        "cash,1000,1,1,USD,cash,brokerage,2026-05-14T10:00:00+00:00,2026-05-14T10:05:00+00:00",
                    ]
                ),
                encoding="utf-8",
            )

            positions = load_portfolio_positions_csv(path)

        self.assertEqual(("NVDA", "CASH"), tuple(position.ticker for position in positions))
        self.assertEqual("USD", positions[0].currency)
        self.assertEqual("equity", positions[0].asset_type.value)
        self.assertEqual("2026-05-14T10:00:00+00:00", positions[0].as_of.isoformat())
        self.assertEqual("2026-05-14T10:05:00+00:00", positions[0].available_at.isoformat())

    def test_trade_journal_csv_validation_rejects_invalid_side(self) -> None:
        from ai_infra_fund_core.local_inputs.csv_validators import load_trade_journal_csv

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trade_journal.csv"
            path.write_text(
                "\n".join(
                    [
                        "ticker,side,quantity,price,fees,trade_date,status,account_label,notes",
                        "NVDA,hold,1,900,0,2026-05-14,completed,brokerage,invalid",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "side"):
                load_trade_journal_csv(path)

    def test_universe_csv_validation_requires_ticker_and_theme(self) -> None:
        from ai_infra_fund_core.local_inputs.csv_validators import load_universe_csv

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "universe.csv"
            path.write_text(
                "\n".join(
                    [
                        "ticker,name,theme,role,watchlist_status,max_weight,liquidity_floor,thesis_source",
                        "NVDA,NVIDIA,ai_accelerators,core,active,0.25,0.05,manual",
                        ",Missing,ai_accelerators,core,active,0.25,0.05,manual",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "ticker"):
                load_universe_csv(path)

    def test_market_snapshot_csv_validation_requires_point_in_time_fields(self) -> None:
        from ai_infra_fund_core.local_inputs.csv_validators import load_market_snapshots_csv

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "market_snapshots.csv"
            path.write_text(
                "\n".join(
                    [
                        "ticker,asset_type,as_of,available_at,source,close_price,volume",
                        "NVDA,equity,2026-05-14T10:00:00+00:00,,manual,900,1000000",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "available_at"):
                load_market_snapshots_csv(path)

    def test_evidence_file_import_requires_provenance_and_rejects_missing_license(self) -> None:
        from ai_infra_fund_core.local_inputs.csv_validators import load_evidence_files

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "nvda-note.md").write_text("NVDA accelerator supply remains tight.", encoding="utf-8")
            index = root / "evidence_index.csv"
            index.write_text(
                "\n".join(
                    [
                        "file_path,source_uri,license_label,data_class,tickers,themes,title",
                        "nvda-note.md,file://local/nvda-note.md,,private_research,NVDA,ai_accelerators,Local note",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "license_label"):
                load_evidence_files(index, root)

    def test_evidence_file_import_marks_private_research_local_only(self) -> None:
        from ai_infra_fund_core.local_inputs.csv_validators import load_evidence_files

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "nvda-note.md").write_text("NVDA accelerator supply remains tight.", encoding="utf-8")
            index = root / "evidence_index.csv"
            index.write_text(
                "\n".join(
                    [
                        "file_path,source_uri,license_label,data_class,tickers,themes,title",
                        "nvda-note.md,file://local/nvda-note.md,user_private,private_research,NVDA,ai_accelerators,Local note",
                    ]
                ),
                encoding="utf-8",
            )

            evidence = load_evidence_files(index, root)

        self.assertEqual(1, len(evidence))
        self.assertTrue(evidence[0].local_only)
        self.assertEqual("private_research", evidence[0].data_class.value)
        self.assertEqual(("NVDA",), evidence[0].tickers)
        self.assertEqual("NVDA accelerator supply remains tight.", evidence[0].content)

    def test_sensitive_schwab_pdf_is_quarantined_before_evidence_import(self) -> None:
        from ai_infra_fund_core.local_inputs.csv_validators import load_evidence_files
        from ai_infra_fund_core.local_inputs.file_validators import validate_local_file_candidate

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sensitive_pdf = root / "schwab-routing-instructions.pdf"
            sensitive_pdf.write_bytes(b"%PDF-1.7\nSchwab routing number and account transfer instructions")

            validation = validate_local_file_candidate(sensitive_pdf)

            self.assertEqual("quarantined", validation.status.value)
            self.assertIn("sensitive", validation.reason)

            index = root / "evidence_index.csv"
            index.write_text(
                "\n".join(
                    [
                        "file_path,source_uri,license_label,data_class,tickers,themes,title",
                        "schwab-routing-instructions.pdf,file://local/schwab-routing-instructions.pdf,user_private,private_research,NVDA,ai_accelerators,Sensitive PDF",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "quarantined"):
                load_evidence_files(index, root)

    def test_ai_equity_watchlist_yaml_is_config_driven_and_validated(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import load_ai_equity_watchlist

        watchlist = load_ai_equity_watchlist(ROOT / "config" / "ai_equity_watchlist.yaml")

        tickers = tuple(item.ticker for item in watchlist.entries)
        self.assertIn("NVDA", tickers)
        self.assertIn("MSFT", tickers)
        for entry in watchlist.entries:
            self.assertTrue(entry.company_name)
            self.assertGreaterEqual(len(entry.themes), 1)
            self.assertGreaterEqual(len(entry.sector_tags), 1)
            self.assertIn(entry.priority, {"critical", "high", "medium", "low"})

    def test_ai_equity_watchlist_validation_rejects_missing_required_fields(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import load_ai_equity_watchlist

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchlist.yaml"
            path.write_text(
                "\n".join(
                    [
                        "version: 1",
                        "entries:",
                        "  - ticker: NVDA",
                        "    company_name: NVIDIA",
                        "    themes: []",
                        "    sector_tags: [semiconductors]",
                        "    priority: high",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "themes"):
                load_ai_equity_watchlist(path)


if __name__ == "__main__":
    unittest.main()
