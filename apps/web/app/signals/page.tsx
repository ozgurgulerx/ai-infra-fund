import { AppShell } from "../../components/app-shell";
import { SectionPanel } from "../../components/section-panel";
import { tickerSignals } from "../../lib/portfolio-data";

export default function SignalsPage() {
  return (
    <div className="control-room-shell">
      <AppShell eyebrow="Deterministic Scores" title="Signals">
        <div className="workbench-grid">
          <SectionPanel eyebrow="Scores" title="Sentiment / Technical / Fundamental" aside={<span className="readonly-label">Versioned formulas</span>}>
            <div className="status-list">
              {tickerSignals.map((signal) => (
                <div className="status-list-row" key={signal.label}>
                  <strong>{signal.label}</strong>
                  <span>{signal.value}</span>
                  <span>{signal.source}</span>
                </div>
              ))}
            </div>
          </SectionPanel>
        </div>
      </AppShell>
    </div>
  );
}
