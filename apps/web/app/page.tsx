import { AppShell } from "../components/app-shell";
import {
  AdvisoryPill,
  EvidencePills,
  RiskFlags,
} from "../components/daily-cockpit/evidence-pills";

export const dynamic = "force-dynamic";

type ApiEnvelope<TData> = {
  data?: TData;
  error?: { code?: string; message?: string };
};

type SourceSignal = {
  signal_id?: string;
  title?: string;
  tickers?: string[];
  themes?: string[];
  evidence_ids?: string[];
  confidence?: string | number;
  review_status?: string;
};

type MarketEvent = {
  event_id?: string;
  event_type?: string;
  tickers?: string[];
  catalyst?: string;
  ai_relevance?: string;
  direction?: string;
  time_horizon?: string;
  confidence?: string | number;
  available_at?: string | null;
  source_evidence_ids?: string[];
  evidence_ids?: string[];
  review_status?: string;
};

type SegmentImpact = {
  segment_id?: string;
  segment_name?: string;
  primary_tickers?: string[];
  second_order_tickers?: string[];
  impact_direction?: string;
  impact_summary?: string;
  evidence_ids?: string[];
  payload?: Record<string, unknown> | null;
};

type EquityImpactAssessment = {
  assessment_id?: string;
  ticker?: string;
  company?: string;
  assessment?: string;
  advisory_implication?: string;
  risk_flags?: string[];
  invalidation?: string;
  evidence_ids?: string[];
  payload?: Record<string, unknown> | null;
};

type RiskRegimeUpdate = {
  regime_id?: string;
  risk_type?: string;
  status?: string;
  summary?: string;
  portfolio_monitoring_note?: string;
  evidence_ids?: string[];
  payload?: Record<string, unknown> | null;
};

type TradingAdvisory = {
  advisory_id?: string;
  ticker?: string;
  advisory_label?: string;
  analyst_action?: string;
  advisory_summary?: string;
  evidence_ids?: string[];
  model_run_ids?: string[];
  deterministic_checks?: string[] | Record<string, unknown>;
  linked_trade_plan_id?: string | null;
  payload?: Record<string, unknown> | null;
};

type AnalystBrief = {
  brief_id?: string;
  as_of?: string | null;
  title?: string;
  advisory_label?: string;
  executive_summary?: string;
  model_run_ids?: string[];
  payload?: Record<string, unknown> | null;
};

type AnalystBriefPayload = {
  status?: string;
  advisory_label?: string;
  detail?: string;
  brief?: AnalystBrief;
  market_events?: MarketEvent[];
  segment_impacts?: SegmentImpact[];
  equity_impact_assessments?: EquityImpactAssessment[];
  risk_regime_updates?: RiskRegimeUpdate[];
  trading_advisories?: TradingAdvisory[];
};

type FeedPayload<TItem> = {
  status?: string;
  advisory_label?: string;
  ticker?: string;
  freshness?: { latest_available_at?: string | null; item_count?: number };
  items?: TItem[];
};

type CockpitPayload = {
  analystBrief: AnalystBriefPayload;
  sourceSignals: FeedPayload<SourceSignal>;
  latestMarketEvents: FeedPayload<MarketEvent>;
  nvdaMarketEvents: FeedPayload<MarketEvent>;
  latestTradingAdvisories: FeedPayload<TradingAdvisory>;
  checkedAt: string;
};

const INTERNAL_TOKEN_HEADER = "X-Internal-Token";

function internalApiBaseUrl(): string {
  return (
    process.env.AI_INFRA_FUND_INTERNAL_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000"
  ).replace(/\/$/, "");
}

function internalHeaders(): HeadersInit | undefined {
  const token = process.env.AI_INFRA_FUND_INTERNAL_TOKEN?.trim();
  return token ? { [INTERNAL_TOKEN_HEADER]: token } : undefined;
}

