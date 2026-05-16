import { AppShell } from "../../components/app-shell";
import {
  AdvisoryPill,
  EvidencePills,
  RiskFlags,
} from "../../components/daily-cockpit/evidence-pills";
import { mockWorkstationData } from "../../lib/situational-awareness/mock-workstation-data";

export default function TradePlansPage() {
  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Manual Planning"
        title="Trade Plan Workbench"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <section className="section-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Planning guidance only</p>
              <h2>Evidence-backed manual review queue</h2>
            </div>
            <span className="readonly-label">no broker connection</span>
          </div>
          <div className="wave2-card-grid">
            {mockWorkstationData.openTradePlans.map((plan) => (
              <article className="wave2-card" key={plan.tradePlanId}>
                <div className="wave2-equity-title">
                  <div>
                    <strong>{plan.ticker}</strong>
                    <span>{plan.segment}</span>
                  </div>
                  <AdvisoryPill label={plan.advisoryAction} />
                </div>
                <p>{plan.thesis}</p>
                <div className="wave2-case-grid">
                  <span>Catalyst</span>
                  <p>{plan.catalyst}</p>
                  <span>Entry level</span>
                  <p>{plan.entryLevel}</p>
                  <span>Add level</span>
                  <p>{plan.addLevel}</p>
                  <span>Stop/invalidation</span>
                  <p>{plan.stopInvalidation}</p>
                  <span>Target 1 / target 2</span>
                  <p>{plan.targetOne} / {plan.targetTwo}</p>
                  <span>Time horizon</span>
                  <p>{plan.timeHorizon}</p>
                  <span>position-sizing note</span>
                  <p>{plan.positionSizingNote}</p>
                  <span>portfolio impact</span>
                  <p>{plan.portfolioImpact}</p>
                  <span>LLM critique</span>
                  <p>{plan.llmCritique}</p>
                </div>
                <RiskFlags flags={plan.riskFlags} />
                <EvidencePills ids={plan.evidenceIds} />
              </article>
            ))}
          </div>
        </section>

        <section className="section-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Exposure context</p>
              <h2>Correlation and concentration checks</h2>
            </div>
          </div>
          <div className="wave2-card-grid">
            {mockWorkstationData.correlationExposures.map((cluster) => (
              <article className="wave2-card" key={cluster.cluster}>
                <div className="wave2-card-kicker">
                  <span>{cluster.weight}</span>
                  <strong>{cluster.cluster}</strong>
                </div>
                <p>{cluster.note}</p>
                <div className="wave2-chip-row">
                  {cluster.tickers.map((ticker) => (
                    <span className="wave2-chip" key={`${cluster.cluster}-${ticker}`}>
                      {ticker}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </section>
      </AppShell>
    </div>
  );
}
