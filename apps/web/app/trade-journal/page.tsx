import Link from "next/link";

import { AppShell } from "../../components/app-shell";
import { TradeEntryForm } from "../../components/trade-entry-form";
import {
  AdvisoryTable,
  EvidenceDrawer,
  MetricTile,
  SectionCard,
  StatusChip,
} from "../../components/workstation";
import {
  formatTimestamp,
  list,
  readLatestPortfolioExposure,
  readTradeJournalEntries,
} from "../../lib/advisory/workstation-data";
import { mockWorkstationData } from "../../lib/situational-awareness/mock-workstation-data";

export const dynamic = "force-dynamic";

export default async function TradeJournalPage() {
  const [portfolioPayload, journalPayload] = await Promise.all([
    readLatestPortfolioExposure(),
    readTradeJournalEntries(),
  ]);
  const snapshot = portfolioPayload.snapshot;
  const positions = snapshot?.positions ?? [];
  const entries = journalPayload.entries ?? [];

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Local Journal"
        title="Trade Journal + PnL Review"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <div className="workstation-grid workstation-grid-2">
          <SectionCard
            badge={<StatusChip label="No broker connection" tone="neutral" />}
            eyebrow="Manual records"
            title="Manual journal only"
            subtitle="Journal-only record capture. External account connections remain disabled."
          >
            <TradeEntryForm />
          </SectionCard>

          <SectionCard
            badge={<StatusChip label={mockWorkstationData.pnlSummary.label} tone="neutral" />}
            eyebrow="Deterministic review"
            title="realized/unrealized PnL"
            subtitle="PnL by segment remains deterministic and journal-backed."
          >
            <div className="summary-strip summary-strip-3">
              <MetricTile label="Total" value={mockWorkstationData.pnlSummary.total} />
              {mockWorkstationData.pnlSummary.bySegment.slice(0, 2).map(([segment, value]) => (
                <MetricTile key={segment} label={segment} value={value} />
              ))}
            </div>
            <p className="panel-note">
              PnL calculations are never owned by LLM output.
            </p>
          </SectionCard>
        </div>

        <SectionCard
          eyebrow="Portfolio context"
          title="Current portfolio alongside journal"
          subtitle="Detailed exposure helps outcome review without creating an execution surface."
          badge={<StatusChip label={portfolioPayload.status ?? "degraded"} tone="review" />}
        >
          <div className="summary-strip summary-strip-3">
            <MetricTile label="Portfolio value" value={snapshot?.total_market_value ?? "n/a"} />
            <MetricTile label="Gross equity" value={snapshot?.gross_equity_exposure ?? "n/a"} />
            <MetricTile label="As of" value={formatTimestamp(snapshot?.as_of)} />
          </div>
          <AdvisoryTable
            columns={["Ticker", "Weight", "PnL", "Risk flags", "Plan"]}
            density="compact"
            emptyLabel="No portfolio positions available."
            rows={positions.map((position) => ({
              id: position.ticker ?? position.company ?? "position",
              cells: [
                <span className="table-main" key="ticker">
                  <Link className="ticker-link" href={`/ticker/${position.ticker ?? "NVDA"}`}>
                    {position.ticker ?? "Ticker"}
                  </Link>
                  <small>{position.company ?? "Company pending"}</small>
                </span>,
                position.portfolio_weight ?? position.portfolio_weight_pct ?? "n/a",
                position.unrealized_pnl ?? "not calculated",
                list(position.risk_flags).join(", ") || "none",
                position.open_trade_plan_id ?? "manual review pending",
              ],
            }))}
          />
        </SectionCard>

        <SectionCard
          eyebrow="Outcome review"
          title="Trade history, exit reason, and post-trade LLM review"
          subtitle="Post-trade LLM review can critique and explain; deterministic journal/PnL remains authoritative."
        >
          <AdvisoryTable
            columns={["Ticker", "Status", "realized/unrealized PnL", "Exit reason", "post-trade LLM review"]}
            density="compact"
            rows={[
              ...entries.map((entry) => ({
                id: entry.trade_id ?? `${entry.ticker}-${entry.trade_date}`,
                cells: [
                  <strong key="ticker">{entry.ticker ?? "Ticker"}</strong>,
                  entry.status ?? "journaled",
                  "deterministic PnL pending",
                  "manual journal entry",
                  entry.notes ?? "Post-trade review pending.",
                ],
              })),
              ...mockWorkstationData.journalReviews.map((entry) => ({
                id: entry.journalId,
                cells: [
                  <strong key="ticker">{entry.ticker}</strong>,
                  entry.status,
                  entry.realizedUnrealizedPnl,
                  entry.exitReason,
                  entry.postTradeLlmReview,
                ],
              })),
            ]}
          />
          <EvidenceDrawer
            ids={[
              ...mockWorkstationData.pnlSummary.evidenceIds,
              ...mockWorkstationData.journalReviews.flatMap((entry) => entry.evidenceIds),
            ]}
          />
        </SectionCard>
      </AppShell>
    </div>
  );
}
