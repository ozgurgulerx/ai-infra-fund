import { AppShell } from "../components/app-shell";
import { AdvisoryPill, RiskFlags } from "../components/daily-cockpit/evidence-pills";
import {
  AdvisoryTable,
  EmptyState,
  EvidenceDrawer,
  LlmReviewBadge,
  MetricTile,
  SectionCard,
  StatusChip,
} from "../components/workstation";

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

function collectEvidenceIds(...groups: Array<Array<{ evidence_ids?: string[]; source_evidence_ids?: string[] }>>): string[] {
  return Array.from(
    new Set(
      groups.flatMap((group) =>
        group.flatMap((item) => [
          ...list(item.evidence_ids),
          ...list(item.source_evidence_ids),
        ]),
      ),
    ),
  );
}

function confidenceNumber(value: string | number | undefined): number | null {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function confidenceTone(value: string | number | undefined): "fresh" | "review" | "cautious" {
  const score = confidenceNumber(value);
  if (score === null) {
    return "review";
  }
  if (score >= 0.75) {
    return "fresh";
  }
  if (score >= 0.5) {
    return "review";
  }
  return "cautious";
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
  const lowConfidenceEvents = marketEvents.filter((event) => {
    const score = confidenceNumber(event.confidence);
    return score !== null && score < 0.5;
  });
  const coreMarketEvents = marketEvents.filter(
    (event) => !lowConfidenceEvents.includes(event),
  );
  const topEvents = coreMarketEvents.slice(0, 4);
  const focusAssessments = equityAssessments.slice(0, 5);
  const sourceSignals = data.sourceSignals.items ?? [];
  const allEvidenceIds = collectEvidenceIds(
    sourceSignals,
    marketEvents,
    segmentImpacts,
    equityAssessments,
    riskRegimes,
    tradingAdvisories,
  );

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Daily Trading Cockpit"
        title="AI Infrastructure Trading Analyst Workstation"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <section className="summary-strip" aria-label="Daily cockpit status">
          <MetricTile
            label="AI infrastructure regime"
            value="API read model"
            detail={`${formatTimestamp(brief.as_of)} · ${
              isStale(briefPayload) ? "stale-data" : "fresh-data"
            }`}
            tone={isStale(briefPayload) ? "stale" : "fresh"}
          />
          <MetricTile
            label="MarketEvents"
            value={marketEvents.length}
            detail="ranked, evidence-linked"
          />
          <MetricTile
            label="Suggested actions"
            value={tradingAdvisories.length}
            detail="watch / accumulate / hold / trim / avoid"
            tone="review"
          />
          <MetricTile
            label="Readiness checks"
            value={checksCount(tradingAdvisories)}
            detail="deterministic gates"
            tone="neutral"
          />
        </section>

        {isStale(briefPayload) ? (
          <SectionCard
            eyebrow="Backend state"
            title="API-backed analyst brief unavailable"
            badge={<StatusChip label="stale-data" tone="stale" />}
          >
            <p className="wave2-lede">
              {briefPayload.detail ??
                "The read-only API did not return an available analyst brief."}
            </p>
          </SectionCard>
        ) : null}

        <div className="workstation-grid workstation-grid-2">
          <SectionCard
            eyebrow="Executive summary"
            title="What changed today?"
            subtitle="Daily high-alpha brief with LLM analyst notes"
            badge={<LlmReviewBadge status={briefPayload.status ?? "fallback"} />}
          >
            <p className="wave2-lede">
              {brief.executive_summary ??
                "No executive summary has been produced yet."}
            </p>
            <div className="compact-list">
              {sourceSignals.slice(0, 3).map((signal) => (
                <div className="compact-row" key={signal.signal_id}>
                  <strong>{signal.title ?? "Source signal under review"}</strong>
                  <span>{list(signal.themes).join(", ") || "No themes reported."}</span>
                  <StatusChip
                    label={`confidence ${signal.confidence ?? "n/a"}`}
                    tone={confidenceTone(signal.confidence)}
                  />
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard
            eyebrow="Portfolio exposure snapshot"
            title="Top advisory stances table"
            subtitle="Theme exposure under review"
            badge={<StatusChip label="No transaction surface" tone="neutral" />}
          >
            <AdvisoryTable
              columns={["Ticker", "Label", "Evidence", "Action"]}
              rows={tradingAdvisories.slice(0, 5).map((advisory) => ({
                id: advisory.advisory_id ?? advisory.ticker ?? "portfolio",
                cells: [
                  <strong key="ticker">{advisory.ticker ?? "Portfolio"}</strong>,
                  advisory.advisory_label ?? "advisory_only",
                  `${list(advisory.evidence_ids).length} refs`,
                  <AdvisoryPill
                    key="action"
                    label={advisory.analyst_action ?? "watch"}
                  />,
                ],
              }))}
            />
          </SectionCard>
        </div>

        <SectionCard
          eyebrow="Top MarketEvents"
          title="Top ranked MarketEvents"
          subtitle="Catalyst tape with relevance, confidence, ticker, segment, and freshness."
          badge={<StatusChip label="classified intelligence" tone="review" />}
        >
          <AdvisoryTable
            columns={["Event", "Tickers", "Direction", "Horizon", "Confidence"]}
            rows={topEvents.map((event) => ({
              id: event.event_id ?? event.catalyst ?? "market-event",
              cells: [
                <span className="table-main" key="event">
                  <strong>{event.catalyst ?? "No catalyst reported."}</strong>
                  <small>{event.ai_relevance ?? "No AI relevance summary reported."}</small>
                </span>,
                list(event.tickers).join(", ") || "watchlist",
                event.direction ?? "not reported",
                event.time_horizon ?? "not reported",
                <StatusChip
                  key="confidence"
                  label={String(event.confidence ?? "n/a")}
                  tone={confidenceTone(event.confidence)}
                />,
              ],
            }))}
          />
          {lowConfidenceEvents.length > 0 ? (
            <details className="compact-collapse">
              <summary>Collapsed low-confidence monitor-only events</summary>
              <div className="compact-list">
                {lowConfidenceEvents.map((event) => (
                  <div className="compact-row" key={event.event_id}>
                    <strong>{event.catalyst ?? "Monitor-only event"}</strong>
                    <span>{event.ai_relevance ?? "No relevance note."}</span>
                  </div>
                ))}
              </div>
            </details>
          ) : null}
        </SectionCard>

        <div className="workstation-grid workstation-grid-2">
          <SectionCard
            eyebrow="Segment impact snapshot"
            title="Segment heatmap"
            subtitle="Bottlenecks, beneficiaries, and latest change."
          >
            <div className="segment-heatmap">
              {segmentImpacts.slice(0, 5).map((segment) => (
                <article className="segment-heatmap-card" key={segment.segment_id}>
                  <div className="compact-row-heading">
                    <strong>{segment.segment_name ?? segment.segment_id}</strong>
                    <AdvisoryPill label={segment.impact_direction ?? "watch"} />
                  </div>
                  <p>{segment.impact_summary ?? "No segment impact summary."}</p>
                  <span>Beneficiaries: {list(segment.primary_tickers).join(", ") || "none"}</span>
                  <span>Evidence count: {list(segment.evidence_ids).length}</span>
                  <RiskFlags
                    flags={list(
                      segment.payload?.risk_flags as string[] | undefined,
                    )}
                  />
                </article>
              ))}
            </div>
          </SectionCard>

          <SectionCard
            eyebrow="Risk regime updates"
            title="Risk / invalidation watch"
            subtitle="Invalidation watchlist"
          >
            <div className="compact-list">
              {riskRegimes.map((risk) => (
                <article className="compact-card" key={risk.regime_id}>
                  <div className="compact-row-heading">
                    <strong>{risk.risk_type ?? "risk regime"}</strong>
                    <AdvisoryPill label={risk.status ?? "watch"} />
                  </div>
                  <p>{risk.summary ?? "No risk summary."}</p>
                  <div className="wave2-invalidation">
                    <strong>Relief / invalidation condition</strong>
                    <span>
                      {risk.portfolio_monitoring_note ??
                        payloadText(risk.payload, "relief_condition", "Invalidation not yet defined")}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          </SectionCard>
        </div>

        <SectionCard
          eyebrow="Equity impact assessments"
          title="Ticker thesis, risk, and invalidation"
          badge={<StatusChip label="planning guidance only" tone="neutral" />}
        >
          <AdvisoryTable
            columns={["Ticker", "Thesis", "Risk", "Invalidation", "Stance"]}
            rows={focusAssessments.map((assessment) => ({
              id: assessment.assessment_id ?? assessment.ticker ?? "assessment",
              cells: [
                <span className="table-main" key="ticker">
                  <strong>{assessment.ticker ?? "Ticker"}</strong>
                  <small>{assessment.company ?? "Company"}</small>
                </span>,
                assessment.assessment ?? "No current thesis assessment.",
                list(assessment.risk_flags).join(", ") || "No risk flags",
                assessment.invalidation ?? "Invalidation not yet defined",
                <AdvisoryPill
                  key="stance"
                  label={assessment.advisory_implication ?? "watch"}
                />,
              ],
            }))}
          />
        </SectionCard>

        <div className="workstation-grid workstation-grid-2">
          <SectionCard
            eyebrow="Suggested actions"
            title="Advisory labels and review prompts"
          >
            <div className="compact-list">
              {tradingAdvisories.map((advisory) => (
                <article className="compact-card" key={advisory.advisory_id}>
                  <div className="compact-row-heading">
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
                        "Invalidation not yet defined",
                      )}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          </SectionCard>

          <SectionCard
            eyebrow="Open trade plans"
            title="Manual planning queue"
            badge={<StatusChip label="local journal only" tone="review" />}
          >
            <div className="compact-list">
              {tradingAdvisories.map((advisory) => (
                <article className="compact-card" key={`${advisory.advisory_id}-plan`}>
                  <div className="compact-row-heading">
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
                </article>
              ))}
              {tradingAdvisories.length === 0 ? (
                <EmptyState title="No open trade plans from the read model." />
              ) : null}
            </div>
          </SectionCard>
        </div>

        <SectionCard
          eyebrow="Evidence And Audit Trace"
          title="Evidence and audit access"
          subtitle="Raw identifiers are intentionally behind progressive disclosure."
          badge={<StatusChip label="Advisory-only" tone="neutral" />}
        >
          <EvidenceDrawer ids={allEvidenceIds} />
        </SectionCard>
      </AppShell>
    </div>
  );
}
