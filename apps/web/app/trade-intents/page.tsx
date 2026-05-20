import Link from "next/link";

import { AppShell } from "../../components/app-shell";
import {
  AdvisoryPill,
  RiskFlags,
} from "../../components/daily-cockpit/evidence-pills";
import { EvidenceDrawer, SectionCard, StatusChip } from "../../components/workstation";
import {
  collectEvidenceIds,
  collectSourceLinks,
  list,
  payloadText,
  readLatestAdvisoryUpdates,
  readLatestTradingAdvisory,
} from "../../lib/advisory/workstation-data";

export const dynamic = "force-dynamic";

export default async function TradeIntentsPage() {
  const [advisoryPayload, updatePayload] = await Promise.all([
    readLatestTradingAdvisory(),
    readLatestAdvisoryUpdates(),
  ]);
  const advisories = advisoryPayload.items ?? [];
  const updates = updatePayload.items ?? [];
  const evidenceIds = collectEvidenceIds(advisories, updates);
  const sourceLinks = collectSourceLinks(advisories, updates);

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Manual Planning"
        title="Manual Plan Review Queue"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <div className="workstation-grid workstation-grid-2">
          <SectionCard
            badge={<StatusChip label="Manual journal only" tone="review" />}
            eyebrow="Local journal only"
            title="Planning queue from advisory changes"
            subtitle="This page explains what deserves manual analyst review. It does not create market instructions."
          >
            <div className="wave2-stack">
              {updates.slice(0, 8).map((update) => (
                <article className="wave2-list-card" key={update.update_id}>
                  <div className="compact-row-heading">
                    <Link className="ticker-link" href={`/ticker/${update.ticker ?? "NVDA"}`}>
                      {update.ticker ?? "Ticker"}
                    </Link>
                    <AdvisoryPill label={update.current_label ?? "review"} />
                  </div>
                  <p>{update.what_changed ?? "No advisory delta explanation."}</p>
                  <div className="wave2-mini-columns">
                    <span>Prior: {update.previous_label ?? "not published"}</span>
                    <span>Outlook: {update.thesis_change_direction ?? "review_needed"}</span>
                    <span>Risk: {update.risk_change_direction ?? "review_needed"}</span>
                    <span>Confidence: {update.confidence_change ?? "review_needed"}</span>
                  </div>
                </article>
              ))}
            </div>
            <EvidenceDrawer ids={evidenceIds} links={sourceLinks} />
          </SectionCard>

          <SectionCard
            eyebrow="Trade plan linkage"
            title="Evidence before manual action"
            subtitle="Suggested review items remain advisory-only until the user records a manual journal entry."
          >
            <div className="wave2-stack">
              {advisories.slice(0, 8).map((advisory) => (
                <article className="wave2-list-card" key={advisory.advisory_id}>
                  <div className="compact-row-heading">
                    <Link className="ticker-link" href={`/ticker/${advisory.ticker ?? "NVDA"}`}>
                      {advisory.ticker ?? "Ticker"}
                    </Link>
                    <AdvisoryPill label={advisory.analyst_action ?? "watch"} />
                  </div>
                  <p>{advisory.advisory_summary ?? "No planning note."}</p>
                  <RiskFlags flags={list(advisory.payload?.risk_flags as string[] | undefined)} />
                  <div className="wave2-invalidation">
                    <strong>Invalidation</strong>
                    <span>
                      {payloadText(
                        advisory.payload,
                        "invalidation_condition",
                        "Invalidation not yet defined",
                      )}
                    </span>
                  </div>
                  <span className="muted-meta">
                    Linked plan: {advisory.linked_trade_plan_id ?? "manual review pending"}
                  </span>
                </article>
              ))}
            </div>
          </SectionCard>
        </div>
      </AppShell>
    </div>
  );
}
