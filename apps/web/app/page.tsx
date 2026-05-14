"use client";

import { useEffect, useMemo, useState } from "react";
import { AppShell } from "../components/app-shell";
import { HedgeFundComponentMap } from "../components/hedge-fund-component-map";
import { ModuleGrid } from "../components/module-grid";
import { SectionPanel } from "../components/section-panel";
import { StatusTile } from "../components/status-tile";
import {
  apiBaseUrl,
  fetchApiHealth,
  fetchApiReadiness,
  fetchLatestAdvisoryChain,
  fetchDashboardModules
} from "../lib/api";
import {
  BASE_MODULES,
  applyLiveModuleSummaries,
  applyRuntimeProbes,
  moduleStatusFromSummary,
  summarizeModules,
  type AdvisoryChainPayload,
  type DashboardModuleSummary,
  type DashboardSummaryFeed,
  type ModuleStatus,
  type RuntimeProbe
} from "../lib/status-model";
import { portfolioRows } from "../lib/portfolio-data";

const initialHealth: RuntimeProbe = {
  state: "unavailable",
  status: "unavailable",
  detail: "Backend unavailable: status check has not completed.",
  checkedAt: "pending",
  sourceLabel: "API /health"
};

const initialReadiness: RuntimeProbe = {
  state: "unavailable",
  status: "unavailable",
  detail: "Backend unavailable: readiness check has not completed.",
  checkedAt: "pending",
  sourceLabel: "API /ready"
};

type DashboardFeedKey =
  | "overview"
  | "evidence"
  | "recommendations"
  | "evaluation"
  | "modelRuns"
  | "dataQuality"
  | "incidents"
  | "watchlist"
  | "crawlFreshness"
  | "equityEvents"
  | "signalSnapshots"
  | "advisoryRun"
  | "tickerIntelligence";

type DashboardEndpointConfig = {
  key: DashboardFeedKey;
  endpoint: string;
  title: string;
  plannedDetail: string;
  buildVisibleValue: (payload: DashboardPayload) => string;
  buildDetail: (payload: DashboardPayload) => string;
  statusOverride?: (payload: DashboardPayload) => ModuleStatus | undefined;
};

type DashboardPayload = Record<string, unknown>;
type DashboardFeedMap = Record<DashboardFeedKey, DashboardSummaryFeed<DashboardPayload>>;

const initialAdvisoryChain: AdvisoryChainPayload = {
  status: "empty",
  chain_id: "latest-local-advisory",
  advisory_label: "advisory_only",
  detail: "No local advisory chain has been produced.",
  ids: {
    evidence_id: "evidence-demo-ai-infra-nvda",
    chunk_id: "chunk-demo-ai-infra-nvda-0",
    claim_id: "claim-demo-ai-infra-nvda-demand",
    model_run_ids: ["model-run-demo-local-review"],
    signal_bundle_id: "signal-bundle-demo-nvda",
    target_weights_id: "target-weights-demo-ai-infra",
    recommendation_id: "recommendation-demo-nvda",
    audit_id: "recommendation-audit-demo-nvda",
    backtest_run_id: "evaluation-demo-ai-infra",
    run_artifact_id: "run-demo-advisory-chain"
  }
};
const advisoryChainPath = "Evidence -> Chunk -> Claim -> SignalBundle -> TargetWeights -> Recommendation -> Audit -> Evaluation";

