"use client";

import { useEffect, useMemo, useState } from "react";
import { AppShell } from "../../components/app-shell";
import { HedgeFundComponentMap } from "../../components/hedge-fund-component-map";
import { ModuleGrid } from "../../components/module-grid";
import { SectionPanel } from "../../components/section-panel";
import {
  fetchApiHealth,
  fetchApiReadiness,
  fetchCrawlActivity,
  fetchDashboardModules,
  type CrawlActivitySummary,
} from "../../lib/api";
import {
  BASE_MODULES,
  applyLiveModuleSummaries,
  applyRuntimeProbes,
  summarizeModules,
  type DashboardModuleSummary,
  type RuntimeProbe,
} from "../../lib/status-model";

const initialHealth: RuntimeProbe = {
  state: "unavailable",
  status: "unavailable",
  detail: "Backend unavailable: status check has not completed.",
  checkedAt: "pending",
  sourceLabel: "API /health",
};

const initialReadiness: RuntimeProbe = {
  state: "unavailable",
  status: "unavailable",
  detail: "Backend unavailable: readiness check has not completed.",
  checkedAt: "pending",
  sourceLabel: "API /ready",
};

export default function OpsPage() {
  const [health, setHealth] = useState<RuntimeProbe>(initialHealth);
  const [readiness, setReadiness] = useState<RuntimeProbe>(initialReadiness);
  const [moduleSummaries, setModuleSummaries] = useState<
    DashboardModuleSummary[]
  >([]);
  const [crawlActivity, setCrawlActivity] =
    useState<CrawlActivitySummary | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function refreshOpsModules() {
      const [healthResult, readinessResult, liveModules, crawl] =
        await Promise.all([
          fetchApiHealth(),
          fetchApiReadiness(),
          fetchDashboardModules(),
          fetchCrawlActivity(),
        ]);

      if (!cancelled) {
        setHealth(healthResult);
        setReadiness(readinessResult);
        setModuleSummaries(liveModules);
        setCrawlActivity(crawl);
      }
    }

    void refreshOpsModules();
    const interval = window.setInterval(refreshOpsModules, 30000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const modules = useMemo(
    () =>
      applyLiveModuleSummaries(
        applyRuntimeProbes(BASE_MODULES, health, readiness),
        moduleSummaries,
      ),
    [health, moduleSummaries, readiness],
  );
  const summary = summarizeModules(modules);

  return (
    <div className="control-room-shell">
      <AppShell eyebrow="Operations" title="Ops Room">
        <div className="workbench-grid">
          <SectionPanel
            eyebrow="System Architecture"
            title="Ops Room"
            aside={
              <span className="readonly-label">
                {summary.passing} passing / {summary.degraded} degraded /{" "}
                {summary.failing} failing / {summary.planned} planned
              </span>
            }
          >
            <HedgeFundComponentMap
              modules={modules}
              sourceSummary="Auto-updates from live module summaries"
            />
            <ModuleGrid modules={modules} />
          </SectionPanel>
          <SectionPanel
            eyebrow="Crawl Activity"
            title="Last 24h"
            aside={
              <span className="readonly-label">
                API /internal/dashboard/crawl-activity
              </span>
            }
          >
            {crawlActivity === null ? (
              <p className="readonly-label">
                Crawl activity unavailable. Worker may be idle or backend
                unreachable.
              </p>
            ) : (
              <dl className="crawl-activity-grid">
                <div>
                  <dt>Total attempts</dt>
                  <dd>{crawlActivity.total}</dd>
                </div>
                <div>
                  <dt>Succeeded (2xx)</dt>
                  <dd>{crawlActivity.succeeded}</dd>
                </div>
                <div>
                  <dt>Not modified (304)</dt>
                  <dd>{crawlActivity.not_modified}</dd>
                </div>
                <div>
                  <dt>Client error (4xx)</dt>
                  <dd>{crawlActivity.client_error}</dd>
                </div>
                <div>
                  <dt>Server error (5xx)</dt>
                  <dd>{crawlActivity.server_error}</dd>
                </div>
                <div>
                  <dt>Transport failed</dt>
                  <dd>{crawlActivity.failed}</dd>
                </div>
              </dl>
            )}
          </SectionPanel>
        </div>
      </AppShell>
    </div>
  );
}
