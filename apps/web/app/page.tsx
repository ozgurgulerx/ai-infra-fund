import { headers } from "next/headers";

import { AppShell } from "../components/app-shell";

export const dynamic = "force-dynamic";
export const revalidate = 0;

type MarketEvent = {
  event_id: string;
  event_type: string;
  source_evidence_ids?: string[];
  evidence_ids?: string[];
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
  extracted_by_model_run_id: string | null;
  review_status: string;
};

type SegmentImpact = {
  segment_id: string;
  segment_name: string;
  primary_tickers: string[];
  second_order_tickers?: string[];
  linked_event_ids: string[];
  impact_direction: string;
  impact_summary: string;
  evidence_ids?: string[];
};

type EquityImpactAssessment = {
  assessment_id?: string;
  ticker: string;
  company: string;
  linked_event_ids: string[];
  assessment: string;
  watch_items: string[];
  advisory_implication: string;
  risk_flags: string[];
  invalidation: string;
  evidence_ids: string[];
};

type RiskRegimeUpdate = {
  regime_id: string;
  risk_type: string;
  status: string;
  linked_event_ids: string[];
  evidence_ids: string[];
  summary: string;
  portfolio_monitoring_note: string;
};

type TradingAdvisory = {
  advisory_id: string;
  ticker: string;
  advisory_label: string;
  analyst_action: string;
  advisory_summary: string;
  evidence_ids: string[];
  model_run_ids: string[];
  signal_bundle_id: string | null;
  target_weights_id: string | null;
  deterministic_checks: string[];
};

type AnalystBriefPayload = {
  highest_conviction_theme_updates?: {
    theme: string;
    supporting_event_ids: string[];
    brief_note: string;
  }[];
  ticker_focus_list?: {
    ticker: string;
    reason: string;
  }[];
  open_questions?: string[];
  next_review_triggers?: string[];
};

type AnalystBrief = {
  brief_id: string;
  as_of: string;
  title: string;
  advisory_label: string;
  executive_summary: string;
  market_event_ids: string[];
  segment_impact_ids: string[];
  trading_advisory_ids: string[];
  model_run_ids: string[];
  payload?: AnalystBriefPayload;
};

type AnalystBriefReadModel = {
  status: "available" | "empty" | "degraded" | string;
  advisory_label: string;
  detail?: string;
  brief?: AnalystBrief;
  market_events?: MarketEvent[];
  segment_impacts?: SegmentImpact[];
  equity_impact_assessments?: EquityImpactAssessment[];
  risk_regime_updates?: RiskRegimeUpdate[];
  trading_advisories?: TradingAdvisory[];
};

const ANALYST_ACTIONS = ["watch", "accumulate", "hold", "trim", "avoid"];
const ANALYST_BRIEF_ENDPOINT = "/internal/analyst-brief/latest";

async function fetchAnalystBrief(): Promise<AnalystBriefReadModel> {
  try {
    const headerList = await headers();
    const host = headerList.get("host") ?? "localhost:3000";
    const proto = headerList.get("x-forwarded-proto") ?? "http";
    const response = await fetch(
      `${proto}://${host}/api/backend${ANALYST_BRIEF_ENDPOINT}`,
      { cache: "no-store", method: "GET" },
    );
    const payload = await readAnalystBriefPayload(response);

    if (!response.ok || !payload.data) {
      return degradedAnalystBrief(
        `API-backed analyst brief unavailable: HTTP ${response.status}`,
      );
    }

    return payload.data;
  } catch (error) {
    const reason = error instanceof Error ? error.message : "request failed";
    return degradedAnalystBrief(
      `API-backed analyst brief unavailable: ${reason}`,
    );
  }
}

async function readAnalystBriefPayload(
  response: Response,
): Promise<{ data?: AnalystBriefReadModel }> {
  try {
    return (await response.json()) as { data?: AnalystBriefReadModel };
  } catch {
    return {};
  }
}

