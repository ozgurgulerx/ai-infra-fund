import { AppShell } from "../../components/app-shell";
import { SectionPanel } from "../../components/section-panel";

export default function TradeIntentsPage() {
  return (
    <div className="control-room-shell">
      <AppShell eyebrow="Manual Planning" title="Manual Trade Intents">
        <div className="workbench-grid">
          <SectionPanel
            eyebrow="Local journal only"
            title="Read-Only Planning Placeholder"
            aside={<span className="readonly-label">No broker connection</span>}
          >
            <div className="audit-stack">
              <div>
                <strong>Manual Trade Intents</strong>
                <span>Intent capture remains disabled in Phase 10 while crawler, evidence, and advisory-run traceability mature.</span>
              </div>
              <div>
                <strong>No local save action</strong>
                <span>This page does not write browser storage, call mutation APIs, or create executable instructions.</span>
              </div>
              <div>
                <strong>Evidence-first planning</strong>
                <span>Use the advisory chain to inspect recommendation_id, evidence_ids, model_run_ids, and audit_id.</span>
              </div>
            </div>
          </SectionPanel>
        </div>
      </AppShell>
    </div>
  );
}
