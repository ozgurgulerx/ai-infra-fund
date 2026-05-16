import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { AppShell } from "../components/app-shell";

type MarketEvent = {
  event_id: string;
  event_type: string;
  source_evidence_ids: string[];
  tickers: string[];
  companies: string[];
  themes: string[];
  catalyst: string;
  ai_relevance: string;
  direction: string;
  time_horizon: string;
  confidence: string;
  occurred_at: string;
  available_at: string;
  content_hash: string;
  extracted_by_model_run_id: string;
  review_status: string;
};

type SegmentImpact = {
  segment_id: string;
  segment_name: string;
  primary_tickers: string[];
  linked_event_ids: string[];
  impact_direction: string;
  impact_summary: string;
};

type EquityImpactAssessment = {
  ticker: string;
  company: string;
  linked_event_ids: string[];
  assessment: string;
  watch_items: string[];
  advisory_implication: string;
};

type RiskRegimeUpdate = {
  regime_id: string;
  risk_type: string;
  status: string;
  linked_event_ids: string[];
  summary: string;
  portfolio_monitoring_note: string;
};

type AnalystBrief = {
  brief_id: string;
  as_of: string;
  title: string;
  advisory_label: string;
  executive_summary: string;
  highest_conviction_theme_updates: {
    theme: string;
    supporting_event_ids: string[];
    brief_note: string;
  }[];
  ticker_focus_list: {
    ticker: string;
    reason: string;
  }[];
  open_questions: string[];
  next_review_triggers: string[];
};

type SituationalAwarenessBrief = {
  AnalystBrief: AnalystBrief;
  MarketEvents: MarketEvent[];
  SegmentImpacts: SegmentImpact[];
  EquityImpactAssessments: EquityImpactAssessment[];
  RiskRegimeUpdates: RiskRegimeUpdate[];
};

const ANALYST_ACTIONS = ["watch", "accumulate", "hold", "trim", "avoid"];

const actionByTicker: Record<string, string> = {
  ANET: "accumulate",
  CEG: "hold",
  MSFT: "trim",
  MU: "watch",
  NVDA: "watch",
  TSM: "accumulate",
  VRT: "accumulate",
};

function loadBrief(): SituationalAwarenessBrief {
  const candidates = [
    join(
      process.cwd(),
      "../../docs/mock_data/situational_awareness_brief.example.json",
    ),
    join(process.cwd(), "docs/mock_data/situational_awareness_brief.example.json"),
  ];
  const mockPath = candidates.find((candidate) => existsSync(candidate));
  if (!mockPath) {
    throw new Error("Static situational awareness brief mock data was not found");
  }
  return JSON.parse(readFileSync(mockPath, "utf8")) as SituationalAwarenessBrief;
}

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

function labelize(value: string): string {
  return value.replaceAll("_", " ");
}

function shortId(value: string): string {
  if (value.length <= 28) return value;
  return `${value.slice(0, 18)}...${value.slice(-7)}`;
}

function evidenceForEvents(events: MarketEvent[], eventIds: string[]): string[] {
  const ids = eventIds.flatMap(
    (eventId) =>
      events.find((event) => event.event_id === eventId)?.source_evidence_ids ??
      [],
  );
  return Array.from(new Set(ids));
}

function invalidationFromWatchItems(items: string[]): string {
  if (items.length === 0) {
    return "Invalidate if linked catalyst evidence weakens without replacement support.";
  }
  return `Invalidate if ${items[0].toLowerCase()} turns negative while fresh evidence fails to offset it.`;
}

function riskFlagsFromWatchItems(items: string[]): string[] {
  return items.length === 0 ? ["evidence freshness"] : items;
}

function EventEvidence({ ids }: { ids: string[] }) {
  return (
    <div className="brief-evidence-list">
      {ids.map((id) => (
        <code key={id}>{shortId(id)}</code>
      ))}
    </div>
  );
}

