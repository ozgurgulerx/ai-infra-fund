"use client";

import { useEffect, useMemo, useState } from "react";
import { AppShell } from "../../components/app-shell";
import { HedgeFundComponentMap } from "../../components/hedge-fund-component-map";
import { ModuleGrid } from "../../components/module-grid";
import { SectionPanel } from "../../components/section-panel";
import {
  fetchApiHealth,
  fetchApiReadiness,
  fetchDashboardModules
} from "../../lib/api";
import {
  BASE_MODULES,
  applyLiveModuleSummaries,
  applyRuntimeProbes,
  summarizeModules,
  type DashboardModuleSummary,
  type RuntimeProbe
} from "../../lib/status-model";

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

export default function OpsPage() {
  const [health, setHealth] = useState<RuntimeProbe>(initialHealth);
  const [readiness, setReadiness] = useState<RuntimeProbe>(initialReadiness);
  const [moduleSummaries, setModuleSummaries] = useState<DashboardModuleSummary[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function refreshOpsModules() {
      const [healthResult, readinessResult, liveModules] = await Promise.all([
        fetchApiHealth(),
        fetchApiReadiness(),
        fetchDashboardModules()
      ]);

      if (!cancelled) {
        setHealth(healthResult);
        setReadiness(readinessResult);
        setModuleSummaries(liveModules);
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
    () => applyLiveModuleSummaries(applyRuntimeProbes(BASE_MODULES, health, readiness), moduleSummaries),
    [health, moduleSummaries, readiness]
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
                {summary.passing} passing / {summary.degraded} degraded / {summary.failing} failing / {summary.planned} planned
              </span>
            }
          >
            <HedgeFundComponentMap modules={modules} sourceSummary="Auto-updates from live module summaries" />
            <ModuleGrid modules={modules} />
          </SectionPanel>
        </div>
      </AppShell>
    </div>
  );
}
