"use client";

import { useEffect, useState } from "react";
import { SectionPanel } from "./section-panel";
import { EmptyState } from "./empty-state";
import { fetchPortfolioSummary, type PortfolioSummary } from "../lib/api";

function formatMoney(value: string | null | undefined): string {
  if (!value) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(2)}`;
}

function formatWeight(value: string | null | undefined): string {
  if (!value) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  return `${(n * 100).toFixed(1)}%`;
}

export function PortfolioTile() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const result = await fetchPortfolioSummary();
      if (!cancelled) setSummary(result);
    }
    void load();
    const id = window.setInterval(load, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const empty =
    !summary || summary.status === "empty" || summary.positions.length === 0;

  return (
    <SectionPanel
      eyebrow="Portfolio"
      title="Latest snapshot"
      aside={
        <a className="readonly-label" href="/portfolio">
          → details
        </a>
      }
    >
      {empty ? (
        <EmptyState
          reason="No portfolio snapshot yet. Import positions or record manual trades to seed the portfolio."
          ctaLabel="Open trade journal"
          ctaHref="/trade-journal"
        />
      ) : (
        <table className="portfolio-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Qty</th>
              <th>Price</th>
              <th>Weight</th>
              <th>P&amp;L</th>
            </tr>
          </thead>
          <tbody>
            {summary!.positions.slice(0, 8).map((p) => (
              <tr key={p.ticker}>
                <td className="portfolio-ticker">{p.ticker}</td>
                <td>{p.quantity}</td>
                <td>{formatMoney(p.market_price)}</td>
                <td>{formatWeight(p.portfolio_weight)}</td>
                <td>{formatMoney(p.unrealized_pnl)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={2}>Cash</td>
              <td colSpan={3}>{formatMoney(summary!.cash_value)}</td>
            </tr>
            <tr>
              <td colSpan={2}>
                <strong>Total</strong>
              </td>
              <td colSpan={3}>
                <strong>{formatMoney(summary!.total_market_value)}</strong>
              </td>
            </tr>
          </tfoot>
        </table>
      )}
    </SectionPanel>
  );
}
