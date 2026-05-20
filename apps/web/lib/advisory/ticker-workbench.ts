export type AdvisoryStance = {
  action:
    | "watch"
    | "accumulate"
    | "hold"
    | "trim"
    | "avoid"
    | "exit-candidate"
    | "review"
    | "unrated";
  tone: "positive" | "neutral" | "cautious" | "negative" | "mixed";
  confidence?: string | number | null;
  freshness?: string | null;
  source_advisory_id?: string | null;
  evidence_ids: string[];
  model_run_ids: string[];
  deterministic_check_ids: string[];
  advisory_only: true;
};

export type RelevanceMetadata = {
  score?: number;
  level?: string;
  reason?: string;
};

export type WorkbenchItem = {
  [key: string]: unknown;
  evidence_ids?: string[];
  evidence_refs?: Array<{
    evidence_id?: string;
    title?: string | null;
    summary?: string | null;
    source_links?: Array<{ url?: string; label?: string; evidence_ids?: string[] }>;
  }>;
  source_links?: Array<{ url?: string; label?: string; evidence_ids?: string[] }>;
  relevance?: RelevanceMetadata;
};

export type RelatedTicker = {
  ticker: string;
  relationship_type: string;
  reason: string;
  evidence_ids?: string[];
  relevance?: RelevanceMetadata;
};

export type ThemeGroup = {
  theme_id: string;
  theme_label: string;
  ticker: string;
  why_now: string;
  what_changed: string;
  advisory_stance: AdvisoryStance;
  source_signals: WorkbenchItem[];
  market_events: WorkbenchItem[];
  impact_assessments: WorkbenchItem[];
  llm_notes: WorkbenchItem[];
  journal_notes: WorkbenchItem[];
  trade_plan_notes: WorkbenchItem[];
  related_tickers: RelatedTicker[];
  risk_flags: string[];
  invalidation?: string | null;
  next_watch_items: string[];
  latest_available_at?: string | null;
  evidence_ids: string[];
  source_links?: Array<{ url?: string; label?: string; evidence_ids?: string[] }>;
};

export type TickerWorkbenchPayload = {
  status?: "available" | "empty" | "degraded" | string;
  ticker: string;
  advisory_label?: "advisory_only" | string;
  source_signals?: WorkbenchItem[];
  market_events?: WorkbenchItem[];
  segment_impacts?: WorkbenchItem[];
  equity_impact_assessments?: WorkbenchItem[];
  valuation_contexts?: WorkbenchItem[];
  trading_advisories?: WorkbenchItem[];
  trade_plans?: WorkbenchItem[];
  risk_regime_updates?: WorkbenchItem[];
  llm_analyst_notes?: WorkbenchItem[];
  theme_groups?: ThemeGroup[];
  is_fixture_fallback?: boolean;
  detail?: string;
};

type ApiEnvelope<TData> = {
  data?: TData;
  error?: { code?: string; message?: string };
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

export async function readTickerWorkbenchPayload(
  ticker: string,
): Promise<TickerWorkbenchPayload> {
  const symbol = ticker.trim().toUpperCase();
  try {
    const response = await fetch(
      `${internalApiBaseUrl()}/internal/ticker/${encodeURIComponent(symbol)}/workbench`,
      {
        cache: "no-store",
        headers: internalHeaders(),
        method: "GET",
      },
    );
    const payload = (await response.json()) as ApiEnvelope<TickerWorkbenchPayload>;
    if (!response.ok || !payload.data) {
      return degradedTickerWorkbench(symbol, payload.error?.message);
    }
    return {
      ...payload.data,
      ticker: payload.data.ticker ?? symbol,
      theme_groups: payload.data.theme_groups ?? [],
      is_fixture_fallback: false,
    };
  } catch (error) {
    const detail = error instanceof Error ? error.message : "request failed";
    return degradedTickerWorkbench(symbol, detail);
  }
}

function degradedTickerWorkbench(
  ticker: string,
  detail = "Ticker workbench read model is unavailable.",
): TickerWorkbenchPayload {
  return {
    status: "degraded",
    ticker,
    advisory_label: "advisory_only",
    source_signals: [],
    market_events: [],
    segment_impacts: [],
    equity_impact_assessments: [],
    valuation_contexts: [],
    trading_advisories: [],
    trade_plans: [],
    risk_regime_updates: [],
    llm_analyst_notes: [],
    theme_groups: [],
    is_fixture_fallback: false,
    detail,
  };
}
