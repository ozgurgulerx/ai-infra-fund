import type {
  AdvisoryChainPayload,
  DashboardModuleSummary,
  DashboardOverviewSummary,
  DashboardSummaryFeed,
  DataQualitySummary,
  EvaluationSummary,
  EvidenceSummary,
  IncidentSummary,
  CrawlFrontierHealth,
  LatestAdvisoryRun,
  LatestEquityEvents,
  LatestSignalSnapshots,
  ModelRunSummary,
  RecommendationSummary,
  TickerIntelligenceSummary,
  WatchlistSummary,
  RuntimeProbe,
} from "./status-model";

type ProbeEndpoint = "health" | "ready";
type DashboardSummaryEndpoint =
  | "/internal/status/overview"
  | "/internal/dashboard/evidence-summary"
  | "/internal/dashboard/recommendation-summary"
  | "/internal/dashboard/evaluation-summary"
  | "/internal/dashboard/model-run-summary"
  | "/internal/dashboard/data-quality-summary"
  | "/internal/dashboard/incident-summary"
  | "/internal/dashboard/watchlist-summary"
  | "/internal/dashboard/crawl-frontier-health"
  | "/internal/dashboard/latest-equity-events"
  | "/internal/dashboard/latest-signal-snapshots"
  | "/internal/dashboard/latest-advisory-run"
  | "/internal/dashboard/ticker-intelligence/NVDA";

const DEFAULT_TIMEOUT_MS = 2500;
const DASHBOARD_MODULES_ENDPOINT = "/internal/status/modules";
const DEMO_ADVISORY_CHAIN_ENDPOINT = "/internal/advisory-chain/demo";
const LATEST_ADVISORY_CHAIN_ENDPOINT = "/internal/advisory-chain/latest";
const TRADE_JOURNAL_ENTRIES_ENDPOINT = "/internal/trade-journal/entries";
const TRADE_JOURNAL_PROXY_ENDPOINT = "/api/trade-journal/entries";
const BACKEND_PROXY_PREFIX = "/api/backend";

export type TradeJournalEntryInput = {
  ticker: string;
  side: "buy" | "sell";
  quantity: string;
  price?: string;
  fees?: string;
  trade_date: string;
  settlement_date?: string;
  account_label: string;
  status: "intended" | "paper" | "completed" | "cancelled" | "ignored";
  notes?: string;
};

export type TradeJournalEntry = TradeJournalEntryInput & {
  trade_id: string;
  source: "manual_ui" | string;
  created_at: string;
  journal_only: boolean;
  advisory_only: boolean;
};

export function apiBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
  ).replace(/\/$/, "");
}

function backendProxyUrl(endpoint: string): string {
  return `${BACKEND_PROXY_PREFIX}${endpoint}`;
}

export async function fetchApiHealth(): Promise<RuntimeProbe> {
  return fetchProbe("health");
}

export async function fetchApiReadiness(): Promise<RuntimeProbe> {
  return fetchProbe("ready");
}

export async function fetchDashboardOverview(): Promise<DashboardOverviewSummary> {
  return fetchReadOnlyDashboardSummary(
    "/internal/status/overview",
    "System overview",
  );
}

export async function fetchDashboardModules(): Promise<
  DashboardModuleSummary[]
> {
  const checkedAt = new Date().toISOString();
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS,
  );

  try {
    const response = await fetch(backendProxyUrl(DASHBOARD_MODULES_ENDPOINT), {
      cache: "no-store",
      method: "GET",
      signal: controller.signal,
    });
    const payload = (await response.json()) as {
      data?: DashboardModuleSummary[] | { modules?: DashboardModuleSummary[] };
      modules?: DashboardModuleSummary[];
    };
    const modules = Array.isArray(payload.data)
      ? payload.data
      : (payload.data?.modules ?? payload.modules ?? []);

    if (!response.ok) {
      return [
        {
          id: "api",
          status: "degraded",
          sourceLabel: `API ${DASHBOARD_MODULES_ENDPOINT}`,
          detail: `Backend unavailable: HTTP ${response.status}`,
          visibleValue: "Backend unavailable",
        },
      ];
    }

    return modules.map((module) => ({
      ...module,
      sourceLabel:
        module.sourceLabel ??
        module.source_label ??
        `API ${DASHBOARD_MODULES_ENDPOINT}`,
      detail:
        module.detail ??
        module.visibleValue ??
        module.visible_value ??
        `Updated ${checkedAt}`,
    }));
  } catch (error) {
    const reason = error instanceof Error ? error.message : "request failed";
    return [
      {
        id: "api",
        status: "degraded",
        sourceLabel: `API ${DASHBOARD_MODULES_ENDPOINT}`,
        detail: `Backend unavailable: ${reason}`,
        visibleValue: "Backend unavailable",
      },
    ];
  } finally {
    window.clearTimeout(timeout);
  }
}

