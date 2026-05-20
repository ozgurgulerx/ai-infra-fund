export type ApiEnvelope<TData> = {
  data?: TData;
  error?: { code?: string; message?: string };
};

export type SourceLinkRef = {
  url?: string;
  label?: string;
  evidence_ids?: string[];
};

export type EvidenceRef = {
  evidence_id?: string;
  title?: string | null;
  summary?: string | null;
  source_links?: SourceLinkRef[];
};

export type SourceSignal = {
  signal_id?: string;
  title?: string;
  summary?: string;
  display_text?: string;
  tickers?: string[];
  themes?: string[];
  evidence_ids?: string[];
  evidence_refs?: EvidenceRef[];
  source_links?: SourceLinkRef[];
  confidence?: string | number;
  review_status?: string;
  available_at?: string | null;
};

export type MarketEvent = {
  event_id?: string;
  event_type?: string;
  tickers?: string[];
  companies?: string[];
  themes?: string[];
  catalyst?: string;
  ai_relevance?: string;
  display_text?: string;
  direction?: string;
  time_horizon?: string;
  confidence?: string | number;
  available_at?: string | null;
  source_evidence_ids?: string[];
  evidence_ids?: string[];
  evidence_refs?: EvidenceRef[];
  source_links?: SourceLinkRef[];
  review_status?: string;
};

export type SegmentImpact = {
  segment_id?: string;
  segment_name?: string;
  primary_tickers?: string[];
  second_order_tickers?: string[];
  linked_event_ids?: string[];
  impact_direction?: string;
  impact_summary?: string;
  evidence_ids?: string[];
  evidence_refs?: EvidenceRef[];
  source_links?: SourceLinkRef[];
  proof_points?: Array<{ proof_point_id?: string; summary?: string; evidence_ids?: string[] }>;
  payload?: Record<string, unknown> | null;
};

export type EquityImpactAssessment = {
  assessment_id?: string;
  ticker?: string;
  company?: string;
  assessment?: string;
  advisory_implication?: string;
  risk_flags?: string[];
  invalidation?: string;
  evidence_ids?: string[];
  evidence_refs?: EvidenceRef[];
  source_links?: SourceLinkRef[];
  payload?: Record<string, unknown> | null;
};

export type RiskRegimeUpdate = {
  regime_id?: string;
  risk_type?: string;
  status?: string;
  severity?: string;
  confidence?: string | number;
  summary?: string;
  portfolio_monitoring_note?: string;
  relief_condition?: string;
  invalidation_condition?: string;
  affected_tickers?: string[];
  evidence_ids?: string[];
  evidence_refs?: EvidenceRef[];
  source_links?: SourceLinkRef[];
  payload?: Record<string, unknown> | null;
};

export type TradingAdvisory = {
  advisory_id?: string;
  ticker?: string;
  advisory_label?: string;
  analyst_action?: string;
  advisory_summary?: string;
  evidence_ids?: string[];
  evidence_refs?: EvidenceRef[];
  source_links?: SourceLinkRef[];
  model_run_ids?: string[];
  deterministic_checks?: string[] | Record<string, unknown>;
  linked_trade_plan_id?: string | null;
  payload?: Record<string, unknown> | null;
};

export type AdvisoryUpdate = {
  update_id?: string;
  ticker?: string;
  company?: string | null;
  previous_label?: string | null;
  current_label?: string;
  what_changed?: string;
  update_type?: string;
  thesis_change_direction?: string;
  risk_change_direction?: string;
  valuation_change_direction?: string;
  confidence_change?: string;
  time_horizon?: string | null;
  evidence_ids?: string[];
  evidence_refs?: EvidenceRef[];
  source_links?: SourceLinkRef[];
  model_run_ids?: string[];
  deterministic_check_ids?: string[];
  advisory_label?: string;
  created_at?: string | null;
};

export type WatchlistRating = {
  ticker?: string;
  company?: string | null;
  current_label?: string;
  previous_label?: string | null;
  outlook_delta?: string;
  risk_delta?: string;
  valuation_delta?: string;
  confidence_delta?: string;
  latest_change?: string;
  freshness?: string | null;
  source_advisory_id?: string | null;
  source_update_id?: string | null;
  risk_flags?: string[];
  invalidation?: string | null;
  evidence_ids?: string[];
  evidence_refs?: EvidenceRef[];
  source_links?: SourceLinkRef[];
  advisory_only?: boolean;
};

export type AnalystBrief = {
  brief_id?: string;
  as_of?: string | null;
  title?: string;
  advisory_label?: string;
  executive_summary?: string;
  model_run_ids?: string[];
  payload?: Record<string, unknown> | null;
};

export type AnalystBriefPayload = {
  status?: string;
  advisory_label?: string;
  detail?: string;
  brief?: AnalystBrief;
  market_events?: MarketEvent[];
  segment_impacts?: SegmentImpact[];
  equity_impact_assessments?: EquityImpactAssessment[];
  risk_regime_updates?: RiskRegimeUpdate[];
  trading_advisories?: TradingAdvisory[];
  advisory_updates?: AdvisoryUpdate[];
};

export type FeedPayload<TItem> = {
  status?: string;
  advisory_label?: string;
  ticker?: string;
  freshness?: { latest_available_at?: string | null; item_count?: number };
  items?: TItem[];
};

export type SegmentMapPayload = {
  status?: string;
  advisory_label?: string;
  segment_impacts?: SegmentImpact[];
  market_events?: MarketEvent[];
  risk_regime_updates?: RiskRegimeUpdate[];
};