function EmptyBriefState() {
  return (
    <section className="section-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Static mock</p>
          <h2>No validated brief</h2>
        </div>
      </div>
      <p className="panel-note">
        No validated brief for this date. Evidence ingestion or the analyst run
        has not produced an audited brief yet.
      </p>
    </section>
  );
}

export default function DailyBriefPage() {
  const brief = loadBrief();
  const analystBrief = brief.AnalystBrief;
  const topEvents = brief.MarketEvents.slice(0, 5);
  const focusTickers = analystBrief.ticker_focus_list.map((item) => item.ticker);

  if (!analystBrief || brief.MarketEvents.length === 0) {
    return (
      <div className="control-room-shell">
        <AppShell
          eyebrow="Daily Brief"
          title="AI Infrastructure Situational Awareness Brief"
        >
          <EmptyBriefState />
        </AppShell>
      </div>
    );
  }

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Daily Brief"
        title="AI Infrastructure Situational Awareness Brief"
        aside={
          <div className="advisory-badge">
            {labelize(analystBrief.advisory_label)}
          </div>
        }
      >
        <section className="brief-command-strip" aria-label="Brief overview">
          <div className="brief-command-card brief-command-card-wide">
            <span>As of</span>
            <strong>{formatTimestamp(analystBrief.as_of)}</strong>
            <small>{analystBrief.brief_id}</small>
          </div>
          <div className="brief-command-card">
            <span>MarketEvents</span>
            <strong>{brief.MarketEvents.length}</strong>
            <small>all linked to evidence</small>
          </div>
          <div className="brief-command-card">
            <span>Segments</span>
            <strong>{brief.SegmentImpacts.length}</strong>
            <small>impact mapped</small>
          </div>
          <div className="brief-command-card">
            <span>Risk regimes</span>
            <strong>{brief.RiskRegimeUpdates.length}</strong>
            <small>with invalidation watch</small>
          </div>
        </section>

        <section className="brief-analyst-actions" aria-label="Analyst actions">
          <span>Advisory action vocabulary</span>
          <div>
            {ANALYST_ACTIONS.map((action) => (
              <strong key={action}>{action}</strong>
            ))}
          </div>
        </section>

        <div className="brief-layout">
          <section className="section-panel brief-summary-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Executive Summary</p>
                <h2>{analystBrief.title}</h2>
              </div>
              <span className="readonly-label">Static mock JSON</span>
            </div>
            <p className="brief-summary-copy">
              {analystBrief.executive_summary}
            </p>
            <div className="brief-theme-stack">
              {analystBrief.highest_conviction_theme_updates.map((theme) => (
                <article className="brief-theme-card" key={theme.theme}>
                  <strong>{theme.theme}</strong>
                  <p>{theme.brief_note}</p>
                  <EventEvidence ids={theme.supporting_event_ids} />
                </article>
              ))}
            </div>
          </section>

          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Focus List</p>
                <h2>Ticker thesis queue</h2>
              </div>
              <span className="readonly-label">{focusTickers.length} names</span>
            </div>
            <div className="brief-focus-list">
              {analystBrief.ticker_focus_list.map((item) => (
                <div className="brief-focus-row" key={item.ticker}>
                  <strong>{item.ticker}</strong>
                  <span>{item.reason}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        <section className="section-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Top MarketEvents</p>
              <h2>Catalysts with evidence references</h2>
            </div>
            <span className="readonly-label">Occurred / available tracked</span>
          </div>
          <div className="brief-event-grid">
            {topEvents.map((event) => (
              <article className="brief-event-card" key={event.event_id}>
                <div className="brief-card-header">
                  <span>{labelize(event.event_type)}</span>
                  <strong>{event.confidence}</strong>
                </div>
                <h3>{event.catalyst}</h3>
                <p>{event.ai_relevance}</p>
                <div className="brief-meta-grid">
                  <span>Direction</span>
                  <strong>{labelize(event.direction)}</strong>
                  <span>Horizon</span>
                  <strong>{labelize(event.time_horizon)}</strong>
                  <span>Available</span>
                  <strong>{formatTimestamp(event.available_at)}</strong>
                </div>
                <div className="brief-chip-row">
                  {event.tickers.slice(0, 8).map((ticker) => (
                    <span className="brief-chip" key={ticker}>
                      {ticker}
                    </span>
                  ))}
                </div>
                <div className="brief-evidence-block">
                  <span>Evidence</span>
                  <EventEvidence ids={event.source_evidence_ids} />
                </div>
              </article>
            ))}
          </div>
        </section>

        <div className="brief-layout">
          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">SegmentImpact</p>
                <h2>AI infrastructure propagation map</h2>
              </div>
            </div>
            <div className="brief-segment-list">
              {brief.SegmentImpacts.map((segment) => (
                <article className="brief-segment-row" key={segment.segment_id}>
                  <div>
                    <strong>{segment.segment_name}</strong>
                    <span>{labelize(segment.impact_direction)}</span>
                  </div>
                  <p>{segment.impact_summary}</p>
                  <div className="brief-chip-row">
                    {segment.primary_tickers.map((ticker) => (
                      <span className="brief-chip" key={ticker}>
                        {ticker}
                      </span>
                    ))}
                  </div>
                  <EventEvidence ids={segment.linked_event_ids} />
                </article>
              ))}
            </div>
          </section>

          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">RiskRegimeUpdate</p>
                <h2>Systemic risk monitor</h2>
              </div>
            </div>
            <div className="brief-risk-stack">
              {brief.RiskRegimeUpdates.map((risk) => (
                <article className="brief-risk-card" key={risk.regime_id}>
                  <div className="brief-card-header">
                    <span>{labelize(risk.risk_type)}</span>
                    <strong>{risk.status}</strong>
                  </div>
                  <p>{risk.summary}</p>
                  <div className="brief-invalidation">
                    <strong>Invalidation / relief watch</strong>
                    <span>{risk.portfolio_monitoring_note}</span>
                  </div>
                  <EventEvidence ids={risk.linked_event_ids} />
                </article>
              ))}
            </div>
          </section>
        </div>

        <section className="section-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">EquityImpactAssessment</p>
              <h2>Ticker thesis clarity, risk, and invalidation</h2>
            </div>
            <span className="readonly-label">
              No execution controls · research only
            </span>
          </div>
          <div className="brief-equity-grid">
            {brief.EquityImpactAssessments.map((assessment) => {
              const evidenceIds = evidenceForEvents(
                brief.MarketEvents,
                assessment.linked_event_ids,
              );
              const riskFlags = riskFlagsFromWatchItems(assessment.watch_items);
              return (
                <article className="brief-equity-card" key={assessment.ticker}>
                  <div className="brief-equity-title">
                    <div>
                      <strong>{assessment.ticker}</strong>
                      <span>{assessment.company}</span>
                    </div>
                    <span className="brief-action-pill">
                      {actionByTicker[assessment.ticker] ?? "watch"}
                    </span>
                  </div>
                  <p>{assessment.assessment}</p>
                  <div className="brief-field-stack">
                    <div>
                      <strong>Risk flags</strong>
                      <div className="brief-chip-row">
                        {riskFlags.map((flag) => (
                          <span className="brief-chip brief-chip-risk" key={flag}>
                            {flag}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="brief-invalidation">
                      <strong>Invalidation condition</strong>
                      <span>
                        {invalidationFromWatchItems(assessment.watch_items)}
                      </span>
                    </div>
                    <div>
                      <strong>Evidence references</strong>
                      <EventEvidence ids={evidenceIds} />
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="section-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">OutcomeJournal Prep</p>
              <h2>Open questions and next review triggers</h2>
            </div>
          </div>
          <div className="brief-review-grid">
            <div>
              <h3>Open questions</h3>
              <ul>
                {analystBrief.open_questions.map((question) => (
                  <li key={question}>{question}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3>Next review triggers</h3>
              <ul>
                {analystBrief.next_review_triggers.map((trigger) => (
                  <li key={trigger}>{trigger}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      </AppShell>
    </div>
  );
}
