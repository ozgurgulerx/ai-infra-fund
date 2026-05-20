import Link from "next/link";

import { AppShell } from "../../components/app-shell";
import {
  AdvisoryPill,
  RiskFlags,
} from "../../components/daily-cockpit/evidence-pills";
import { EmptyState, EvidenceDrawer, SectionCard, StatusChip } from "../../components/workstation";
import {
  collectEvidenceIds,
  collectSourceLinks,
  list,
  readLatestPortfolioExposure,
  readLatestSegmentMap,
  type MarketEvent,
  type SegmentImpact,
} from "../../lib/advisory/workstation-data";

export const dynamic = "force-dynamic";

function relatedEvents(segment: SegmentImpact, events: MarketEvent[]): MarketEvent[] {
  const linked = new Set(list(segment.linked_event_ids));
  return events.filter((event) => event.event_id && linked.has(event.event_id)).slice(0, 3);
}

export default async function SegmentsPage() {
  const [segmentMap, portfolioPayload] = await Promise.all([
    readLatestSegmentMap(),
    readLatestPortfolioExposure(),
  ]);
  const segments = segmentMap.segment_impacts ?? [];
  const events = segmentMap.market_events ?? [];
  const risks = segmentMap.risk_regime_updates ?? [];
  const portfolioTickers = new Set(
    (portfolioPayload.snapshot?.positions ?? [])
      .map((position) => position.ticker)
      .filter(Boolean),
  );
  const evidenceIds = collectEvidenceIds(segments, events, risks);
  const sourceLinks = collectSourceLinks(segments, events, risks);

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Segment Map"
        title="AI Infrastructure Ecosystem Map"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <SectionCard
          badge={<StatusChip label={segmentMap.status ?? "degraded"} tone="review" />}
          eyebrow="Stack propagation"
          title="Bottlenecks, beneficiaries, and risk migration"
          subtitle="AI progress flows through capex, accelerators, memory, packaging, networking, datacenters, power, cooling, policy, and software monetization."
        >
          <div className="ecosystem-map">
            {segments.map((segment) => {
              const linkedEvents = relatedEvents(segment, events);
              const ownedTickers = [
                ...list(segment.primary_tickers),
                ...list(segment.second_order_tickers),
              ].filter((ticker) => portfolioTickers.has(ticker));
              return (
                <article className="ecosystem-segment-card" key={segment.segment_id}>
                  <div className="wave2-card-kicker">
                    <span>{segment.impact_direction ?? "mixed"} tone</span>
                    <AdvisoryPill label={segment.impact_direction ?? "watch"} />
                  </div>
                  <h3>{segment.segment_name ?? segment.segment_id}</h3>
                  <p>{segment.impact_summary ?? "Segment impact summary pending."}</p>

                  <div className="wave2-beneficiary-grid">
                    <div>
                      <strong>first-order beneficiaries</strong>
                      <span>{list(segment.primary_tickers).join(", ") || "None"}</span>
                    </div>
                    <div>
                      <strong>second-order beneficiaries</strong>
                      <span>{list(segment.second_order_tickers).join(", ") || "None"}</span>
                    </div>
                    <div>
                      <strong>negatively exposed</strong>
                      <span>{list(segment.payload?.negatively_exposed_tickers as string[] | undefined).join(", ") || "Review risk flags"}</span>
                    </div>
                    <div>
                      <strong>portfolio overlay</strong>
                      <span>{ownedTickers.join(", ") || "No current holdings tagged"}</span>
                    </div>
                    <div>
                      <strong>related MarketEvents</strong>
                      <span>{list(segment.linked_event_ids).join(", ") || "None"}</span>
                    </div>
                  </div>

                  <div className="proof-point-list">
                    {(segment.proof_points ?? []).slice(0, 3).map((proof) => (
                      <small key={proof.proof_point_id}>{proof.summary}</small>
                    ))}
                    {linkedEvents.map((event) => (
                      <small key={event.event_id}>
                        {event.catalyst ?? "Linked event"} · {event.ai_relevance ?? "interpretation pending"}
                      </small>
                    ))}
                  </div>

                  <div className="source-link-row">
                    {(segment.source_links ?? []).slice(0, 2).map((link) => (
                      <a
                        className="source-inline-link"
                        href={link.url}
                        key={link.url}
                        rel="noreferrer"
                        target="_blank"
                      >
                        {link.label || "review source"}
                      </a>
                    ))}
                  </div>

                  <div className="wave2-chip-row">
                    {list(segment.primary_tickers).slice(0, 5).map((ticker) => (
                      <Link className="wave2-chip" href={`/ticker/${ticker}`} key={ticker}>
                        {ticker}
                      </Link>
                    ))}
                  </div>
                  <RiskFlags flags={list(segment.payload?.risk_flags as string[] | undefined)} />
                </article>
              );
            })}
          </div>
          {segments.length === 0 ? (
            <EmptyState title="No live SegmentImpact rows available." />
          ) : null}
        </SectionCard>

        <SectionCard
          eyebrow="Segment-level risk"
          title="Risk flags and invalidation context"
        >
          <div className="compact-list">
            {risks.map((risk) => (
              <article className="compact-card" key={risk.regime_id}>
                <div className="compact-row-heading">
                  <strong>{risk.risk_type ?? "risk regime"}</strong>
                  <StatusChip label={risk.status ?? "review"} tone="review" />
                </div>
                <p>{risk.summary ?? "No risk summary available."}</p>
                <div className="wave2-invalidation">
                  <strong>Invalidation</strong>
                  <span>{risk.invalidation_condition ?? "Invalidation not yet defined"}</span>
                </div>
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Evidence And Audit Trace"
          title="Evidence and source review"
        >
          <EvidenceDrawer ids={evidenceIds} links={sourceLinks} />
        </SectionCard>
      </AppShell>
    </div>
  );
}
