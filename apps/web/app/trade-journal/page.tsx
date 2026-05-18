import { AppShell } from "../../components/app-shell";
import { TradeEntryForm } from "../../components/trade-entry-form";
import {
  AdvisoryTable,
  EvidenceDrawer,
  MetricTile,
  SectionCard,
  StatusChip,
} from "../../components/workstation";
import { mockWorkstationData } from "../../lib/situational-awareness/mock-workstation-data";

export default function TradeJournalPage() {
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
          >
            <TradeEntryForm />
          </SectionCard>

          <SectionCard
            badge={<StatusChip label={mockWorkstationData.pnlSummary.label} tone="neutral" />}
            eyebrow="Mock deterministic review"
            title="realized/unrealized PnL"
          >
            <div className="summary-strip summary-strip-3">
              <MetricTile label="Total" value={mockWorkstationData.pnlSummary.total} />
              {mockWorkstationData.pnlSummary.bySegment.map(([segment, value]) => (
                <MetricTile key={segment} label={segment} value={value} />
              ))}
            </div>
            <p className="panel-note">
              PnL by segment uses static deterministic fixture values for review only.
            </p>
          </SectionCard>
        </div>

        <SectionCard
          eyebrow="Outcome review"
          title="Trade history, exit reason, and post-trade LLM review"
        >
          <AdvisoryTable
            columns={["Ticker", "Status", "realized/unrealized PnL", "Exit reason", "post-trade LLM review"]}
            rows={mockWorkstationData.journalReviews.map((entry) => ({
              id: entry.journalId,
              cells: [
                <strong key="ticker">{entry.ticker}</strong>,
                entry.status,
                entry.realizedUnrealizedPnl,
                entry.exitReason,
                entry.postTradeLlmReview,
              ],
            }))}
          />
          <p className="panel-note">
            PnL by segment remains deterministic and journal-backed.
          </p>
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
