import { AppShell } from "../../components/app-shell";
import { SectionPanel } from "../../components/section-panel";

export default function IncidentsPage() {
  return (
    <div className="control-room-shell">
      <AppShell eyebrow="Governance" title="Incidents">
        <div className="workbench-grid">
          <SectionPanel eyebrow="Freeze controls" title="Incidents" aside={<span className="readonly-label">Read-only</span>}>
            <div className="status-list">
              <div className="status-list-row">
                <strong>Active freeze</strong>
                <span>None reported by the local dashboard feed.</span>
              </div>
              <div className="status-list-row">
                <strong>Publication policy</strong>
                <span>Invalid, stale, or quarantined evidence suppresses recommendation publication.</span>
              </div>
            </div>
          </SectionPanel>
        </div>
      </AppShell>
    </div>
  );
}
