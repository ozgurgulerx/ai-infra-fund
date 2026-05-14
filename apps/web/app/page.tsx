"use client";

import { useEffect, useMemo, useState } from "react";
import { ModuleGrid } from "../components/module-grid";
import { SectionPanel } from "../components/section-panel";
import { StatusTile } from "../components/status-tile";
import {
  apiBaseUrl,
  fetchApiHealth,
  fetchApiReadiness,
  fetchDashboardModules
} from "../lib/api";
import {
  BASE_MODULES,
  applyLiveModuleSummaries,
  applyRuntimeProbes,
  moduleStatusFromSummary,
  summarizeModules,
  type DashboardModuleSummary,
  type DashboardSummaryFeed,
  type ModuleStatus,
  type RuntimeProbe
} from "../lib/status-model";

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

const portfolioRows = [
  ["MSFT", "AI platform and cloud capex", "Core", "23.19%"],
  ["NVDA", "AI accelerator leader", "Core", "9.67%"],
  ["SMCI", "AI server hardware", "Active risk", "5.21%"],
  ["ARM", "CPU/IP layer", "Satellite", "7.89%"],
  ["Cash", "Dry powder and risk buffer", "Reserve", "51.38%"]
];

type DashboardFeedKey =
  | "overview"
  | "evidence"
  | "recommendations"
  | "evaluation"
  | "modelRuns"
  | "dataQuality"
  | "incidents";

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
      const [feeds, liveModules] = await Promise.all([
        fetchDashboardFeedMap(),
        fetchDashboardModules()
      ]);

      if (!cancelled) {
        setDashboardFeeds(feeds);
        setModuleSummaries(liveModules);
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
    <main className="control-room-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Local Read-Only Dashboard</p>
          <h1>AI Infrastructure Fund Control Room</h1>
        </div>
        <div className="advisory-badge">Advisory-only</div>
      </header>

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
              <strong>Execution boundary</strong>
              <span>No routing controls, venue links, credentials, or transaction submission surface.</span>
            </div>
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
        <ModuleGrid modules={modules} />
      </section>
    </main>
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
