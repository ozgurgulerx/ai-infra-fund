"use client";

import { useEffect, useMemo, useState } from "react";
import { ModuleGrid } from "../components/module-grid";
import { SectionPanel } from "../components/section-panel";
import { StatusTile } from "../components/status-tile";
import { fetchApiHealth, fetchApiReadiness } from "../lib/api";
import {
  BASE_MODULES,
  applyRuntimeProbes,
  summarizeModules,
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

const statusRows = [
  ["Evidence", "Local ingestion foundation exists; claim extraction is audited and local-safe."],
  ["Recommendations", "Artifacts require evidence IDs, model run IDs, signal bundle ID, and target weights ID."],
  ["Evaluation", "Walk-forward, leakage, costs, stress, benchmark, and shadow-mode helpers are implemented."],
  ["Model Runs", "ModelRun ledger and data-class routing policy are available; no live model calls in this UI."],
  ["Data Quality", "Incident and quality records are schema-backed; live dashboard feeds are still planned."],
  ["Incidents", "No active freeze is exposed to the UI yet; this panel remains read-only."]
];

export default function Page() {
  const [health, setHealth] = useState<RuntimeProbe>(initialHealth);
  const [readiness, setReadiness] = useState<RuntimeProbe>(initialReadiness);

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

  const modules = useMemo(() => applyRuntimeProbes(BASE_MODULES, health, readiness), [health, readiness]);
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
          title="Module Health"
          status={summary.failing > 0 ? "failing" : summary.degraded > 0 ? "degraded" : "passing"}
          metric={`${summary.passing} passing`}
          detail={`${summary.degraded} degraded, ${summary.failing} failing, ${summary.planned} planned modules.`}
          source="Status model plus live health probes"
        />
      </section>

      <div className="dashboard-grid">
        <SectionPanel
          eyebrow="Portfolio"
          title="Portfolio Snapshot"
          aside={<span className="readonly-label">Read-only placeholder</span>}
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
            Manual trade entry and Trade Journal views are local-journal only and stay disabled in this read-only phase.
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
            <p>Manual and file evidence foundations are implemented with content hashes and span references.</p>
            <p>Private research stays local by default; cloud-assisted extraction must be audited through ModelRun records.</p>
          </div>
        </SectionPanel>

        <SectionPanel eyebrow="Evaluation" title="Backtest And Evaluation">
          <div className="compact-list">
            <p>Evaluation Harness includes walk-forward splits, lookahead checks, recursive checks, stress, costs, and benchmarks.</p>
            <p>Shadow-mode outputs are isolated and cannot alter production recommendation IDs.</p>
          </div>
        </SectionPanel>

        <SectionPanel eyebrow="Operations" title="Model Runs, Data Quality, Incidents">
          <div className="status-list">
            {statusRows.map(([label, detail]) => (
              <div className="status-list-row" key={label}>
                <strong>{label}</strong>
                <span>{detail}</span>
              </div>
            ))}
          </div>
        </SectionPanel>
      </div>

      <section className="ops-room" aria-label="System Architecture">
        <div className="section-heading">
          <div>
            <p className="eyebrow">System Architecture</p>
            <h2>Trading System Ops Room</h2>
          </div>
          <span className="readonly-label">Module colors require source evidence</span>
        </div>
        <ModuleGrid modules={modules} />
      </section>
    </main>
  );
}