const dashboardEndpointConfigs: DashboardEndpointConfig[] = [
  {
    key: "overview",
    endpoint: "/internal/status/overview",
    title: "Dashboard Feed",
    plannedDetail: "Dashboard repository is configured, but no DB-backed records are available yet.",
    buildVisibleValue: (payload) => String(payload.status ?? "available").toUpperCase(),
    buildDetail: (payload) => {
      const status = String(payload.status ?? "available");
      return status === "empty"
        ? "Repository returned an intentionally empty control-room overview."
        : "Repository overview loaded from read-only dashboard tables.";
    },
    statusOverride: (payload) => (payload.status === "empty" ? "planned" : undefined)
  },
  {
    key: "evidence",
    endpoint: "/internal/dashboard/evidence-summary",
    title: "Evidence",
    plannedDetail: "Evidence tables are reachable, but no ingested records have been reported yet.",
    buildVisibleValue: (payload) => `${readNumber(payload, "total_items")} items`,
    buildDetail: (payload) =>
      `${readNumber(payload, "total_chunks")} chunks, ${readNumber(payload, "total_claims")} claims, latest ${readOptionalText(payload, "latest_created_at")}.`
  },
  {
    key: "recommendations",
    endpoint: "/internal/dashboard/recommendation-summary",
    title: "Recommendations",
    plannedDetail: "Recommendation artifacts are intentionally empty until audited advisory outputs exist.",
    buildVisibleValue: (payload) => `${readNumber(payload, "total_recommendations")} artifacts`,
    buildDetail: (payload) =>
      `${readNumber(payload, "total_audits")} audits, ${readNumber(payload, "schema_valid_audits")} schema-valid, ${readNumber(payload, "schema_invalid_audits")} invalid.`
  },
  {
    key: "evaluation",
    endpoint: "/internal/dashboard/evaluation-summary",
    title: "Evaluation",
    plannedDetail: "Backtest and run-artifact tables are ready; no evaluation output has been published.",
    buildVisibleValue: (payload) => `${readNumber(payload, "total_backtest_runs", "total_backtests")} backtests`,
    buildDetail: (payload) =>
      `${readNumber(payload, "total_run_artifacts")} run artifacts; backtests ${formatBreakdown(payload.backtest_runs_by_status)}.`
  },
  {
    key: "modelRuns",
    endpoint: "/internal/dashboard/model-run-summary",
    title: "Model Runs",
    plannedDetail: "ModelRun ledger is available, with no recorded runs in the current feed.",
    buildVisibleValue: (payload) => `${readNumber(payload, "total_model_runs", "total_runs")} runs`,
    buildDetail: (payload) => `Runs by status: ${formatBreakdown(payload.runs_by_status)}.`
  },
  {
    key: "dataQuality",
    endpoint: "/internal/dashboard/data-quality-summary",
    title: "Data Quality",
    plannedDetail: "Data-quality checks are intentionally empty until scheduled checks publish results.",
    buildVisibleValue: (payload) => `${readNumber(payload, "total_checks")} checks`,
    buildDetail: (payload) =>
      `Status ${formatBreakdown(payload.checks_by_status)}; severity ${formatBreakdown(payload.checks_by_severity)}.`
  },
  {
    key: "incidents",
    endpoint: "/internal/dashboard/incident-summary",
    title: "Incidents",
    plannedDetail: "Incident records are empty; no active freeze is exposed by the feed.",
    buildVisibleValue: (payload) =>
      `${readNumber(payload, "open_incidents")} open / ${readNumber(payload, "total_incidents")} total`,
    buildDetail: (payload) =>
      `Severity ${formatBreakdown(payload.incidents_by_severity)}; freeze ${formatBreakdown(payload.incidents_by_freeze_status)}.`
  },
  {
    key: "watchlist",
    endpoint: "/internal/dashboard/watchlist-summary",
    title: "Watchlist Status",
    plannedDetail: "Watchlist universe is reachable, but no tickers are registered yet.",
    buildVisibleValue: (payload) => `${readNumber(payload, "total_members")} tickers`,
    buildDetail: (payload) => `Status mix: ${formatBreakdown(payload.by_watchlist_status)}.`
  },
  {
    key: "crawlFreshness",
    endpoint: "/internal/dashboard/crawl-frontier-health",
    title: "Crawl Freshness",
    plannedDetail: "No data snapshot frontier has reported freshness yet.",
    buildVisibleValue: (payload) => `${readNumber(payload, "total_datasets")} datasets`,
    buildDetail: (payload) => `Latest available ${readOptionalText(payload, "latest_available_at")}.`
  },
  {
    key: "equityEvents",
    endpoint: "/internal/dashboard/latest-equity-events",
    title: "Latest Equity Events",
    plannedDetail: "No equity evidence events are available in the local feed.",
    buildVisibleValue: (payload) => `${readArray(payload, "events").length} events`,
    buildDetail: (payload) => eventHeadline(readArray(payload, "events"))
  },
  {
    key: "signalSnapshots",
    endpoint: "/internal/dashboard/latest-signal-snapshots",
    title: "Sentiment / Technical / Fundamental",
    plannedDetail: "No deterministic signal snapshots are available yet.",
    buildVisibleValue: (payload) => `${readArray(payload, "snapshots").length} score cards`,
    buildDetail: (payload) => signalHeadline(readArray(payload, "snapshots"))
  },
  {
    key: "advisoryRun",
    endpoint: "/internal/dashboard/latest-advisory-run",
    title: "Latest Advisory Run",
    plannedDetail: "No local advisory run has been produced.",
    buildVisibleValue: (payload) => readOptionalText(payload, "run_status"),
    buildDetail: (payload) =>
      `${readOptionalText(payload, "run_id")} / advisory_label ${readOptionalText(payload, "advisory_label")}.`
  },
  {
    key: "tickerIntelligence",
    endpoint: "/internal/dashboard/ticker-intelligence/NVDA",
    title: "Ticker Intelligence",
    plannedDetail: "No local intelligence summary exists for NVDA yet.",
    buildVisibleValue: (payload) => readOptionalText(payload, "ticker"),
    buildDetail: (payload) => tickerTraceHeadline(payload)
  }
];

