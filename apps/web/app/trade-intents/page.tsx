import { AppShell } from "../../components/app-shell";
import {
  AdvisoryPill,
  RiskFlags,
} from "../../components/daily-cockpit/evidence-pills";
import { EvidenceDrawer, SectionCard, StatusChip } from "../../components/workstation";
import { mockWorkstationData } from "../../lib/situational-awareness/mock-workstation-data";

export default function TradeIntentsPage() {
  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Manual Planning"
        title="Manual Trade Intents"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <div className="workstation-grid workstation-grid-2">
          <SectionCard
            badge={<StatusChip label="No broker connection" tone="neutral" />}
            eyebrow="Local journal only"
            title="Planning queue from suggested actions"
          >
            <p className="panel-note">
              Intent capture remains an advisory review surface. It does not write
              browser storage, call order APIs, or create market instructions.
            </p>
            <div className="wave2-stack">
              {mockWorkstationData.suggestedActions.map((action) => (
                <article className="wave2-list-card" key={action.actionId}>
                  <div>
                    <strong>{action.ticker}</strong>
                    <AdvisoryPill label={action.advisoryLabel} />
                  </div>
                  <p>{action.analystAction}</p>
                  <RiskFlags flags={action.riskFlags} />
                  <div className="wave2-invalidation">
                    <strong>Invalidation</strong>
                    <span>{action.invalidationCondition}</span>
                  </div>
                </article>
              ))}
            </div>
            <EvidenceDrawer
              ids={mockWorkstationData.suggestedActions.flatMap(
                (action) => action.evidenceIds,
              )}
            />
          </SectionCard>

          <SectionCard
            eyebrow="Trade plan linkage"
            title="Evidence before manual action"
          >
            <div className="wave2-stack">
              {mockWorkstationData.openTradePlans.map((plan) => (
                <article className="wave2-list-card" key={plan.tradePlanId}>
                  <div>
                    <strong>{plan.ticker}</strong>
                    <span>{plan.tradePlanId}</span>
                  </div>
                  <p>{plan.thesis}</p>
                  <span>{plan.positionSizingNote}</span>
                </article>
              ))}
            </div>
          </SectionCard>
        </div>
      </AppShell>
    </div>
  );
}
