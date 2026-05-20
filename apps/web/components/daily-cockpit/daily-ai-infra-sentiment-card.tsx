"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import type {
  AdvisoryUpdate,
  MarketEvent,
  SourceLinkRef,
  SourceSignal,
} from "../../lib/advisory/workstation-data";

type DailyAiInfraSentimentCardProps = {
  marketEvents: MarketEvent[];
  sourceSignals: SourceSignal[];
  advisoryUpdates: AdvisoryUpdate[];
  asOf?: string | null;
};

const STORAGE_PREFIX = "ai-infra-fund:daily-ai-infra-sentiment";

type RankedEvent = {
  event: MarketEvent;
  rankScore: number;
};

function list(values: string[] | undefined): string[] {
  return Array.isArray(values) ? values.filter(Boolean) : [];
}

function confidenceNumber(value: string | number | undefined): number | null {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "No timestamp";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "No timestamp";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  }).format(parsed);
}

function eventInterpretation(event: MarketEvent): string {
  return (
    event.ai_relevance ||
    event.display_text ||
    "AI interpretation pending; review the linked evidence before changing exposure."
  );
}

function eventReviewPrompt(event: MarketEvent): string {
  const direction = String(event.direction ?? "mixed").toLowerCase();
  if (direction.includes("positive")) {
    return "Potential stock effect: supports exposure-upside review only if freshness and invalidation checks stay clean.";
  }
  if (direction.includes("negative")) {
    return "Potential stock effect: pressures exposure, thesis, or valuation review if the linked risk persists.";
  }
  return "Potential stock effect: keep affected names on watch until the catalyst resolves into ticker-level evidence.";
}

function directionTone(direction: string | undefined): string {
  const normalized = String(direction ?? "mixed").toLowerCase();
  if (normalized.includes("positive")) return "positive";
  if (normalized.includes("negative")) return "negative";
  if (normalized.includes("mixed")) return "mixed";
  return "neutral";
}

function rankEvent(event: MarketEvent, nowMs: number): number {
  const confidence = confidenceNumber(event.confidence) ?? 0.5;
  const tickers = list(event.tickers).length;
  const sources = (event.source_links ?? []).filter((link) => link.url).length;
  const evidence = [
    ...list(event.evidence_ids),
    ...list(event.source_evidence_ids),
  ].length;
  const availableAt = event.available_at ? Date.parse(event.available_at) : 0;
  const ageHours = availableAt > 0 ? Math.max(0, (nowMs - availableAt) / 3_600_000) : 999;
  const freshness = ageHours <= 24 ? 1.5 : ageHours <= 72 ? 0.75 : 0;

  return (
    confidence * 5 +
    Math.min(tickers, 6) * 0.35 +
    Math.min(sources, 4) * 0.4 +
    Math.min(evidence, 6) * 0.12 +
    freshness
  );
}

function ecosystemTone(events: MarketEvent[]): {
  label: string;
  detail: string;
  toneClass: string;
} {
  const score = events.reduce((total, event) => {
    const direction = String(event.direction ?? "").toLowerCase();
    if (direction.includes("positive")) return total + 1;
    if (direction.includes("negative")) return total - 1;
    return total;
  }, 0);

  if (score >= 2) {
    return {
      label: "constructive",
      detail: "positive catalysts outnumber risk flags in the top event set",
      toneClass: "positive",
    };
  }
  if (score <= -2) {
    return {
      label: "cautious",
      detail: "risk catalysts dominate the top event set",
      toneClass: "negative",
    };
  }
  return {
    label: "mixed",
    detail: "catalysts and risks are balanced enough to require manual review",
    toneClass: "mixed",
  };
}

function storageKey(asOf: string | null | undefined): string {
  return `${STORAGE_PREFIX}:${asOf || "no-edition"}`;
}