const initialDashboardFeeds = Object.fromEntries(
  dashboardEndpointConfigs.map((config) => [
    config.key,
    createPlannedDashboardFeed(config)
  ])
) as DashboardFeedMap;

export default function Page() {
  const [health, setHealth] = useState<RuntimeProbe>(initialHealth);
  const [readiness, setReadiness] = useState<RuntimeProbe>(initialReadiness);
  const [dashboardFeeds, setDashboardFeeds] = useState<DashboardFeedMap>(initialDashboardFeeds);
  const [moduleSummaries, setModuleSummaries] = useState<DashboardModuleSummary[]>([]);
  const [advisoryChain, setAdvisoryChain] = useState<AdvisoryChainPayload>(initialAdvisoryChain);

  useEffect(() => {
    let cancelled = false;

    async function refreshStatus() {
      const [healthResult, readinessResult] = await Promise.all([
        fetchApiHealth(),
        fetchApiReadiness()
      ]);

      if (!cancelled) {
        setHealth(healthResult);
        setReadiness(readinessResult);
      }
    }

    void refreshStatus();
    const interval = window.setInterval(refreshStatus, 30000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function refreshDashboardFeeds() {
      const [feeds, liveModules, chain] = await Promise.all([
        fetchDashboardFeedMap(),
        fetchDashboardModules(),
        fetchLatestAdvisoryChain()
      ]);

      if (!cancelled) {
        setDashboardFeeds(feeds);
        setModuleSummaries(liveModules);
        setAdvisoryChain(chain);
      }
    }

    void refreshDashboardFeeds();
    const interval = window.setInterval(refreshDashboardFeeds, 30000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const modules = useMemo(
    () => applyLiveModuleSummaries(applyRuntimeProbes(BASE_MODULES, health, readiness), moduleSummaries),
    [health, moduleSummaries, readiness]
  );
  const summary = summarizeModules(modules);

  return (
    <AppShell eyebrow="Local Read-Only Dashboard" title="AI Infrastructure Fund Control Room">
      <div className="control-room-shell">
      <section className="status-strip" aria-label="System Status">
        <StatusTile
          title="System Status"
          status={health.state === "available" ? "passing" : "failing"}
          metric={health.status.toUpperCase()}
          detail={health.detail}
          source={health.sourceLabel}
        />
        <StatusTile
          title="Readiness"
          status={readiness.state === "available" && readiness.status === "ready" ? "passing" : "degraded"}
          metric={readiness.status.toUpperCase()}
          detail={readiness.detail}
          source={readiness.sourceLabel}
        />
        <StatusTile
          title={dashboardFeeds.overview.title}
          status={dashboardFeeds.overview.status}
          metric={dashboardFeeds.overview.visibleValue}
          detail={dashboardFeeds.overview.detail}
          source={dashboardFeeds.overview.sourceLabel}
        />
      </section>

      <div className="dashboard-grid">
        <SectionPanel
          eyebrow="Portfolio"
          title="Portfolio Snapshot"
          aside={<span className="readonly-label">Planned feed</span>}
        >
          <div className="portfolio-table" role="table" aria-label="Portfolio">
            <div role="row" className="portfolio-row portfolio-header">
              <span>Symbol</span>
              <span>Role</span>
              <span>Class</span>
              <span>Weight</span>
            </div>
            {portfolioRows.map(([symbol, role, bucket, weight]) => (
              <div role="row" className="portfolio-row" key={symbol}>
                <span>{symbol}</span>
                <span>{role}</span>
                <span>{bucket}</span>
                <span>{weight}</span>
              </div>
            ))}
          </div>
          <p className="panel-note">
            Portfolio rows remain a static planning snapshot until a read-only portfolio summary feed is exposed. Manual trade
            entry and Trade Journal views stay disabled in this read-only phase.
          </p>
        </SectionPanel>

        <SectionPanel
          eyebrow="Recommendations"
          title="Audit Status"
          aside={<span className="advisory-inline">Advisory-only</span>}
        >
          <div className="audit-stack">
            <div>
              <strong>Publication gate</strong>
              <span>Evidence IDs, Model Runs, SignalBundle, TargetWeights, and deterministic checks required.</span>
            </div>
            <div>
              <strong>Current UI mode</strong>
              <span>No recommendation generation from the browser; artifacts remain read-only.</span>
            </div>
            <div>
              <strong>Read-only boundary</strong>
              <span>No transaction controls, venue links, credentials, or submission surface.</span>
            </div>
          </div>
        </SectionPanel>

        <SectionPanel
          eyebrow="End-to-End"
          title="Latest Advisory Chain"
          aside={<span className="advisory-inline">Advisory-only</span>}
        >
          <div className="compact-list">
            <p className="chain-path">
              {advisoryChainPath}
            </p>
            <p>
              <strong>{chainHeadline(advisoryChain)}</strong> {chainDetail(advisoryChain)}
            </p>
          </div>
          <div className="status-list chain-list">
            <ChainLinkRow label="evidence_id" value={chainId(advisoryChain, "evidence_id")} />
            <ChainLinkRow label="chunk_id" value={chainId(advisoryChain, "chunk_id")} />
            <ChainLinkRow label="claim_id" value={chainId(advisoryChain, "claim_id")} />
            <ChainLinkRow label="model_run_ids" value={chainId(advisoryChain, "model_run_ids")} />
            <ChainLinkRow label="signal_bundle_id" value={chainId(advisoryChain, "signal_bundle_id")} />
            <ChainLinkRow label="target_weights_id" value={chainId(advisoryChain, "target_weights_id")} />
            <ChainLinkRow label="recommendation_id" value={chainId(advisoryChain, "recommendation_id")} />
            <ChainLinkRow label="audit_id" value={chainId(advisoryChain, "audit_id")} />
            <ChainLinkRow label="evaluation" value={chainEvaluation(advisoryChain)} />
          </div>
        </SectionPanel>

        <SectionPanel eyebrow="Universe" title="Watchlist Status">
          <div className="compact-list">
            <p>
              <strong>{dashboardFeeds.watchlist.visibleValue}</strong> {dashboardFeeds.watchlist.detail}
            </p>
            <p>{dashboardFeeds.watchlist.sourceLabel}</p>
          </div>
        </SectionPanel>

        <SectionPanel eyebrow="Freshness" title="Crawl Freshness">
          <div className="compact-list">
            <p>
              <strong>{dashboardFeeds.crawlFreshness.visibleValue}</strong> {dashboardFeeds.crawlFreshness.detail}
            </p>
            <p>{dashboardFeeds.crawlFreshness.sourceLabel}</p>
          </div>
        </SectionPanel>

        <SectionPanel eyebrow="Events" title="Latest Equity Events">
          <div className="compact-list">
            <p>
              <strong>{dashboardFeeds.equityEvents.visibleValue}</strong> {dashboardFeeds.equityEvents.detail}
            </p>
            <p>{dashboardFeeds.equityEvents.sourceLabel}</p>
          </div>
        </SectionPanel>

        <SectionPanel eyebrow="Scores" title="Sentiment / Technical / Fundamental">
          <div className="status-list">
            {scoreCards(dashboardFeeds.signalSnapshots.payload).map((card) => (
              <div className="status-list-row" key={card.label}>
                <strong>{card.label}</strong>
                <span>{card.value}</span>
              </div>
            ))}
          </div>
        </SectionPanel>

        <SectionPanel
          eyebrow="Advisory"
          title="Latest Advisory Run"
          aside={<span className="advisory-inline">Advisory-only</span>}
        >
          <div className="compact-list">
            <p>
              <strong>{dashboardFeeds.advisoryRun.visibleValue}</strong> {dashboardFeeds.advisoryRun.detail}
            </p>
            <p>{dashboardFeeds.advisoryRun.sourceLabel}</p>
          </div>
        </SectionPanel>

        <SectionPanel eyebrow="Ticker" title="Ticker Intelligence">
          <div className="compact-list">
            <p>
              <strong>{dashboardFeeds.tickerIntelligence.visibleValue}</strong> {dashboardFeeds.tickerIntelligence.detail}
            </p>
            <p>{dashboardFeeds.tickerIntelligence.sourceLabel}</p>
          </div>
        </SectionPanel>

        <SectionPanel eyebrow="Traceability" title="Evidence And Audit Trace">
          <div className="status-list">
            <TraceRow label="evidence_ids" value={traceValue(dashboardFeeds.tickerIntelligence.payload, "evidence_ids")} />
            <TraceRow label="model_run_ids" value={traceValue(dashboardFeeds.tickerIntelligence.payload, "model_run_ids")} />
            <TraceRow label="audit_id" value={chainId(advisoryChain, "audit_id")} />
          </div>
        </SectionPanel>

        <SectionPanel eyebrow="Evidence" title="Evidence Ingestion Status">
          <div className="compact-list">
            <p>
              <strong>{dashboardFeeds.evidence.visibleValue}</strong> {dashboardFeeds.evidence.detail}
            </p>
            <p>{dashboardFeeds.evidence.sourceLabel}</p>
          </div>
        </SectionPanel>

        <SectionPanel eyebrow="Evaluation" title="Backtest And Evaluation">
          <div className="compact-list">
            <p>
              <strong>{dashboardFeeds.evaluation.visibleValue}</strong> {dashboardFeeds.evaluation.detail}
            </p>
            <p>{dashboardFeeds.evaluation.sourceLabel}</p>
          </div>
        </SectionPanel>

        <SectionPanel eyebrow="Operations" title="Model Runs, Data Quality, Incidents">
          <div className="status-list">
            <DashboardFeedRow feed={dashboardFeeds.recommendations} />
            <DashboardFeedRow feed={dashboardFeeds.modelRuns} />
            <DashboardFeedRow feed={dashboardFeeds.dataQuality} />
            <DashboardFeedRow feed={dashboardFeeds.incidents} />
          </div>
        </SectionPanel>
      </div>

      <section className="ops-room" aria-label="System Architecture">
        <div className="section-heading">
          <div>
            <p className="eyebrow">System Architecture</p>
            <h2>Trading System Ops Room</h2>
          </div>
          <span className="readonly-label">
            {summary.passing} passing / {summary.degraded} degraded / {summary.failing} failing / {summary.planned} planned
          </span>
        </div>
        <HedgeFundComponentMap
          modules={modules}
          sourceSummary="Auto-updates from live module summaries"
        />
        <ModuleGrid modules={modules} />
      </section>
      </div>
    </AppShell>
  );
}

function DashboardFeedRow({ feed }: { feed: DashboardSummaryFeed<DashboardPayload> }) {
  return (
    <div className="status-list-row">
      <strong>{feed.title}</strong>
      <span>
        {feed.visibleValue} - {feed.detail}
      </span>
      <span>{feed.sourceLabel}</span>
    </div>
  );
}

function ChainLinkRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="status-list-row">
      <strong>{label}</strong>
      <span className="chain-id">{value}</span>
    </div>
  );
}

function TraceRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="status-list-row">
      <strong>{label}</strong>
      <span className="chain-id">{value}</span>
    </div>
  );
}