async function readCockpitPayload(): Promise<CockpitPayload> {
  const [
    analystBrief,
    sourceSignals,
    latestMarketEvents,
    nvdaMarketEvents,
    latestTradingAdvisories,
  ] = await Promise.all([
    readAnalystBriefPayload(),
    readFeedPayload<SourceSignal>("/internal/source-signals/latest"),
    readFeedPayload<MarketEvent>("/internal/market-events/latest"),
    readFeedPayload<MarketEvent>("/internal/market-events/NVDA"),
    readFeedPayload<TradingAdvisory>("/internal/trading-advisory/latest"),
  ]);

  return {
    analystBrief,
    sourceSignals,
    latestMarketEvents,
    nvdaMarketEvents,
    latestTradingAdvisories,
    checkedAt: new Date().toISOString(),
  };
}

async function readAnalystBriefPayload(): Promise<AnalystBriefPayload> {
  return readApiData<AnalystBriefPayload>(
    "/internal/analyst-brief/latest",
    degradedAnalystBrief("API-backed analyst brief unavailable"),
  );
}

async function readFeedPayload<TItem>(
  endpoint: string,
): Promise<FeedPayload<TItem>> {
  return readApiData<FeedPayload<TItem>>(endpoint, {
    status: "degraded",
    advisory_label: "advisory_only",
    items: [],
  });
}

async function readApiData<TData>(
  endpoint: string,
  fallback: TData,
): Promise<TData> {
  try {
    const response = await fetch(`${internalApiBaseUrl()}${endpoint}`, {
      cache: "no-store",
      headers: internalHeaders(),
      method: "GET",
    });
    const payload = (await response.json()) as ApiEnvelope<TData>;
    if (!response.ok || !payload.data) {
      return fallback;
    }
    return payload.data;
  } catch {
    return fallback;
  }
}

