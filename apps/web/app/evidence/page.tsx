import { AppShell } from "../../components/app-shell";
import { SectionPanel } from "../../components/section-panel";

export default function EvidencePage() {
  return (
    <div className="control-room-shell">
      <AppShell eyebrow="Evidence" title="Evidence Library">
        <div className="workbench-grid">
          <SectionPanel eyebrow="Provenance" title="Evidence And Audit Trace" aside={<span className="readonly-label">Read-only</span>}>
            <div className="status-list">
              <div className="status-list-row">
                <strong>evidence_ids</strong>
                <span>Linked from latest advisory chain when available.</span>
              </div>
              <div className="status-list-row">
                <strong>model_run_ids</strong>
                <span>Deterministic/no-model marker or audited model runs only.</span>
              </div>
              <div className="status-list-row">
                <strong>audit_id</strong>
                <span>Recommendation publication remains advisory-only.</span>
              </div>
            </div>
          </SectionPanel>
        </div>
      </AppShell>
    </div>
  );
}
