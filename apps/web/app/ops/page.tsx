import { AppShell } from "../../components/app-shell";
import { ModuleGrid } from "../../components/module-grid";
import { SectionPanel } from "../../components/section-panel";
import { BASE_MODULES } from "../../lib/status-model";

export default function OpsPage() {
  return (
    <div className="control-room-shell">
      <AppShell eyebrow="Operations" title="Ops Room">
        <div className="workbench-grid">
          <SectionPanel eyebrow="System Architecture" title="Ops Room" aside={<span className="readonly-label">Module health</span>}>
            <ModuleGrid modules={BASE_MODULES} />
          </SectionPanel>
        </div>
      </AppShell>
    </div>
  );
}