export type CrawlActivitySummary = {
  total: number;
  succeeded: number;
  not_modified: number;
  client_error: number;
  server_error: number;
  failed: number;
  window_hours?: number;
};

export async function fetchCrawlActivity(): Promise<CrawlActivitySummary | null> {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS,
  );
  try {
    const response = await fetch(
      backendProxyUrl("/internal/dashboard/crawl-activity"),
      {
        cache: "no-store",
        method: "GET",
        signal: controller.signal,
      },
    );
    if (!response.ok) {
      return null;
    }
    const payload = (await response.json()) as { data?: CrawlActivitySummary };
    return payload.data ?? null;
  } catch {
    return null;
  } finally {
    window.clearTimeout(timeout);
  }
}

export type PortfolioPosition = {
  ticker: string;
  quantity: string;
  market_price: string | null;
  market_value: string | null;
  portfolio_weight: string | null;
  unrealized_pnl: string | null;
};

export type PortfolioSummary = {
  status: "available" | "empty";
  advisory_label: "advisory_only";
  snapshot_id: string | null;
  as_of: string | null;
  total_market_value: string | null;
  cash_value: string | null;
  previous_total_market_value: string | null;
  day_delta_pct: number | null;
  source?: string | null;
  positions: PortfolioPosition[];
};

export async function fetchPortfolioSummary(): Promise<PortfolioSummary | null> {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS,
  );
  try {
    const response = await fetch(
      backendProxyUrl("/internal/dashboard/portfolio-summary"),
      { cache: "no-store", method: "GET", signal: controller.signal },
    );
    if (!response.ok) {
      return null;
    }
    const payload = (await response.json()) as { data?: PortfolioSummary };
    return payload.data ?? null;
  } catch {
    return null;
  } finally {
    window.clearTimeout(timeout);
  }
}

export type RecommendationSummaryItem = {
  recommendation_id: string;
  ticker_or_portfolio: string;
  action: string;
  horizon: string;
  advisory_label: "advisory_only";
  signal_bundle_id: string | null;
  target_weights_id: string | null;
  evidence_count: number;
  model_run_count: number;
  schema_valid: boolean;
  created_at: string | null;
};

export type LatestRecommendationsPayload = {
  status: "available" | "empty";
  advisory_label: "advisory_only";
  items: RecommendationSummaryItem[];
};

