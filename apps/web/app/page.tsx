import Link from "next/link";

import { AppShell } from "../components/app-shell";
import { DailyAiInfraSentimentCard } from "../components/daily-cockpit/daily-ai-infra-sentiment-card";
import { AdvisoryPill, RiskFlags } from "../components/daily-cockpit/evidence-pills";
import {
  AdvisoryTable,
  EmptyState,
  EvidenceDrawer,
  LlmReviewBadge,
  MetricTile,
  SectionCard,
  StatusChip,
} from "../components/workstation";
import {
  checksCount,
  collectEvidenceIds,
  collectSourceLinks,
  confidenceNumber,
  confidenceTone,
  formatTimestamp,
  list,
  payloadText,
  readAnalystBriefPayload,
  readLatestAdvisoryUpdates,
  readLatestMarketEvents,
  readLatestPortfolioExposure,
  readLatestSourceSignals,
  readLatestTradingAdvisory,
  text,
  type AdvisoryUpdate,
  type MarketEvent,
  type SourceLinkRef,
} from "../lib/advisory/workstation-data";

export const dynamic = "force-dynamic";

async function readCockpitPayload() {
  const [
    analystBrief,
    sourceSignals,
    latestMarketEvents,
    latestTradingAdvisories,
    latestAdvisoryUpdates,
    portfolioExposure,
  ] = await Promise.all([
    readAnalystBriefPayload(),
    readLatestSourceSignals(),
    readLatestMarketEvents(),
    readLatestTradingAdvisory(),
    readLatestAdvisoryUpdates(),
    readLatestPortfolioExposure(),
  ]);

  return {
    analystBrief,
    sourceSignals,
    latestMarketEvents,
    latestTradingAdvisories,
    latestAdvisoryUpdates,
    portfolioExposure,
  };
}

function isStale(status: string | undefined): boolean {
  return status !== "available";
}

function updateDeltaTone(value: string | undefined) {
  const normalized = String(value ?? "").toLowerCase();
  if (["improved", "positive", "increased"].includes(normalized)) {
    return "fresh" as const;
  }
  if (["deteriorated", "negative", "decreased"].includes(normalized)) {
    return "negative" as const;
  }
  if (normalized.includes("review")) {
    return "review" as const;
  }
  return "neutral" as const;
}

function eventInterpretation(event: MarketEvent): string {
  return (
    event.ai_relevance ||
    event.display_text ||
    "Analyst interpretation pending; review linked evidence before changing exposure."
  );
}

function eventReviewPrompt(event: MarketEvent): string {
  const direction = String(event.direction ?? "mixed").toLowerCase();
  if (direction.includes("positive")) {
    return "Review for exposure increase only if evidence freshness and invalidation checks remain clean.";
  }
  if (direction.includes("negative")) {
    return "Review for exposure reduction or thesis downgrade if linked risks persist.";
  }
  return "Keep on watchlist until the catalyst resolves into ticker-level evidence.";
}