function chainHeadline(chain: AdvisoryChainPayload): string {
  if (chain.status === "available") {
    return `${textValue(chain.recommendation, "action", "advisory")} / ${textValue(chain.recommendation, "horizon", "horizon")}`;
  }
  if (chain.status === "empty") {
    return "Planned";
  }
  return "Degraded";
}

function chainDetail(chain: AdvisoryChainPayload): string {
  if (chain.status === "available") {
    return `${textValue(chain.recommendation, "advisory_label", chain.advisory_label ?? "advisory_only")} recommendation linked through ${chain.chain_id}.`;
  }
  return chain.detail ?? "No local advisory chain has been produced.";
}

function chainId(chain: AdvisoryChainPayload, key: string): string {
  const value = chain.ids?.[key];
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (typeof value === "string" && value.length > 0) {
    return value;
  }
  return "not reported";
}

function chainEvaluation(chain: AdvisoryChainPayload): string {
  const backtestId = chainId(chain, "backtest_run_id");
  const runArtifactId = chainId(chain, "run_artifact_id");
  const status = textValue(chain.evaluation, "status", "not reported");
  return `${backtestId} / ${runArtifactId} / ${status}`;
}

async function fetchDashboardFeedMap(): Promise<DashboardFeedMap> {
  const entries = await Promise.all(
    dashboardEndpointConfigs.map(async (config) => [config.key, await fetchDashboardFeed(config)] as const)
  );

  return Object.fromEntries(entries) as DashboardFeedMap;
}

