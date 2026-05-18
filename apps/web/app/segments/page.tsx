import { AppShell } from "../../components/app-shell";
import {
  AdvisoryPill,
  RiskFlags,
} from "../../components/daily-cockpit/evidence-pills";
import { EvidenceDrawer, SectionCard, StatusChip } from "../../components/workstation";
import { mockWorkstationData } from "../../lib/situational-awareness/mock-workstation-data";

export default function SegmentsPage() {
  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Segment Map"
        title="AI Infrastructure Ecosystem Map"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <SectionCard
          badge={<StatusChip label="mock data only" tone="neutral" />}
          eyebrow="Stack propagation"
          title="Bottlenecks, beneficiaries, and risk migration"
        >
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
              </article>
            ))}
          </div>
          <EvidenceDrawer
            ids={mockWorkstationData.segmentImpacts.flatMap(
              (segment) => segment.evidenceIds,
            )}
          />
        </SectionCard>
      </AppShell>
    </div>
  );
}
