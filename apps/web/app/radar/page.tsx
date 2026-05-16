import { AppShell } from "../../components/app-shell";
import { EvidencePills, RiskFlags } from "../../components/daily-cockpit/evidence-pills";
import { mockWorkstationData } from "../../lib/situational-awareness/mock-workstation-data";

export default function RadarPage() {
  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Market Radar"
        title="Live Market / Sentiment Radar"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <section className="section-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Classified intelligence</p>
              <h2>Event feed, sentiment, urgency, and evidence</h2>
            </div>
            <span className="readonly-label">static mock feed</span>
          </div>

          <div className="wave2-radar-grid">
            {mockWorkstationData.marketEvents.map((event) => (
              <article className="wave2-radar-row" key={event.eventId}>
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
                  <EvidencePills ids={event.evidenceIds} />
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="section-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">LLM scout notes</p>
              <h2>Interpretation layer, not raw internet feed</h2>
            </div>
          </div>
          <div className="wave2-card-grid">
            {mockWorkstationData.llmAnalystNotes.map((note) => (
              <article className="wave2-card" key={note.noteId}>
                <div className="wave2-card-kicker">
                  <span>{note.role}</span>
                  <strong>{note.confidence}</strong>
                </div>
                <h3>{note.tickerOrSegment}</h3>
                <p>{note.summary}</p>
                <small>{note.modelRunId}</small>
                <EvidencePills ids={note.evidenceIds} />
              </article>
            ))}
          </div>
        </section>
      </AppShell>
    </div>
  );
}