async function fetchDashboardFeed(config: DashboardEndpointConfig): Promise<DashboardSummaryFeed<DashboardPayload>> {
  const checkedAt = new Date().toISOString();
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 2500);

  try {
    const response = await fetch(`${apiBaseUrl()}${config.endpoint}`, {
      cache: "no-store",
      method: "GET",
      signal: controller.signal
    });
    const envelope = (await response.json()) as { data?: DashboardPayload };

    if (!response.ok) {
      return createDegradedDashboardFeed(config, `Backend unavailable: HTTP ${response.status}`, checkedAt);
    }

    return normalizeDashboardFeed(config, envelope.data ?? {}, checkedAt);
  } catch (error) {
    const reason = error instanceof Error ? error.message : "request failed";
    return createDegradedDashboardFeed(config, `Backend unavailable: ${reason}`, checkedAt);
  } finally {
    window.clearTimeout(timeout);
  }
}

function normalizeDashboardFeed(
  config: DashboardEndpointConfig,
  payload: DashboardPayload,
  checkedAt: string
): DashboardSummaryFeed<DashboardPayload> {
  const sourceLabel = `API ${config.endpoint}`;
  const status = config.statusOverride?.(payload) ?? moduleStatusFromSummary(readOptionalText(payload, "status"));
  const isPlanned = status === "planned" || feedHasNoRecords(payload);

  if (isPlanned) {
    return {
      state: "available",
      status: "planned",
      title: config.title,
      visibleValue: "Planned",
      detail: config.plannedDetail,
      checkedAt,
      sourceLabel,
      payload
    };
  }

  return {
    state: status === "failing" ? "degraded" : "available",
    status,
    title: config.title,
    visibleValue: config.buildVisibleValue(payload),
    detail: config.buildDetail(payload),
    checkedAt,
    sourceLabel,
    payload
  };
}