export async function fetchLatestRecommendations(
  limit = 10,
): Promise<LatestRecommendationsPayload | null> {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS,
  );
  try {
    const response = await fetch(
      backendProxyUrl(
        `/internal/dashboard/latest-recommendations?limit=${encodeURIComponent(
          String(limit),
        )}`,
      ),
      { cache: "no-store", method: "GET", signal: controller.signal },
    );
    if (!response.ok) {
      return null;
    }
    const payload = (await response.json()) as {
      data?: LatestRecommendationsPayload;
    };
    return payload.data ?? null;
  } catch {
    return null;
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function fetchEvidenceSummary(): Promise<EvidenceSummary> {
  return fetchReadOnlyDashboardSummary(
    "/internal/dashboard/evidence-summary",
    "Evidence",
  );
}

export async function fetchRecommendationSummary(): Promise<RecommendationSummary> {
  return fetchReadOnlyDashboardSummary(
    "/internal/dashboard/recommendation-summary",
    "Recommendations",
  );
}

export async function fetchEvaluationSummary(): Promise<EvaluationSummary> {
  return fetchReadOnlyDashboardSummary(
    "/internal/dashboard/evaluation-summary",
    "Evaluation",
  );
}

export async function fetchModelRunSummary(): Promise<ModelRunSummary> {
  return fetchReadOnlyDashboardSummary(
    "/internal/dashboard/model-run-summary",
    "Model Runs",
  );
}

export async function fetchDataQualitySummary(): Promise<DataQualitySummary> {
  return fetchReadOnlyDashboardSummary(
    "/internal/dashboard/data-quality-summary",
    "Data Quality",
  );
}

export async function fetchIncidentSummary(): Promise<IncidentSummary> {
  return fetchReadOnlyDashboardSummary(
    "/internal/dashboard/incident-summary",
    "Incidents",
  );
}

export async function fetchWatchlistSummary(): Promise<WatchlistSummary> {
  return fetchReadOnlyDashboardSummary(
    "/internal/dashboard/watchlist-summary",
    "Watchlist Status",
  );
}

export async function fetchCrawlFrontierHealth(): Promise<CrawlFrontierHealth> {
  return fetchReadOnlyDashboardSummary(
    "/internal/dashboard/crawl-frontier-health",
    "Crawl Freshness",
  );
}

export async function fetchLatestEquityEvents(): Promise<LatestEquityEvents> {
  return fetchReadOnlyDashboardSummary(
    "/internal/dashboard/latest-equity-events",
    "Latest Equity Events",
  );
}

export async function fetchLatestSignalSnapshots(): Promise<LatestSignalSnapshots> {
  return fetchReadOnlyDashboardSummary(
    "/internal/dashboard/latest-signal-snapshots",
    "Sentiment / Technical / Fundamental",
  );
}

export async function fetchLatestAdvisoryRun(): Promise<LatestAdvisoryRun> {
  return fetchReadOnlyDashboardSummary(
    "/internal/dashboard/latest-advisory-run",
    "Latest Advisory Run",
  );
}

export async function fetchTickerIntelligenceSummary(): Promise<TickerIntelligenceSummary> {
  return fetchReadOnlyDashboardSummary(
    "/internal/dashboard/ticker-intelligence/NVDA",
    "Ticker Intelligence",
  );
}

export async function fetchLatestAdvisoryChain(): Promise<AdvisoryChainPayload> {
  return fetchAdvisoryChain(LATEST_ADVISORY_CHAIN_ENDPOINT);
}

export async function fetchDemoAdvisoryChain(): Promise<AdvisoryChainPayload> {
  return fetchAdvisoryChain(DEMO_ADVISORY_CHAIN_ENDPOINT);
}

export async function fetchTradeJournalEntries(): Promise<TradeJournalEntry[]> {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS,
  );

  try {
    const response = await fetch(TRADE_JOURNAL_PROXY_ENDPOINT, {
      cache: "no-store",
      method: "GET",
      signal: controller.signal,
    });
    const payload = (await response.json()) as {
      data?: {
        entries?: TradeJournalEntry[];
      };
    };

    if (!response.ok) {
      return [];
    }

    return payload.data?.entries ?? [];
  } catch {
    return [];
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function createTradeJournalEntry(
  input: TradeJournalEntryInput,
): Promise<TradeJournalEntry> {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS,
  );

  try {
    const response = await fetch(TRADE_JOURNAL_PROXY_ENDPOINT, {
      body: JSON.stringify(input),
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      method: "POST",
      signal: controller.signal,
    });
    const payload = (await response.json()) as {
      data?: TradeJournalEntry;
      error?: { message?: string };
    };

    if (!response.ok || !payload.data) {
      throw new Error(
        payload.error?.message ??
          `Trade journal write failed: HTTP ${response.status}`,
      );
    }

    return payload.data;
  } finally {
    window.clearTimeout(timeout);
  }
}

async function fetchAdvisoryChain(
  endpoint: string,
): Promise<AdvisoryChainPayload> {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS,
  );

  try {
    const response = await fetch(backendProxyUrl(endpoint), {
      cache: "no-store",
      method: "GET",
      signal: controller.signal,
    });
    const payload = (await response.json()) as {
      data?: AdvisoryChainPayload;
    };

    if (!response.ok) {
      return unavailableAdvisoryChain(
        `Backend unavailable: HTTP ${response.status}`,
      );
    }

    return payload.data ?? emptyAdvisoryChain();
  } catch (error) {
    const reason = error instanceof Error ? error.message : "request failed";
    return unavailableAdvisoryChain(`Backend unavailable: ${reason}`);
  } finally {
    window.clearTimeout(timeout);
  }
}

