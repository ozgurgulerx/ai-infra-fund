import { AppShell } from "../components/app-shell";
import {
  AdvisoryPill,
  EvidencePills,
  RiskFlags,
} from "../components/daily-cockpit/evidence-pills";
import { mockWorkstationData } from "../lib/situational-awareness/mock-workstation-data";

export const dynamic = "force-static";

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

export default function DailyTradingCockpitPage() {
  const data = mockWorkstationData;
  const topEvents = data.marketEvents.slice(0, 4);
  const focusAssessments = data.equityAssessments.slice(0, 5);

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Daily Trading Cockpit"
        title="AI Infrastructure Trading Analyst Workstation"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <section className="wave2-command-strip" aria-label="Daily cockpit status">
          <div className="wave2-command-card wave2-command-card-wide">
            <span>AI infrastructure regime</span>
            <strong>{data.run.regime}</strong>
            <small>{formatTimestamp(data.run.asOf)} · {data.run.runId}</small>
          </div>
          <div className="wave2-command-card">
            <span>MarketEvents</span>
            <strong>{data.marketEvents.length}</strong>
            <small>evidence-linked</small>
          </div>
          <div className="wave2-command-card">
            <span>Suggested actions</span>
            <strong>{data.suggestedActions.length}</strong>
            <small>watch / accumulate / hold / trim / avoid</small>
          </div>
          <div className="wave2-command-card">
            <span>Suppressed</span>
            <strong>{data.run.suppressedAdvisories.length}</strong>
            <small>publication gates visible</small>
          </div>
        </section>

        <div className="wave2-grid wave2-grid-2">
          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Executive summary</p>
                <h2>Daily high-alpha brief with LLM analyst notes</h2>
              </div>
              <span className="readonly-label">Static mock data</span>
            </div>
            <p className="wave2-lede">{data.run.executiveSummary}</p>
            <div className="wave2-note-stack">
              {data.llmAnalystNotes.map((note) => (
                <article className="wave2-note" key={note.noteId}>
                  <span>{note.role}</span>
                  <strong>{note.tickerOrSegment}</strong>
                  <p>{note.summary}</p>
                  <small>confidence {note.confidence} · {note.modelRunId}</small>
                  <EvidencePills ids={note.evidenceIds} />
                </article>
              ))}
            </div>
          </section>

          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Portfolio exposure snapshot</p>
                <h2>Theme exposure under review</h2>
              </div>
              <span className="readonly-label">No transaction surface</span>
            </div>
            <div className="wave2-table wave2-table-4">
              <span>Ticker</span>
              <span>Segment</span>
              <span>Weight</span>
              <span>Action</span>
              {data.portfolioSnapshot.map((position) => (
                <div className="wave2-table-row" key={position.ticker}>
                  <strong>{position.ticker}</strong>
                  <span>{position.segment}</span>
                  <span>{position.weight}</span>
                  <AdvisoryPill label={position.advisoryAction} />
                </div>
              ))}
            </div>
          </section>
        </div>

        <section className="section-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Top MarketEvents</p>
              <h2>Catalyst tape with evidence references</h2>
            </div>
            <span className="readonly-label">classified intelligence</span>
          </div>
          <div className="wave2-card-grid">
            {topEvents.map((event) => (
              <article className="wave2-card" key={event.eventId}>
                <div className="wave2-card-kicker">
                  <span>{event.eventType.replaceAll("_", " ")}</span>
                  <strong>{event.reviewPriority}</strong>
                </div>
                <h3>{event.catalyst}</h3>
                <p>{event.aiRelevance}</p>
                <div className="wave2-meta">
                  <span>Segment</span>
                  <strong>{event.segment}</strong>
                  <span>Sentiment</span>
                  <strong>{event.sentimentDirection}</strong>
                  <span>Materiality</span>
                  <strong>{event.materiality}</strong>
                </div>
                <div className="wave2-chip-row">
                  {event.tickers.map((ticker) => (
                    <span className="wave2-chip" key={`${event.eventId}-${ticker}`}>
                      {ticker}
                    </span>
                  ))}
                </div>
                <EvidencePills ids={event.evidenceIds} />
              </article>
            ))}
          </div>
        </section>

        <div className="wave2-grid wave2-grid-2">
          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Segment impact snapshot</p>
                <h2>Bottlenecks and beneficiaries</h2>
              </div>
            </div>
            <div className="wave2-stack">
              {data.segmentImpacts.slice(0, 5).map((segment) => (
                <article className="wave2-list-card" key={segment.segmentId}>
                  <div>
                    <strong>{segment.segmentName}</strong>
                    <AdvisoryPill label={`${segment.status} / ${segment.momentum}`} />
                  </div>
                  <p>{segment.latestCatalyst}</p>
                  <div className="wave2-mini-columns">
                    <span>First-order: {segment.firstOrderBeneficiaries.join(", ")}</span>
                    <span>Second-order: {segment.secondOrderBeneficiaries.join(", ")}</span>
                  </div>
                  <RiskFlags flags={segment.riskFlags} />
                  <EvidencePills ids={segment.evidenceIds} />
                </article>
              ))}
            </div>
          </section>

          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Risk regime updates</p>
                <h2>Invalidation watchlist</h2>
              </div>
            </div>
            <div className="wave2-stack">
              {data.riskRegimes.map((risk) => (
                <article className="wave2-list-card" key={risk.regimeId}>
                  <div>
                    <strong>{risk.riskType}</strong>
                    <AdvisoryPill label={risk.status} />
                  </div>
                  <p>{risk.summary}</p>
                  <div className="wave2-invalidation">
                    <strong>Relief / invalidation condition</strong>
                    <span>{risk.reliefCondition}</span>
                  </div>
                  <EvidencePills ids={risk.evidenceIds} />
                </article>
              ))}
            </div>
          </section>
        </div>

        <section className="section-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Equity impact assessments</p>
              <h2>Ticker thesis, risk, and invalidation</h2>
            </div>
            <span className="readonly-label">planning guidance only</span>
          </div>
          <div className="wave2-card-grid">
            {focusAssessments.map((assessment) => (
              <article className="wave2-card" key={assessment.ticker}>
                <div className="wave2-equity-title">
                  <div>
                    <strong>{assessment.ticker}</strong>
                    <span>{assessment.company}</span>
                  </div>
                  <AdvisoryPill label={assessment.advisoryImplication} />
                </div>
                <p>{assessment.currentThesis}</p>
                <div className="wave2-case-grid">
                  <span>Bull case</span>
                  <p>{assessment.bullCase}</p>
                  <span>Bear case</span>
                  <p>{assessment.bearCase}</p>
                </div>
                <RiskFlags flags={assessment.riskFlags} />
                <div className="wave2-invalidation">
                  <strong>Invalidation</strong>
                  <span>{assessment.invalidationCondition}</span>
                </div>
                <EvidencePills ids={assessment.evidenceIds} />
              </article>
            ))}
          </div>
        </section>

        <div className="wave2-grid wave2-grid-2">
          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Suggested actions</p>
                <h2>Advisory labels and review prompts</h2>
              </div>
            </div>
            <div className="wave2-stack">
              {data.suggestedActions.map((action) => (
                <article className="wave2-list-card" key={action.actionId}>
                  <div>
                    <strong>{action.ticker}</strong>
                    <AdvisoryPill label={action.advisoryLabel} />
                  </div>
                  <p>{action.analystAction}</p>
                  <RiskFlags flags={action.riskFlags} />
                  <div className="wave2-invalidation">
                    <strong>Invalidation</strong>
                    <span>{action.invalidationCondition}</span>
                  </div>
                  <EvidencePills ids={action.evidenceIds} />
                </article>
              ))}
            </div>
          </section>

          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Open trade plans</p>
                <h2>Manual planning queue</h2>
              </div>
              <span className="readonly-label">local journal only</span>
            </div>
            <div className="wave2-stack">
              {data.openTradePlans.map((plan) => (
                <article className="wave2-list-card" key={plan.tradePlanId}>
                  <div>
                    <strong>{plan.ticker}</strong>
                    <AdvisoryPill label={plan.advisoryAction} />
                  </div>
                  <p>{plan.thesis}</p>
                  <div className="wave2-mini-columns">
                    <span>Entry: {plan.entryLevel}</span>
                    <span>Invalidation: {plan.stopInvalidation}</span>
                  </div>
                  <EvidencePills ids={plan.evidenceIds} />
                </article>
              ))}
            </div>
          </section>
        </div>
      </AppShell>
    </div>
  );
}
