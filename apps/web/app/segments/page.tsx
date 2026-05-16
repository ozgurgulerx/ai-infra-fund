import { AppShell } from "../../components/app-shell";
import {
  AdvisoryPill,
  EvidencePills,
  RiskFlags,
} from "../../components/daily-cockpit/evidence-pills";
import { mockWorkstationData } from "../../lib/situational-awareness/mock-workstation-data";

export default function SegmentsPage() {
  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Segment Map"
        title="AI Infrastructure Ecosystem Map"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <section className="section-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Stack propagation</p>
              <h2>Bottlenecks, beneficiaries, and risk migration</h2>
            </div>
            <span className="readonly-label">mock data only</span>
          </div>
          <div className="wave2-segment-map">
            {mockWorkstationData.segmentImpacts.map((segment) => (
              <article className="wave2-segment-card" key={segment.segmentId}>
                <div className="wave2-card-kicker">
                  <span>{segment.momentum} momentum</span>
                  <AdvisoryPill label={segment.status} />
                </div>
                <h3>{segment.segmentName}</h3>
                <p>{segment.latestCatalyst}</p>

                <div className="wave2-beneficiary-grid">
                  <div>
                    <strong>first-order beneficiaries</strong>
                    <span>{segment.firstOrderBeneficiaries.join(", ") || "None"}</span>
                  </div>
                  <div>
                    <strong>second-order beneficiaries</strong>
                    <span>{segment.secondOrderBeneficiaries.join(", ") || "None"}</span>
                  </div>
                  <div>
                    <strong>negatively exposed</strong>
                    <span>{segment.negativelyExposedTickers.join(", ") || "None"}</span>
                  </div>
                  <div>
                    <strong>related MarketEvents</strong>
                    <span>{segment.relatedEventIds.join(", ")}</span>
                  </div>
                </div>

                <RiskFlags flags={segment.riskFlags} />
                <EvidencePills ids={segment.evidenceIds} />
              </article>
            ))}
          </div>
        </section>
      </AppShell>
    </div>
  );
}
