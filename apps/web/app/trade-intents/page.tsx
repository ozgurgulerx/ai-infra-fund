import { AppShell } from "../../components/app-shell";
import {
  AdvisoryPill,
  EvidencePills,
  RiskFlags,
} from "../../components/daily-cockpit/evidence-pills";
import { mockWorkstationData } from "../../lib/situational-awareness/mock-workstation-data";

export default function TradeIntentsPage() {
  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Manual Planning"
        title="Manual Trade Intents"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <div className="wave2-grid wave2-grid-2">
          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Local journal only</p>
                <h2>Planning queue from suggested actions</h2>
              </div>
              <span className="readonly-label">No broker connection</span>
            </div>
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
                  <EvidencePills ids={action.evidenceIds} />
                </article>
              ))}
            </div>
          </section>

          <section className="section-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Trade plan linkage</p>
                <h2>Evidence before manual action</h2>
              </div>
            </div>
            <div className="wave2-stack">
              {mockWorkstationData.openTradePlans.map((plan) => (
                <article className="wave2-list-card" key={plan.tradePlanId}>
                  <div>
                    <strong>{plan.ticker}</strong>
                    <span>{plan.tradePlanId}</span>
                  </div>
                  <p>{plan.thesis}</p>
                  <span>{plan.positionSizingNote}</span>
                  <EvidencePills ids={plan.evidenceIds} />
                </article>
              ))}
            </div>
          </section>
        </div>
      </AppShell>
    </div>
  );
}
