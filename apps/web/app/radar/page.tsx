import { AppShell } from "../../components/app-shell";
import { RiskFlags } from "../../components/daily-cockpit/evidence-pills";
import {
  AdvisoryTable,
  EvidenceDrawer,
  SectionCard,
  StatusChip,
} from "../../components/workstation";
import { mockWorkstationData } from "../../lib/situational-awareness/mock-workstation-data";

export default function RadarPage() {
  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Market Radar"
        title="Live Market / Sentiment Radar"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <SectionCard
          badge={<StatusChip label="static mock feed" tone="neutral" />}
          eyebrow="Classified intelligence"
          title="Compact event feed"
          subtitle="event feed, sentiment, urgency, relevance, and freshness"
        >
          <div className="compact-list">
            {mockWorkstationData.marketEvents.map((event) => (
              <article className="wave2-radar-row compact-card" key={event.eventId}>
                <div className="wave2-radar-score">
                  <strong>{event.reviewPriority}</strong>
                  <span>review priority</span>
                </div>
                <div>
                  <div className="wave2-card-kicker">
                    <span>{event.eventType.replaceAll("_", " ")}</span>
                    <strong>{event.sentimentDirection}</strong>
                  </div>
                  <h3>{event.catalyst}</h3>
                  <p>{event.aiRelevance}</p>
                  <div className="wave2-mini-columns">
                    <span>Affected segment: {event.segment}</span>
                    <span>Materiality: {event.materiality}</span>
                    <span>Market reaction placeholder/mock: watch price distance vs. levels</span>
                    <span>
                      correlation/sector movement notes:{" "}
                      {mockWorkstationData.correlationExposures[0].note}
                    </span>
                  </div>
                  <div className="wave2-chip-row">
                    {event.tickers.map((ticker) => (
                      <span className="wave2-chip" key={`${event.eventId}-${ticker}`}>
                        {ticker}
                      </span>
                    ))}
                  </div>
                  <RiskFlags flags={event.riskFlags} />
                </div>
              </article>
            ))}
          </div>
          <details className="compact-collapse">
            <summary>Collapsed noisy low-confidence items</summary>
            <p className="wave2-muted">
              Low-confidence monitor-only items remain available after review
              priority and evidence checks.
            </p>
          </details>
        </SectionCard>

        <SectionCard
          eyebrow="LLM scout notes"
          title="Interpretation layer, not raw internet feed"
        >
          <AdvisoryTable
            columns={["Role", "Scope", "Confidence", "Note"]}
            rows={mockWorkstationData.llmAnalystNotes.map((note) => ({
              id: note.noteId,
              cells: [note.role, note.tickerOrSegment, note.confidence, note.summary],
            }))}
          />
          <EvidenceDrawer
            ids={[
              ...mockWorkstationData.marketEvents.flatMap((event) => event.evidenceIds),
              ...mockWorkstationData.llmAnalystNotes.flatMap((note) => note.evidenceIds),
            ]}
          />
        </SectionCard>
      </AppShell>
    </div>
  );
}