function degradedAnalystBrief(detail: string): AnalystBriefReadModel {
  return {
    status: "degraded",
    advisory_label: "advisory_only",
    detail,
  };
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

function labelize(value: string | null | undefined): string {
  return (value ?? "review").replaceAll("_", " ").replaceAll("-", " ");
}

function shortId(value: string): string {
  if (value.length <= 28) return value;
  return `${value.slice(0, 18)}...${value.slice(-7)}`;
}

function eventEvidence(event: MarketEvent): string[] {
  return event.source_evidence_ids ?? event.evidence_ids ?? [];
}

function evidenceForEvents(events: MarketEvent[], eventIds: string[]): string[] {
  const ids = eventIds.flatMap(
    (eventId) =>
      eventEvidence(events.find((event) => event.event_id === eventId) ?? ({} as MarketEvent)),
  );
  return Array.from(new Set(ids));
}

function EmptyBriefState({ detail }: { detail?: string }) {
  return (
    <section className="section-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">API-backed analyst brief</p>
          <h2>No validated brief</h2>
        </div>
      </div>
      <p className="panel-note">
        {detail ??
          "The fixture-backed advisory read model has not produced an audited brief yet."}
      </p>
    </section>
  );
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

export default async function DailyBriefPage() {
  const readModel = await fetchAnalystBrief();
  const analystBrief = readModel.brief;
  const marketEvents = readModel.market_events ?? [];
  const segmentImpacts = readModel.segment_impacts ?? [];
  const equityAssessments = readModel.equity_impact_assessments ?? [];
  const riskRegimes = readModel.risk_regime_updates ?? [];
  const tradingAdvisories = readModel.trading_advisories ?? [];
  const briefPayload = analystBrief?.payload ?? {};
  const themeUpdates = briefPayload.highest_conviction_theme_updates ?? [];
  const focusTickers = briefPayload.ticker_focus_list ?? [];
  const openQuestions = briefPayload.open_questions ?? [];
  const reviewTriggers = briefPayload.next_review_triggers ?? [];

  if (!analystBrief || readModel.status !== "available") {
    return (
      <div className="control-room-shell">
        <AppShell
          eyebrow="Daily Brief"
          title="AI Infrastructure Trading Analyst Workstation"
        >
          <EmptyBriefState detail={readModel.detail} />
        </AppShell>
      </div>
    );
  }

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Daily Brief"
        title="AI Infrastructure Trading Analyst Workstation"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <section className="brief-command-strip" aria-label="Brief overview">
          <div className="brief-command-card brief-command-card-wide">
            <span>As of</span>
            <strong>{formatTimestamp(analystBrief.as_of)}</strong>
            <small>{analystBrief.brief_id}</small>
          </div>
          <div className="brief-command-card">
            <span>MarketEvents</span>
            <strong>{marketEvents.length}</strong>
            <small>all linked to evidence</small>
          </div>
          <div className="brief-command-card">
            <span>Segments</span>
            <strong>{segmentImpacts.length}</strong>
            <small>impact mapped</small>
          </div>
          <div className="brief-command-card">
            <span>TradingAdvisory</span>
            <strong>{tradingAdvisories.length}</strong>
            <small>planning only</small>
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
              <span className="readonly-label">API-backed analyst brief</span>
            </div>
            <p className="brief-summary-copy">
              {analystBrief.executive_summary}
            </p>
            <div className="brief-theme-stack">
              {themeUpdates.map((theme) => (
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
              {focusTickers.map((item) => (
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
            {marketEvents.slice(0, 5).map((event) => (
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
                  <EventEvidence ids={eventEvidence(event)} />
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
              {segmentImpacts.map((segment) => (
                <article className="brief-segment-row" key={segment.segment_id}>
                  <div>
                    <strong>{segment.segment_name}</strong>
                    <span>{labelize(segment.impact_direction)}</span>
                  </div>
                  <p>{segment.impact_summary}</p>
                  <div className="brief-chip-row">
                    {[...segment.primary_tickers, ...(segment.second_order_tickers ?? [])]
                      .slice(0, 10)
                      .map((ticker) => (
                        <span className="brief-chip" key={`${segment.segment_id}-${ticker}`}>
                          {ticker}
                        </span>
                      ))}
                  </div>
                  <EventEvidence ids={segment.evidence_ids ?? segment.linked_event_ids} />
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
              {riskRegimes.map((risk) => (
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
                  <EventEvidence ids={risk.evidence_ids} />
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
            {equityAssessments.map((assessment) => {
              const advisory = tradingAdvisories.find(
                (item) => item.ticker === assessment.ticker,
              );
              const evidenceIds =
                assessment.evidence_ids.length > 0
                  ? assessment.evidence_ids
                  : evidenceForEvents(marketEvents, assessment.linked_event_ids);
              return (
                <article
                  className="brief-equity-card"
                  key={assessment.assessment_id ?? assessment.ticker}
                >
                  <div className="brief-equity-title">
                    <div>
                      <strong>{assessment.ticker}</strong>
                      <span>{assessment.company}</span>
                    </div>
                    <span className="brief-action-pill">
                      {advisory?.analyst_action ?? "watch"}
                    </span>
                  </div>
                  <p>{assessment.assessment}</p>
                  <div className="brief-field-stack">
                    <div>
                      <strong>Risk flags</strong>
                      <div className="brief-chip-row">
                        {assessment.risk_flags.map((flag) => (
                          <span className="brief-chip brief-chip-risk" key={flag}>
                            {labelize(flag)}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="brief-invalidation">
                      <strong>Invalidation condition</strong>
                      <span>{assessment.invalidation}</span>
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
              <p className="eyebrow">TradingAdvisory</p>
              <h2>Advisory labels and deterministic trace</h2>
            </div>
            <span className="readonly-label">No broker · no order path</span>
          </div>
          <div className="brief-event-grid">
            {tradingAdvisories.slice(0, 6).map((advisory) => (
              <article className="brief-event-card" key={advisory.advisory_id}>
                <div className="brief-card-header">
                  <span>{advisory.ticker}</span>
                  <strong>{advisory.analyst_action}</strong>
                </div>
                <p>{advisory.advisory_summary}</p>
                <div className="brief-meta-grid">
                  <span>SignalBundle</span>
                  <strong>{shortId(advisory.signal_bundle_id ?? "not linked")}</strong>
                  <span>TargetWeights</span>
                  <strong>{shortId(advisory.target_weights_id ?? "not linked")}</strong>
                </div>
                <EventEvidence ids={advisory.evidence_ids} />
              </article>
            ))}
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
                {openQuestions.map((question) => (
                  <li key={question}>{question}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3>Next review triggers</h3>
              <ul>
                {reviewTriggers.map((trigger) => (
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
