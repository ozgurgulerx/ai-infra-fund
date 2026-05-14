import { AppShell } from "../../components/app-shell";
import { SectionPanel } from "../../components/section-panel";

export default function EvaluationPage() {
  return (
    <div className="control-room-shell">
      <AppShell eyebrow="Evaluation" title="Evaluation">
        <div className="workbench-grid">
          <SectionPanel eyebrow="Harness" title="Evaluation" aside={<span className="readonly-label">Point-in-time safe</span>}>
            <div className="status-list">
              <div className="status-list-row">
                <strong>Walk-forward</strong>
                <span>Chronological splits with embargo checks.</span>
              </div>
              <div className="status-list-row">
                <strong>Monte Carlo</strong>
                <span>Deterministic seeded stress metrics.</span>
              </div>
              <div className="status-list-row">
                <strong>Benchmark</strong>
                <span>Relative return, drawdown, and volatility comparisons.</span>
              </div>
            </div>
          </SectionPanel>
        </div>
      </AppShell>
    </div>
  );
}
