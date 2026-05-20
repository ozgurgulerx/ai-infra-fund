import Link from "next/link";

import { AppShell } from "../../components/app-shell";
import { RiskFlags } from "../../components/daily-cockpit/evidence-pills";
import {
  AdvisoryTable,
  EmptyState,
  EvidenceDrawer,
  SectionCard,
  StatusChip,
} from "../../components/workstation";
import {
  collectEvidenceIds,
  collectSourceLinks,
  confidenceNumber,
  confidenceTone,
  formatTimestamp,
  list,
  readLatestMarketEvents,
  readLatestSourceSignals,
  readLatestTradingAdvisory,
  type MarketEvent,
  type SourceLinkRef,
} from "../../lib/advisory/workstation-data";

export const dynamic = "force-dynamic";

function reviewPriority(event: MarketEvent): string {
  const score = confidenceNumber(event.confidence);
  if (score !== null && score >= 0.75) {
    return "high";
  }
  if (String(event.confidence ?? "").toLowerCase() === "high") {
    return "high";
  }
  if (list(event.tickers).length >= 3) {
    return "medium";
  }
  return "watch";
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

export default async function RadarPage() {
  const [signalsPayload, eventsPayload, advisoryPayload] = await Promise.all([
    readLatestSourceSignals(),
    readLatestMarketEvents(),
    readLatestTradingAdvisory(),
  ]);
  const sourceSignals = signalsPayload.items ?? [];
  const events = eventsPayload.items ?? [];
  const advisories = advisoryPayload.items ?? [];
  const lowConfidenceEvents = events.filter((event) => {
    const score = confidenceNumber(event.confidence);
    return score !== null && score < 0.5;
  });
  const visibleEvents = events.filter((event) => !lowConfidenceEvents.includes(event));
  const evidenceIds = collectEvidenceIds(sourceSignals, events, advisories);
  const sourceLinks = collectSourceLinks(sourceSignals, events, advisories);

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Market Radar"
        title="Live Market / Sentiment Radar"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <SectionCard
          badge={<StatusChip label="classified intelligence" tone="review" />}
          eyebrow="Classified intelligence"
          title="Compact event feed"
          subtitle="event feed, sentiment, urgency, relevance, confidence, ticker, segment, and freshness"
        >
          <div className="compact-list">
            {visibleEvents.map((event) => (
              <article className="wave2-radar-row compact-card" key={event.event_id}>
                <div className="wave2-radar-score">
                  <strong>{reviewPriority(event)}</strong>
                  <span>review priority</span>
                </div>
                <div>
                  <div className="wave2-card-kicker">
                    <span>{event.event_type?.replaceAll("_", " ") ?? "MarketEvent"}</span>
                    <StatusChip
                      label={event.direction ?? "mixed"}
                      tone={confidenceTone(event.confidence)}
                    />
                  </div>
                  <h3>{event.catalyst ?? "MarketEvent under review"}</h3>
                  <p>{event.ai_relevance ?? "LLM scout notes pending for this event."}</p>
                  <div className="wave2-mini-columns">
                    <span>Tickers: {list(event.tickers).join(", ") || "watchlist"}</span>
                    <span>Themes: {list(event.themes).join(", ") || "theme review pending"}</span>
                    <span>Freshness: {formatTimestamp(event.available_at)}</span>
                    <span>correlation/sector movement: monitor linked segment moves</span>
                  </div>
                  <SourceLinks links={event.source_links ?? []} />
                  <RiskFlags flags={list(event.themes).slice(0, 3)} />
                </div>
                <Link className="secondary-action" href={`/ticker/${list(event.tickers)[0] ?? "NVDA"}`}>
                  Ticker review
                </Link>
              </article>
            ))}
            {visibleEvents.length === 0 ? (
              <EmptyState title="No validated live MarketEvents available." />
            ) : null}
          </div>
          {lowConfidenceEvents.length > 0 ? (
            <details className="compact-collapse">
              <summary>Collapsed noisy low-confidence items</summary>
              <div className="compact-list">
                {lowConfidenceEvents.map((event) => (
                  <div className="compact-row" key={event.event_id}>
                    <strong>{event.catalyst ?? "Monitor-only item"}</strong>
                    <span>{event.ai_relevance ?? "Awaiting interpretation."}</span>
                    <SourceLinks links={event.source_links ?? []} />
                  </div>
                ))}
              </div>
            </details>
          ) : null}
        </SectionCard>

        <SectionCard
          eyebrow="LLM scout notes"
          title="Interpretation layer, not raw internet feed"
          subtitle="Detailed source-to-event interpretation with analyst review prompts."
        >
          <AdvisoryTable
            columns={["Signal", "Themes", "Confidence", "Source review"]}
            density="compact"
            rows={sourceSignals.map((signal) => ({
              id: signal.signal_id ?? signal.title ?? "signal",
              cells: [
                <span className="table-main" key="signal">
                  <strong>{signal.title ?? "Source signal under review"}</strong>
                  <small>{signal.summary ?? "Summary pending review."}</small>
                </span>,
                list(signal.themes).join(", ") || "theme review pending",
                <StatusChip
                  key="confidence"
                  label={String(signal.confidence ?? "n/a")}
                  tone={confidenceTone(signal.confidence)}
                />,
                <SourceLinks key="source" links={signal.source_links ?? []} />,
              ],
            }))}
          />
          <EvidenceDrawer ids={evidenceIds} links={sourceLinks} />
        </SectionCard>
      </AppShell>
    </div>
  );
}