async function fetchProbe(endpoint: ProbeEndpoint): Promise<RuntimeProbe> {
  const checkedAt = new Date().toISOString();
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS,
  );

  try {
    const response = await fetch(`${apiBaseUrl()}/${endpoint}`, {
      cache: "no-store",
      signal: controller.signal,
    });
    const payload = (await response.json()) as {
      data?: {
        service?: string;
        status?: string;
        checks?: Record<string, string>;
      };
    };
    const status = payload.data?.status ?? "unknown";
    const databaseStatus = payload.data?.checks?.database;
    const detail =
      endpoint === "ready"
        ? `API readiness ${status}; database ${databaseStatus ?? "not reported"}.`
        : `API health ${status}.`;

    return {
      state: response.ok ? "available" : "unavailable",
      status,
      detail,
      checkedAt,
      sourceLabel: `API /${endpoint}`,
    };
  } catch (error) {
    const reason = error instanceof Error ? error.message : "request failed";
    return {
      state: "unavailable",
      status: "unavailable",
      detail: `Backend unavailable: ${reason}`,
      checkedAt,
      sourceLabel: `API /${endpoint}`,
    };
  } finally {
    window.clearTimeout(timeout);
  }
}

async function fetchReadOnlyDashboardSummary<
  TSummary extends DashboardSummaryFeed,
>(endpoint: DashboardSummaryEndpoint, title: string): Promise<TSummary> {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS,
  );

  try {
    const response = await fetch(backendProxyUrl(endpoint), {
      cache: "no-store",
      method: "GET",
      signal: controller.signal,
    });
    const payload = (await response.json()) as {
      data?: Partial<TSummary>;
    };

    if (!response.ok) {
      return createUnavailableDashboardSummary(
        endpoint,
        title,
        `HTTP ${response.status}`,
      ) as TSummary;
    }

    return normalizeDashboardSummary(
      endpoint,
      title,
      payload.data ?? {},
    ) as TSummary;
  } catch (error) {
    const reason = error instanceof Error ? error.message : "request failed";
    return createUnavailableDashboardSummary(
      endpoint,
      title,
      reason,
    ) as TSummary;
  } finally {
    window.clearTimeout(timeout);
  }
}

function normalizeDashboardSummary<TSummary extends DashboardSummaryFeed>(
  endpoint: DashboardSummaryEndpoint,
  title: string,
  summary: Partial<TSummary>,
): DashboardSummaryFeed {
  return {
    state: summary.state ?? "available",
    status: summary.status ?? "passing",
    title: summary.title ?? title,
    visibleValue: summary.visibleValue ?? "Available",
    detail:
      summary.detail ?? "Live read-only dashboard summary loaded from API.",
    checkedAt: summary.checkedAt ?? new Date().toISOString(),
    sourceLabel: summary.sourceLabel ?? `API ${endpoint}`,
    payload: summary.payload,
  };
}

function createUnavailableDashboardSummary(
  endpoint: DashboardSummaryEndpoint,
  title: string,
  reason: string,
): DashboardSummaryFeed {
  return {
    state: "degraded",
    status: "degraded",
    title,
    visibleValue: "Backend unavailable",
    detail: `Backend unavailable: ${reason}`,
    checkedAt: new Date().toISOString(),
    sourceLabel: `API ${endpoint}`,
  };
}

function emptyAdvisoryChain(): AdvisoryChainPayload {
  return {
    status: "empty",
    chain_id: "latest-local-advisory",
    detail: "No local advisory chain has been produced.",
  };
}

function unavailableAdvisoryChain(detail: string): AdvisoryChainPayload {
  return {
    ...emptyAdvisoryChain(),
    status: "degraded",
    detail,
  };
}
