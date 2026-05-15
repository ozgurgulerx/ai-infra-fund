"use client";

import { useEffect, useState } from "react";
import { SectionPanel } from "./section-panel";
import { EmptyState } from "./empty-state";
import { fetchLatestEquityEvents } from "../lib/api";
import type { LatestEquityEvents } from "../lib/status-model";

type EquityEventRow = {
  evidence_id: string;
  title?: string | null;
  publisher?: string | null;
  published_at?: string | null;
  ingested_at?: string | null;
  summary?: string | null;
  tickers?: string[];
  themes?: string[];
  data_class?: string;
};

type EventsPayload = { events?: EquityEventRow[] };

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return "—";
  const diffMs = Date.now() - t;
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.round(hours / 24);
  return `${days}d`;
}

export function NewsTile() {
  const [feed, setFeed] = useState<LatestEquityEvents | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const result = await fetchLatestEquityEvents();
      if (!cancelled) setFeed(result);
    }
    void load();
    const id = window.setInterval(load, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const payload = (feed?.payload ?? {}) as EventsPayload;
  const events = (payload.events ?? []).slice(0, 8);

  return (
    <SectionPanel
      eyebrow="News & Events"
      title="Last 24h"
      aside={
        <a className="readonly-label" href="/evidence">
          → evidence
        </a>
      }
    >
      {events.length === 0 ? (
        <EmptyState
          reason="No fresh events. The crawl worker may be idle or upstream sources have not updated."
          ctaLabel="View evidence pipeline"
          ctaHref="/evidence"
        />
      ) : (
        <ul className="news-rows">
          {events.map((event) => {
            const tickers = (event.tickers ?? []).slice(0, 3).join(", ");
            return (
              <li key={event.evidence_id} className="news-row">
                <span className="news-title">
                  {event.title ?? event.summary ?? event.evidence_id}
                </span>
                <span className="news-meta">
                  <span className="news-time">
                    {relativeTime(event.published_at ?? event.ingested_at)}
                  </span>
                  {tickers ? (
                    <span className="news-tickers">{tickers}</span>
                  ) : null}
                  {event.publisher ? (
                    <span className="news-publisher">{event.publisher}</span>
                  ) : null}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </SectionPanel>
  );
}
