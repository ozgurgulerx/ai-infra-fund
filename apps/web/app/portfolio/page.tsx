import { AppShell } from "../../components/app-shell";
import { SectionPanel } from "../../components/section-panel";
import { portfolioHoldings } from "../../lib/portfolio-data";

import { ShadowCurveChart } from "./components/shadow-curve-chart";
import { ShadowDriftTable } from "./components/shadow-drift-table";

export default function PortfolioPage() {
  return (
    <div className="control-room-shell">
      <AppShell eyebrow="Portfolio" title="Portfolio Workbench">
        <div className="workbench-grid">
          <SectionPanel
            eyebrow="Read-only"
            title="Portfolio Workbench"
            aside={<span className="advisory-inline">Advisory-only</span>}
          >
            <div
              className="data-table"
              role="table"
              aria-label="Portfolio workbench"
            >
              <div className="data-row data-header" role="row">
                <span>Symbol</span>
                <span>Role</span>
                <span>Bucket</span>
                <span>Current</span>
                <span>Target</span>
                <span>Drift</span>
              </div>
              {portfolioHoldings.map((holding) => (
                <div className="data-row" role="row" key={holding.symbol}>
                  <span>{holding.symbol}</span>
                  <span>{holding.role}</span>
                  <span>{holding.bucket}</span>
                  <span>{holding.currentWeight}</span>
                  <span>{holding.targetWeight}</span>
                  <span>{holding.drift}</span>
                </div>
              ))}
            </div>
            <p className="panel-note">
              Local portfolio import drives advisory analysis only. This page
              has no order, broker, or execution control.
            </p>
          </SectionPanel>

          <SectionPanel
            eyebrow="Shadow simulation"
            title="Counterfactual drift vs. advisory target"
            aside={<span className="advisory-inline">Advisory-only</span>}
          >
            <ShadowDriftTable />
            <p className="panel-note">
              Shadow simulation — advisory only. No order, broker, or execution
              control. Counterfactual prices use only data available
              at-or-before the as-of timestamp.
            </p>
          </SectionPanel>

          <SectionPanel
            eyebrow="Shadow curve"
            title="Counterfactual value curve"
            aside={<span className="advisory-inline">Advisory-only</span>}
          >
            <ShadowCurveChart />
          </SectionPanel>
        </div>
      </AppShell>
    </div>
  );
}