function SourceLinks({ links }: { links: SourceLinkRef[] }) {
  const usableLinks = links.filter((link) => link.url).slice(0, 2);
  if (usableLinks.length === 0) {
    return <span className="muted-meta">source link unavailable</span>;
  }
  return (
    <div className="source-link-row">
      {usableLinks.map((link) => (
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

export function DailyAiInfraSentimentCard({
  marketEvents,
  sourceSignals,
  advisoryUpdates,
  asOf,
}: DailyAiInfraSentimentCardProps) {
  const key = storageKey(asOf);
  const [isDismissed, setIsDismissed] = useState(false);
  const [hasLoadedPreference, setHasLoadedPreference] = useState(false);

  useEffect(() => {
    try {
      setIsDismissed(window.localStorage.getItem(key) === "hidden");
    } catch {
      setIsDismissed(false);
    } finally {
      setHasLoadedPreference(true);
    }
  }, [key]);

  const rankedEvents = useMemo<RankedEvent[]>(() => {
    const nowMs = Date.now();
    return [...marketEvents]
      .map((event) => ({ event, rankScore: rankEvent(event, nowMs) }))
      .sort((a, b) => b.rankScore - a.rankScore)
      .slice(0, 3);
  }, [marketEvents]);

  const tone = ecosystemTone(rankedEvents.map(({ event }) => event));
  const tickerCount = new Set(
    rankedEvents.flatMap(({ event }) => list(event.tickers)),
  ).size;
  const sourceCount = rankedEvents.reduce(
    (count, { event }) =>
      count + (event.source_links ?? []).filter((link) => link.url).length,
    0,
  );
  const latestSignal = sourceSignals[0];
  const latestUpdate = advisoryUpdates[0];

  function dismiss() {
    setIsDismissed(true);
    try {
      window.localStorage[key] = "hidden";
    } catch {
      // The card still hides for this render if browser storage is unavailable.
    }
  }

  function restore() {
    setIsDismissed(false);
    try {
      window.localStorage[key] = "visible";
    } catch {
      // Browser storage is optional for this advisory-only UI preference.
    }
  }

  if (hasLoadedPreference && isDismissed) {
    return (
      <section className="ai-infra-sentiment-restore" aria-label="Daily AI infra sentiment controls">
        <button type="button" onClick={restore}>
          Show AI infra sentiment
        </button>
      </section>
    );
  }

  return (
    <section className="ai-infra-sentiment-card" aria-labelledby="ai-infra-sentiment-title">
      <div className="ai-infra-sentiment-header">
        <div>
          <p className="eyebrow">Daily sentiment</p>
          <h2 id="ai-infra-sentiment-title">Daily AI Infra Ecosystem Sentiment</h2>
          <p>
            Prominent news, AI interpretation, and potential effect on monitored stocks.
          </p>
        </div>
        <div className="ai-infra-sentiment-actions">
          <span className={`ai-infra-sentiment-tone ai-infra-sentiment-tone-${tone.toneClass}`}>
            {tone.label}
          </span>
          <button type="button" onClick={dismiss} aria-label="Hide daily AI infra sentiment card">
            Hide
          </button>
        </div>
      </div>

      <div className="ai-infra-sentiment-summary">
        <span>
          <strong>{rankedEvents.length}</strong>
          <small>ranked events</small>
        </span>
        <span>
          <strong>{tickerCount}</strong>
          <small>affected tickers</small>
        </span>
        <span>
          <strong>{sourceCount}</strong>
          <small>source links</small>
        </span>
        <span>
          <strong>{advisoryUpdates.length}</strong>
          <small>advisory deltas</small>
        </span>
      </div>

      <p className="ai-infra-sentiment-thesis">{tone.detail}</p>

      {rankedEvents.length === 0 ? (
        <div className="empty-state">
          <strong>No ranked AI infrastructure events available.</strong>
          <span>The card will populate when the daily advisory read model publishes MarketEvents.</span>
        </div>
      ) : (
        <div className="ai-infra-sentiment-list">
          {rankedEvents.map(({ event, rankScore }, index) => {
            const tickers = list(event.tickers);
            const confidence = confidenceNumber(event.confidence);
            return (
              <article className="ai-infra-sentiment-event" key={event.event_id ?? `${index}-${event.catalyst}`}>
                <div className="ai-infra-sentiment-rank">
                  <strong>{index + 1}</strong>
                  <span>{rankScore.toFixed(1)}</span>
                </div>
                <div className="ai-infra-sentiment-event-body">
                  <div className="compact-row-heading">
                    <strong>{event.catalyst ?? "MarketEvent under review"}</strong>
                    <span className={`ai-infra-direction ai-infra-direction-${directionTone(event.direction)}`}>
                      {event.direction ?? "mixed"}
                    </span>
                  </div>
                  <p>{eventInterpretation(event)}</p>
                  <p className="ai-infra-stock-effect">{eventReviewPrompt(event)}</p>
                  <div className="ai-infra-event-meta">
                    <span>
                      Confidence: {confidence === null ? event.confidence ?? "n/a" : confidence.toFixed(2)}
                    </span>
                    <span>Horizon: {event.time_horizon ?? "not reported"}</span>
                    <span>Freshness: {formatTimestamp(event.available_at)}</span>
                  </div>
                  <div className="ai-infra-ticker-row">
                    <span>Tickers:</span>
                    {tickers.length ? (
                      tickers.slice(0, 8).map((ticker) => (
                        <Link className="ticker-link" href={`/ticker/${ticker}`} key={ticker}>
                          {ticker}
                        </Link>
                      ))
                    ) : (
                      <small>watchlist</small>
                    )}
                  </div>
                  <SourceLinks links={event.source_links ?? []} />
                </div>
              </article>
            );
          })}
        </div>
      )}

      <div className="ai-infra-sentiment-footer">
        <span>
          Latest signal: {latestSignal?.title ?? latestSignal?.summary ?? "source-signal feed pending"}
        </span>
        <span>
          Latest advisory change: {latestUpdate?.what_changed ?? "no advisory delta published"}
        </span>
      </div>
    </section>
  );
}