function degradedAnalystBrief(detail: string): AnalystBriefPayload {
  return {
    status: "degraded",
    advisory_label: "advisory_only",
    detail,
    brief: {
      brief_id: "api-backed-brief-unavailable",
      as_of: null,
      title: "API-backed analyst brief unavailable",
      advisory_label: "advisory_only",
      executive_summary:
        "API-backed analyst brief unavailable. The cockpit is waiting for the read-only analyst brief feed.",
      model_run_ids: [],
    },
    market_events: [],
    segment_impacts: [],
    equity_impact_assessments: [],
    risk_regime_updates: [],
    trading_advisories: [],
  };
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "No timestamp";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

function freshnessClass(payload: AnalystBriefPayload): string {
  return payload.status === "available" ? "fresh-data" : "stale-data";
}

function isStale(payload: AnalystBriefPayload): boolean {
  return payload.status !== "available";
}

function text(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function list(values: string[] | undefined): string[] {
  return Array.isArray(values) ? values.filter(Boolean) : [];
}

function payloadText(
  payload: Record<string, unknown> | null | undefined,
  key: string,
  fallback: string,
): string {
  return text(payload?.[key], fallback);
}

function checksCount(advisories: TradingAdvisory[]): number {
  return advisories.reduce((count, advisory) => {
    const checks = advisory.deterministic_checks;
    if (Array.isArray(checks)) {
      return count + checks.length;
    }
    if (checks && typeof checks === "object") {
      return count + Object.keys(checks).length;
    }
    return count;
  }, 0);
}

export default async function DailyTradingCockpitPage() {
  const data = await readCockpitPayload();
  const briefPayload = data.analystBrief;
  const brief = briefPayload.brief ?? degradedAnalystBrief("empty").brief!;
  const marketEvents =
    briefPayload.market_events?.length
      ? briefPayload.market_events
      : data.latestMarketEvents.items ?? [];
  const segmentImpacts = briefPayload.segment_impacts ?? [];
  const equityAssessments = briefPayload.equity_impact_assessments ?? [];
  const riskRegimes = briefPayload.risk_regime_updates ?? [];
  const tradingAdvisories =
    briefPayload.trading_advisories?.length
      ? briefPayload.trading_advisories
      : data.latestTradingAdvisories.items ?? [];
  const topEvents = marketEvents.slice(0, 4);
  const focusAssessments = equityAssessments.slice(0, 5);
  const sourceSignals = data.sourceSignals.items ?? [];

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
            <strong>API read model</strong>
            <small>
              {formatTimestamp(brief.as_of)} · {brief.brief_id ?? "no-brief"}
            </small>
          </div>
          <div className="wave2-command-card">
            <span>MarketEvents</span>
            <strong>{marketEvents.length}</strong>
            <small>evidence-linked</small>
          </div>
          <div className="wave2-command-card">
            <span>Suggested actions</span>
            <strong>{tradingAdvisories.length}</strong>
            <small>watch / accumulate / hold / trim / avoid</small>
          </div>
          <div className="wave2-command-card">
            <span>Readiness checks</span>
            <strong>{checksCount(tradingAdvisories)}</strong>
            <small className={freshnessClass(briefPayload)}>
              {isStale(briefPayload) ? "stale-data" : "fresh-data"}
            </small>
          </div>
        </section>

        {isStale(briefPayload) ? (
          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Backend state</p>
                <h2>API-backed analyst brief unavailable</h2>
              </div>
              <span className="readonly-label">stale-data</span>
            </div>
            <p className="wave2-lede">
              {briefPayload.detail ??
                "The read-only API did not return an available analyst brief."}
            </p>
          </section>
        ) : null}

        <div className="wave2-grid wave2-grid-2">
          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Executive summary</p>
                <h2>Daily high-alpha brief with LLM analyst notes</h2>
              </div>
              <span className="readonly-label">API read model</span>
            </div>
            <p className="wave2-lede">
              {brief.executive_summary ??
                "No executive summary has been produced yet."}
            </p>
            <div className="wave2-note-stack">
              {sourceSignals.slice(0, 3).map((signal) => (
                <article className="wave2-note" key={signal.signal_id}>
                  <span>{signal.review_status ?? "review pending"}</span>
                  <strong>{signal.title ?? signal.signal_id}</strong>
                  <p>{list(signal.themes).join(", ") || "No themes reported."}</p>
                  <small>
                    confidence {signal.confidence ?? "not reported"} ·{" "}
                    {list(signal.tickers).join(", ") || "watchlist"}
                  </small>
                  <EvidencePills ids={list(signal.evidence_ids)} />
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
              <span>Advisory</span>
              <span>Evidence</span>
              <span>Action</span>
              {tradingAdvisories.slice(0, 5).map((advisory) => (
                <div className="wave2-table-row" key={advisory.advisory_id}>
                  <strong>{advisory.ticker ?? "Portfolio"}</strong>
                  <span>{advisory.advisory_label ?? "advisory_only"}</span>
                  <span>{list(advisory.evidence_ids).length}</span>
                  <AdvisoryPill label={advisory.analyst_action ?? "watch"} />
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
              <article className="wave2-card" key={event.event_id}>
                <div className="wave2-card-kicker">
                  <span>{text(event.event_type, "market event").replaceAll("_", " ")}</span>
                  <strong>{event.review_status ?? "reviewed"}</strong>
                </div>
                <h3>{event.catalyst ?? "No catalyst reported."}</h3>
                <p>{event.ai_relevance ?? "No AI relevance summary reported."}</p>
                <div className="wave2-meta">
                  <span>Horizon</span>
                  <strong>{event.time_horizon ?? "not reported"}</strong>
                  <span>Direction</span>
                  <strong>{event.direction ?? "not reported"}</strong>
                  <span>Confidence</span>
                  <strong>{event.confidence ?? "not reported"}</strong>
                </div>
                <div className="wave2-chip-row">
                  {list(event.tickers).map((ticker) => (
                    <span className="wave2-chip" key={`${event.event_id}-${ticker}`}>
                      {ticker}
                    </span>
                  ))}
                </div>
                <EvidencePills ids={list(event.source_evidence_ids ?? event.evidence_ids)} />
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
              {segmentImpacts.slice(0, 5).map((segment) => (
                <article className="wave2-list-card" key={segment.segment_id}>
                  <div>
                    <strong>{segment.segment_name ?? segment.segment_id}</strong>
                    <AdvisoryPill label={segment.impact_direction ?? "watch"} />
                  </div>
                  <p>{segment.impact_summary ?? "No segment impact summary."}</p>
                  <div className="wave2-mini-columns">
                    <span>
                      First-order: {list(segment.primary_tickers).join(", ") || "none"}
                    </span>
                    <span>
                      Second-order:{" "}
                      {list(segment.second_order_tickers).join(", ") || "none"}
                    </span>
                  </div>
                  <RiskFlags
                    flags={list(
                      segment.payload?.risk_flags as string[] | undefined,
                    )}
                  />
                  <EvidencePills ids={list(segment.evidence_ids)} />
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
              {riskRegimes.map((risk) => (
                <article className="wave2-list-card" key={risk.regime_id}>
                  <div>
                    <strong>{risk.risk_type ?? "risk regime"}</strong>
                    <AdvisoryPill label={risk.status ?? "watch"} />
                  </div>
                  <p>{risk.summary ?? "No risk summary."}</p>
                  <div className="wave2-invalidation">
                    <strong>Relief / invalidation condition</strong>
                    <span>
                      {risk.portfolio_monitoring_note ??
                        payloadText(risk.payload, "relief_condition", "No relief condition reported.")}
                    </span>
                  </div>
                  <EvidencePills ids={list(risk.evidence_ids)} />
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
              <article className="wave2-card" key={assessment.assessment_id}>
                <div className="wave2-equity-title">
                  <div>
                    <strong>{assessment.ticker ?? "Ticker"}</strong>
                    <span>{assessment.company ?? "Company"}</span>
                  </div>
                  <AdvisoryPill label={assessment.advisory_implication ?? "watch"} />
                </div>
                <p>{assessment.assessment ?? "No current thesis assessment."}</p>
                <div className="wave2-case-grid">
                  <span>Bull case</span>
                  <p>{payloadText(assessment.payload, "bull_case", "Not reported.")}</p>
                  <span>Bear case</span>
                  <p>{payloadText(assessment.payload, "bear_case", "Not reported.")}</p>
                </div>
                <RiskFlags flags={list(assessment.risk_flags)} />
                <div className="wave2-invalidation">
                  <strong>Invalidation</strong>
                  <span>{assessment.invalidation ?? "No invalidation condition reported."}</span>
                </div>
                <EvidencePills ids={list(assessment.evidence_ids)} />
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
              {tradingAdvisories.map((advisory) => (
                <article className="wave2-list-card" key={advisory.advisory_id}>
                  <div>
                    <strong>{advisory.ticker ?? "Portfolio"}</strong>
                    <AdvisoryPill label={advisory.analyst_action ?? "watch"} />
                  </div>
                  <p>{advisory.advisory_summary ?? "No advisory summary."}</p>
                  <RiskFlags
                    flags={list(advisory.payload?.risk_flags as string[] | undefined)}
                  />
                  <div className="wave2-invalidation">
                    <strong>Invalidation</strong>
                    <span>
                      {payloadText(
                        advisory.payload,
                        "invalidation_condition",
                        "No invalidation condition reported.",
                      )}
                    </span>
                  </div>
                  <EvidencePills ids={list(advisory.evidence_ids)} />
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
              {tradingAdvisories.map((advisory) => (
                <article className="wave2-list-card" key={`${advisory.advisory_id}-plan`}>
                  <div>
                    <strong>{advisory.linked_trade_plan_id ?? "plan pending"}</strong>
                    <AdvisoryPill label={advisory.analyst_action ?? "watch"} />
                  </div>
                  <p>{advisory.advisory_summary ?? "No planning note."}</p>
                  <div className="wave2-mini-columns">
                    <span>
                      Entry: {payloadText(advisory.payload, "entry_zone", "review only")}
                    </span>
                    <span>
                      Invalidation:{" "}
                      {payloadText(advisory.payload, "invalidation_level", "review only")}
                    </span>
                  </div>
                  <EvidencePills ids={list(advisory.evidence_ids)} />
                </article>
              ))}
            </div>
          </section>
        </div>
      </AppShell>
    </div>
  );
}