export type PortfolioPosition = {
  ticker?: string;
  company?: string;
  segment_tags?: string[];
  role?: string;
  bucket?: string;
  market_value?: string | number | null;
  portfolio_weight?: string | number | null;
  portfolio_weight_pct?: string | number | null;
  target_weight?: string | number | null;
  target_weight_pct?: string | number | null;
  drift?: string | number | null;
  unrealized_pnl?: string | number | null;
  open_trade_plan_id?: string | null;
  risk_flags?: string[];
  last_price_timestamp?: string | null;
};

export type PortfolioExposureSnapshot = {
  snapshot_id?: string;
  as_of?: string | null;
  currency?: string;
  source?: string;
  advisory_label?: string;
  total_market_value?: string | number | null;
  cash_placeholder?: string | number | null;
  gross_equity_exposure?: string | number | null;
  position_count?: number;
  positions?: PortfolioPosition[];
  correlation_exposure_ids?: string[];
  pnl_summary_id?: string | null;
  target_weights_id?: string | null;
  concentration_flags?: string[];
  stale_price_flags?: string[];
  payload?: Record<string, unknown> | null;
};

export type PortfolioExposurePayload = {
  status?: string;
  advisory_label?: string;
  snapshot?: PortfolioExposureSnapshot | null;
};

export type TradeJournalEntry = {
  trade_id?: string;
  ticker?: string;
  side?: string;
  quantity?: string;
  price?: string | null;
  status?: string;
  trade_date?: string;
  notes?: string | null;
  journal_only?: boolean;
  advisory_only?: boolean;
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

export async function readApiData<TData>(
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

export function degradedAnalystBrief(detail: string): AnalystBriefPayload {
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
    advisory_updates: [],
  };
}

export function emptyFeed<TItem>(): FeedPayload<TItem> {
  return {
    status: "degraded",
    advisory_label: "advisory_only",
    items: [],
  };
}

export function readAnalystBriefPayload(): Promise<AnalystBriefPayload> {
  return readApiData<AnalystBriefPayload>(
    "/internal/analyst-brief/latest",
    degradedAnalystBrief("API-backed analyst brief unavailable"),
  );
}

export function readLatestSourceSignals(): Promise<FeedPayload<SourceSignal>> {
  return readApiData<FeedPayload<SourceSignal>>(
    "/internal/source-signals/latest",
    emptyFeed<SourceSignal>(),
  );
}

export function readLatestMarketEvents(): Promise<FeedPayload<MarketEvent>> {
  return readApiData<FeedPayload<MarketEvent>>(
    "/internal/market-events/latest",
    emptyFeed<MarketEvent>(),
  );
}

export function readLatestTradingAdvisory(): Promise<FeedPayload<TradingAdvisory>> {
  return readApiData<FeedPayload<TradingAdvisory>>(
    "/internal/trading-advisory/latest",
    emptyFeed<TradingAdvisory>(),
  );
}

export function readLatestAdvisoryUpdates(): Promise<FeedPayload<AdvisoryUpdate>> {
  return readApiData<FeedPayload<AdvisoryUpdate>>(
    "/internal/advisory-updates/latest",
    emptyFeed<AdvisoryUpdate>(),
  );
}

export function readLatestWatchlistRatings(): Promise<FeedPayload<WatchlistRating>> {
  return readApiData<FeedPayload<WatchlistRating>>(
    "/internal/watchlist/ratings/latest",
    emptyFeed<WatchlistRating>(),
  );
}

export function readLatestSegmentMap(): Promise<SegmentMapPayload> {
  return readApiData<SegmentMapPayload>("/internal/segment-map/latest", {
    status: "degraded",
    advisory_label: "advisory_only",
    segment_impacts: [],
    market_events: [],
    risk_regime_updates: [],
  });
}

export function readLatestPortfolioExposure(): Promise<PortfolioExposurePayload> {
  return readApiData<PortfolioExposurePayload>(
    "/internal/portfolio/exposure/latest",
    {
      status: "degraded",
      advisory_label: "advisory_only",
      snapshot: null,
    },
  );
}

export function readTradeJournalEntries(): Promise<{ entries?: TradeJournalEntry[] }> {
  return readApiData<{ entries?: TradeJournalEntry[] }>(
    "/internal/trade-journal/entries",
    { entries: [] },
  );
}

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "No timestamp";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

export function list(values: string[] | undefined): string[] {
  return Array.isArray(values) ? values.filter(Boolean) : [];
}

export function text(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

export function payloadText(
  payload: Record<string, unknown> | null | undefined,
  key: string,
  fallback: string,
): string {
  return text(payload?.[key], fallback);
}

export function confidenceNumber(value: string | number | undefined): number | null {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function confidenceTone(value: string | number | undefined): "fresh" | "review" | "cautious" {
  const score = confidenceNumber(value);
  if (score === null) {
    return String(value ?? "").toLowerCase() === "high" ? "fresh" : "review";
  }
  if (score >= 0.75) {
    return "fresh";
  }
  if (score >= 0.5) {
    return "review";
  }
  return "cautious";
}

export function collectEvidenceIds(
  ...groups: Array<Array<{ evidence_ids?: string[]; source_evidence_ids?: string[] }>>
): string[] {
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

export function collectSourceLinks(
  ...groups: Array<Array<{ source_links?: SourceLinkRef[] }>>
): SourceLinkRef[] {
  const seen = new Set<string>();
  const result: SourceLinkRef[] = [];
  for (const link of groups.flatMap((group) => group.flatMap((item) => item.source_links ?? []))) {
    const url = link.url;
    if (!url || seen.has(url)) {
      continue;
    }
    seen.add(url);
    result.push(link);
  }
  return result;
}

export function checksCount(advisories: TradingAdvisory[]): number {
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
