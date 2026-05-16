import { AppShell } from "../../components/app-shell";
import { EvidencePills } from "../../components/daily-cockpit/evidence-pills";
import { TradeEntryForm } from "../../components/trade-entry-form";
import { mockWorkstationData } from "../../lib/situational-awareness/mock-workstation-data";

export default function TradeJournalPage() {
  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Local Journal"
        title="Trade Journal + PnL Review"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <div className="wave2-grid wave2-grid-2">
          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Manual records</p>
                <h2>Manual journal only</h2>
              </div>
              <span className="readonly-label">No broker connection</span>
            </div>
            <TradeEntryForm />
          </section>

          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Mock deterministic review</p>
                <h2>realized/unrealized PnL</h2>
              </div>
              <span className="readonly-label">{mockWorkstationData.pnlSummary.label}</span>
            </div>
            <div className="wave2-metric-grid">
              <div>
                <span>Total</span>
                <strong>{mockWorkstationData.pnlSummary.total}</strong>
              </div>
              {mockWorkstationData.pnlSummary.bySegment.map(([segment, value]) => (
                <div key={segment}>
                  <span>{segment}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
            <p className="panel-note">
              PnL by segment uses static deterministic fixture values for review only.
            </p>
            <EvidencePills ids={mockWorkstationData.pnlSummary.evidenceIds} />
          </section>
        </div>

        <section className="section-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Outcome review</p>
              <h2>Trade history, exit reason, and post-trade LLM review</h2>
            </div>
          </div>
          <div className="wave2-card-grid">
            {mockWorkstationData.journalReviews.map((entry) => (
              <article className="wave2-card" key={entry.journalId}>
                <div className="wave2-card-kicker">
                  <span>{entry.status}</span>
                  <strong>{entry.ticker}</strong>
                </div>
                <h3>{entry.entryExit}</h3>
                <div className="wave2-case-grid">
                  <span>realized/unrealized PnL</span>
                  <p>{entry.realizedUnrealizedPnl}</p>
                  <span>exit reason</span>
                  <p>{entry.exitReason}</p>
                  <span>mistake classification</span>
                  <p>{entry.mistakeClassification}</p>
                  <span>post-trade LLM review</span>
                  <p>{entry.postTradeLlmReview}</p>
                  <span>PnL by segment</span>
                  <p>{entry.segment} · {entry.catalystType}</p>
                </div>
                <EvidencePills ids={entry.evidenceIds} />
              </article>
            ))}
          </div>
        </section>
      </AppShell>
    </div>
  );
}
