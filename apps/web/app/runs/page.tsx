import { AppShell } from "../../components/app-shell";
import { SectionPanel } from "../../components/section-panel";
import { systemRunRows } from "../../lib/portfolio-data";

export default function RunsPage() {
  return (
    <div className="control-room-shell">
      <AppShell eyebrow="Runs" title="Runs">
        <div className="workbench-grid">
          <SectionPanel eyebrow="Latest Advisory Run" title="Runs" aside={<span className="advisory-inline">Advisory-only</span>}>
            <div className="data-table data-table-three" role="table" aria-label="Runs">
              <div className="data-row data-header" role="row">
                <span>Name</span>
                <span>ID</span>
                <span>Status</span>
              </div>
              {systemRunRows.map(([name, id, status]) => (
                <div className="data-row" role="row" key={id}>
                  <span>{name}</span>
                  <span>{id}</span>
                  <span>{status}</span>
                </div>
              ))}
            </div>
          </SectionPanel>
        </div>
      </AppShell>
    </div>
  );
}