function SourceLinks({ links }: { links: SourceLinkRef[] }) {
  if (links.length === 0) {
    return <span className="muted-meta">source link unavailable</span>;
  }
  return (
    <div className="source-link-row">
      {links.slice(0, 2).map((link) => (
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
  );
}

function updateRows(updates: AdvisoryUpdate[]) {
  return updates.slice(0, 8).map((update) => ({
    id: update.update_id ?? update.ticker ?? "advisory-update",
    cells: [
      <span className="table-main" key="ticker">
        <Link className="ticker-link" href={`/ticker/${update.ticker ?? "NVDA"}`}>
          {update.ticker ?? "Ticker"}
        </Link>
        <small>{update.previous_label ?? "prior"} {"->"} {update.current_label ?? "review"}</small>
      </span>,
      <strong key="change">{update.what_changed ?? "No change explanation published."}</strong>,
      <StatusChip
        key="outlook"
        label={update.thesis_change_direction ?? "review_needed"}
        tone={updateDeltaTone(update.thesis_change_direction)}
      />,
      <StatusChip
        key="risk"
        label={update.risk_change_direction ?? "review_needed"}
        tone={updateDeltaTone(update.risk_change_direction)}
      />,
      <SourceLinks key="links" links={update.source_links ?? []} />,
    ],
  }));
}

export default async function DailyTradingCockpitPage() {
  const data = await readCockpitPayload();
  const briefPayload = data.analystBrief;
  const brief = briefPayload.brief;
  const marketEvents =
    briefPayload.market_events?.length
      ? briefPayload.market_events
      : data.latestMarketEvents.items ?? [];
  const segmentImpacts = briefPayload.segment_impacts ?? [];
  const equityAssessments = briefPayload.equity_impact_assessments ?? [];
  const riskRegimes = briefPayload.risk_regime_updates ?? [];
  const tradingAdvisories =
    briefPayload.trading_advisories?.length
      ? briefPayload.trading_advisories
      : data.latestTradingAdvisories.items ?? [];
  const advisoryUpdates =
    briefPayload.advisory_updates?.length
      ? briefPayload.advisory_updates
      : data.latestAdvisoryUpdates.items ?? [];
  const sourceSignals = data.sourceSignals.items ?? [];
  const portfolio = data.portfolioExposure.snapshot;
  const lowConfidenceEvents = marketEvents.filter((event) => {
    const score = confidenceNumber(event.confidence);
    return score !== null && score < 0.5;
  });
  const coreMarketEvents = marketEvents.filter(
    (event) => !lowConfidenceEvents.includes(event),
  );
  const topEvents = coreMarketEvents.slice(0, 4);
  const sentimentAsOf =
    brief?.as_of ?? data.latestMarketEvents.freshness?.latest_available_at ?? null;
  const allEvidenceIds = collectEvidenceIds(
    sourceSignals,
    marketEvents,
    segmentImpacts,
    equityAssessments,
    riskRegimes,
    tradingAdvisories,
    advisoryUpdates,
  );
  const allSourceLinks = collectSourceLinks(
    sourceSignals,
    marketEvents,
    segmentImpacts,
    equityAssessments,
    riskRegimes,
    tradingAdvisories,
    advisoryUpdates,
  );

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Daily Trading Cockpit"
        title="AI Infrastructure Trading Analyst Workstation"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <section className="summary-strip" aria-label="Daily cockpit status">
          <MetricTile
            label="AI infrastructure regime"
            value={isStale(briefPayload.status) ? "degraded" : "fresh"}
            detail={`${formatTimestamp(brief?.as_of)} · API read model`}
            tone={isStale(briefPayload.status) ? "stale" : "fresh"}
          />
          <MetricTile
            label="Rating / outlook changes"
            value={advisoryUpdates.length}
            detail="AdvisoryUpdate records"
            tone="review"
          />
          <MetricTile
            label="MarketEvents"
            value={marketEvents.length}
            detail="ranked, evidence-linked"
          />
          <MetricTile
            label="Portfolio exposure"
            value={portfolio?.position_count ?? 0}
            detail={portfolio?.snapshot_id ?? "snapshot pending"}
          />
        </section>

        {isStale(briefPayload.status) ? (
          <SectionCard
            eyebrow="Backend state"
            title="API-backed analyst brief unavailable"
            badge={<StatusChip label="stale-data" tone="stale" />}
          >
            <p className="wave2-lede">
              {briefPayload.detail ??
                "The read-only API did not return an available analyst brief."}
            </p>
          </SectionCard>
        ) : null}

        <DailyAiInfraSentimentCard
          marketEvents={coreMarketEvents}
          sourceSignals={sourceSignals}
          advisoryUpdates={advisoryUpdates}
          asOf={sentimentAsOf}
        />

        <SectionCard
          eyebrow="Executive summary"
          title="What changed today?"
          subtitle="Rating, outlook, thesis, risk, and valuation deltas that need analyst review."
          badge={<LlmReviewBadge status={briefPayload.status ?? "fallback"} />}
        >
          <p className="wave2-lede">
            {brief?.executive_summary ??
              "No executive summary has been produced yet."}
          </p>
          <AdvisoryTable
            columns={["Asset", "Change", "Outlook", "Risk", "Sources"]}
            density="compact"
            emptyLabel="No AdvisoryUpdate records are available yet."
            rows={updateRows(advisoryUpdates)}
          />
          <div className="section-actions">
            <Link className="secondary-action" href="/watchlist">
              View all monitored asset ratings
            </Link>
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Top MarketEvents"
          title="Top ranked MarketEvents"
          subtitle="Interpretation layer for catalyst impact, affected tickers, and exposure-review prompts."
          badge={<StatusChip label="classified intelligence" tone="review" />}
        >
          <div className="event-interpretation-list">
            {topEvents.map((event) => (
              <article className="event-interpretation-row" key={event.event_id}>
                <div className="event-rank">
                  <strong>{event.confidence ?? "n/a"}</strong>
                  <span>confidence</span>
                </div>
                <div className="event-body">
                  <div className="compact-row-heading">
                    <strong>{event.catalyst ?? "MarketEvent under review"}</strong>
                    <StatusChip
                      label={event.direction ?? "mixed"}
                      tone={confidenceTone(event.confidence)}
                    />
                  </div>
                  <p>{eventInterpretation(event)}</p>
                  <div className="proof-grid">
                    <span>Potential impact: {eventReviewPrompt(event)}</span>
                    <span>Tickers: {list(event.tickers).join(", ") || "watchlist"}</span>
                    <span>Horizon: {event.time_horizon ?? "not reported"}</span>
                    <span>Freshness: {formatTimestamp(event.available_at)}</span>
                  </div>
                  <SourceLinks links={event.source_links ?? []} />
                </div>
              </article>
            ))}
            {topEvents.length === 0 ? (
              <EmptyState title="No validated MarketEvents available." />
            ) : null}
          </div>
          {lowConfidenceEvents.length > 0 ? (
            <details className="compact-collapse">
              <summary>Collapsed low-confidence monitor-only events</summary>
              <div className="compact-list">
                {lowConfidenceEvents.map((event) => (
                  <div className="compact-row" key={event.event_id}>
                    <strong>{event.catalyst ?? "Monitor-only event"}</strong>
                    <span>{event.ai_relevance ?? "No relevance note."}</span>
                    <SourceLinks links={event.source_links ?? []} />
                  </div>
                ))}
              </div>
            </details>
          ) : null}
        </SectionCard>

        <div className="workstation-grid workstation-grid-2">
          <SectionCard
            eyebrow="Segment impact snapshot"
            title="Segment heatmap"
            subtitle="Tone, beneficiaries, proof points, and latest changes."
          >
            <div className="segment-heatmap">
              {segmentImpacts.slice(0, 6).map((segment) => (
                <article className="segment-heatmap-card" key={segment.segment_id}>
                  <div className="compact-row-heading">
                    <strong>{segment.segment_name ?? segment.segment_id}</strong>
                    <AdvisoryPill label={segment.impact_direction ?? "watch"} />
                  </div>
                  <p>{segment.impact_summary ?? "No segment impact summary."}</p>
                  <span>Beneficiaries: {list(segment.primary_tickers).join(", ") || "none"}</span>
                  <span>Second order: {list(segment.second_order_tickers).join(", ") || "none"}</span>
                  <div className="proof-point-list">
                    {(segment.proof_points ?? []).slice(0, 2).map((proof) => (
                      <small key={proof.proof_point_id}>{proof.summary}</small>
                    ))}
                    {(segment.proof_points ?? []).length === 0 ? (
                      <small>{list(segment.evidence_ids).length} evidence refs available</small>
                    ) : null}
                  </div>
                  <RiskFlags flags={list(segment.payload?.risk_flags as string[] | undefined)} />
                </article>
              ))}
            </div>
          </SectionCard>

          <SectionCard
            eyebrow="Risk regime updates"
            title="Risk / invalidation watch"
            subtitle="Conditions that can invalidate current advisory stances."
          >
            <div className="compact-list">
              {riskRegimes.map((risk) => (
                <article className="compact-card" key={risk.regime_id}>
                  <div className="compact-row-heading">
                    <strong>{risk.risk_type ?? "risk regime"}</strong>
                    <AdvisoryPill label={risk.status ?? "watch"} />
                  </div>
                  <p>{risk.summary ?? "No risk summary."}</p>
                  <div className="wave2-invalidation">
                    <strong>Invalidation</strong>
                    <span>
                      {risk.invalidation_condition ||
                        payloadText(risk.payload, "relief_condition", "Invalidation not yet defined")}
                    </span>
                  </div>
                </article>
              ))}
              {riskRegimes.length === 0 ? (
                <EmptyState title="No risk regime update published." />
              ) : null}
            </div>
          </SectionCard>
        </div>

        <div className="workstation-grid workstation-grid-2">
          <SectionCard
            eyebrow="Top advisory stances table"
            title="Ticker thesis, risk, and invalidation"
            badge={<StatusChip label="planning guidance only" tone="neutral" />}
          >
            <AdvisoryTable
              columns={["Ticker", "Stance", "Thesis", "Invalidation"]}
              density="compact"
              rows={equityAssessments.slice(0, 8).map((assessment) => ({
                id: assessment.assessment_id ?? assessment.ticker ?? "assessment",
                cells: [
                  <span className="table-main" key="ticker">
                    <Link className="ticker-link" href={`/ticker/${assessment.ticker ?? "NVDA"}`}>
                      {assessment.ticker ?? "Ticker"}
                    </Link>
                    <small>{assessment.company ?? "Company"}</small>
                  </span>,
                  <AdvisoryPill
                    key="stance"
                    label={assessment.advisory_implication ?? "watch"}
                  />,
                  assessment.assessment ?? "No current thesis assessment.",
                  assessment.invalidation ?? "Invalidation not yet defined",
                ],
              }))}
            />
          </SectionCard>

          <SectionCard
            eyebrow="Portfolio exposure summary"
            title="Current exposure context"
            badge={<StatusChip label="manual journal only" tone="review" />}
          >
            <div className="summary-strip summary-strip-3">
              <MetricTile label="Value" value={portfolio?.total_market_value ?? "n/a"} />
              <MetricTile label="Gross equity" value={portfolio?.gross_equity_exposure ?? "n/a"} />
              <MetricTile label="Cash" value={portfolio?.cash_placeholder ?? "n/a"} />
            </div>
            <RiskFlags
              flags={[
                ...list(portfolio?.concentration_flags),
                ...list(portfolio?.stale_price_flags),
              ]}
            />
            <Link className="secondary-action" href="/portfolio">
              Review detailed portfolio exposure
            </Link>
          </SectionCard>
        </div>

        <SectionCard
          eyebrow="LLM analyst notes"
          title="Advisory labels and review prompts"
          subtitle="LLMs classify, summarize, review, and explain. Deterministic code owns scores, checks, and accounting."
        >
          <div className="compact-list">
            {tradingAdvisories.slice(0, 6).map((advisory) => (
              <article className="compact-card" key={advisory.advisory_id}>
                <div className="compact-row-heading">
                  <strong>{advisory.ticker ?? "Portfolio"}</strong>
                  <AdvisoryPill label={advisory.analyst_action ?? "watch"} />
                </div>
                <p>{advisory.advisory_summary ?? "No advisory summary."}</p>
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
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Evidence And Audit Trace"
          title="Evidence and audit access"
          subtitle="Raw IDs and source details are behind progressive disclosure."
          badge={<StatusChip label="Advisory-only" tone="neutral" />}
        >
          <EvidenceDrawer
            ids={allEvidenceIds}
            links={allSourceLinks}
            refs={[
              ...sourceSignals.flatMap((item) => item.evidence_refs ?? []),
              ...marketEvents.flatMap((item) => item.evidence_refs ?? []),
              ...advisoryUpdates.flatMap((item) => item.evidence_refs ?? []),
            ]}
          />
        </SectionCard>
      </AppShell>
    </div>
  );
}