function createPlannedDashboardFeed(config: DashboardEndpointConfig): DashboardSummaryFeed<DashboardPayload> {
  return {
    state: "available",
    status: "planned",
    title: config.title,
    visibleValue: "Planned",
    detail: config.plannedDetail,
    checkedAt: "pending",
    sourceLabel: `API ${config.endpoint}`
  };
}

function createDegradedDashboardFeed(
  config: DashboardEndpointConfig,
  detail: string,
  checkedAt: string
): DashboardSummaryFeed<DashboardPayload> {
  return {
    state: "degraded",
    status: "degraded",
    title: config.title,
    visibleValue: "Backend unavailable",
    detail,
    checkedAt,
    sourceLabel: `API ${config.endpoint}`
  };
}

function readNumber(payload: DashboardPayload, ...keys: string[]): number {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === "number") {
      return value;
    }
  }

  return 0;
}

function readOptionalText(payload: DashboardPayload, key: string): string {
  const value = payload[key];
  return typeof value === "string" && value.length > 0 ? value : "not reported";
}

function readArray(payload: DashboardPayload, key: string): Record<string, unknown>[] {
  const value = payload[key];
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function textValue(payload: Record<string, unknown> | undefined, key: string, fallback: string): string {
  const value = payload?.[key];
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

function eventHeadline(events: Record<string, unknown>[]): string {
  const first = events[0];
  return first ? `${textValue(first, "title", "Untitled event")} / ${textValue(first, "evidence_id", "no evidence_id")}.` : "No events reported.";
}

function signalHeadline(snapshots: Record<string, unknown>[]): string {
  const first = snapshots[0];
  return first
    ? `${textValue(first, "ticker", "ticker")} sentiment_score ${textValue(first, "sentiment_score", "n/a")}, technical_score ${textValue(first, "technical_score", "n/a")}, fundamental_score ${textValue(first, "fundamental_score", "n/a")}.`
    : "No score cards reported.";
}

function tickerTraceHeadline(payload: DashboardPayload): string {
  const recommendation = isRecord(payload.latest_recommendation) ? payload.latest_recommendation : undefined;
  return recommendation
    ? `${textValue(recommendation, "action", "action")} / advisory_label ${textValue(recommendation, "advisory_label", "advisory_only")}.`
    : "No advisory recommendation trace reported.";
}

function scoreCards(payload: DashboardPayload | undefined) {
  const snapshot = payload ? readArray(payload, "snapshots")[0] : undefined;
  return [
    { label: "sentiment_score", value: textValue(snapshot, "sentiment_score", "not reported") },
    { label: "technical_score", value: textValue(snapshot, "technical_score", "not reported") },
    { label: "fundamental_score", value: textValue(snapshot, "fundamental_score", "not reported") }
  ];
}

function traceValue(payload: DashboardPayload | undefined, key: string): string {
  const recommendation = payload && isRecord(payload.latest_recommendation) ? payload.latest_recommendation : undefined;
  const value = recommendation?.[key];
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (typeof value === "string") {
    return value;
  }
  return "not reported";
}

function formatBreakdown(value: unknown): string {
  if (!isRecord(value) || Object.keys(value).length === 0) {
    return "none reported";
  }

  return Object.entries(value)
    .map(([key, count]) => `${key} ${String(count)}`)
    .join(", ");
}

function feedHasNoRecords(payload: DashboardPayload): boolean {
  const totalEntries = Object.entries(payload).filter(([key, value]) => key.startsWith("total_") && typeof value === "number");
  return totalEntries.length > 0 && totalEntries.every(([, value]) => value === 0);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
