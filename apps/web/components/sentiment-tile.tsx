"use client";

import { useEffect, useState } from "react";
import { SectionPanel } from "./section-panel";
import { EmptyState } from "./empty-state";
import { fetchLatestSignalSnapshots } from "../lib/api";
import type { LatestSignalSnapshots } from "../lib/status-model";

type SignalRow = {
  ticker: string;
  sentiment_score?: string | number | null;
  technical_score?: string | number | null;
  fundamental_score?: string | number | null;
  forward_indicator_score?: string | number | null;
  portfolio_risk_score?: string | number | null;
  as_of?: string | null;
};

type SnapshotsPayload = { snapshots?: SignalRow[] };

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function dominantDriver(row: SignalRow): string {
  const drivers = [
    { name: "sentiment", value: toNumber(row.sentiment_score) },
    { name: "technical", value: toNumber(row.technical_score) },
    { name: "fundamental", value: toNumber(row.fundamental_score) },
    { name: "forward", value: toNumber(row.forward_indicator_score) },
  ];
  let best = drivers[0];
  let bestAbs = best.value === null ? -1 : Math.abs(best.value);
  for (const d of drivers) {
    if (d.value === null) continue;
    if (Math.abs(d.value) > bestAbs) {
      best = d;
      bestAbs = Math.abs(d.value);
    }
  }
  return best.name;
}

function arrow(value: number | null): string {
  if (value === null) return "·";
  if (value > 0.05) return "▲";
  if (value < -0.05) return "▼";
  return "◆";
}

export function SentimentTile() {
  const [feed, setFeed] = useState<LatestSignalSnapshots | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const result = await fetchLatestSignalSnapshots();
      if (!cancelled) setFeed(result);
    }
    void load();
    const id = window.setInterval(load, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const payload = (feed?.payload ?? {}) as SnapshotsPayload;
  const snapshots = payload.snapshots ?? [];

  const ranked = [...snapshots]
    .map((row) => ({
      row,
      magnitude: Math.max(
        Math.abs(toNumber(row.forward_indicator_score) ?? 0),
        Math.abs(toNumber(row.sentiment_score) ?? 0),
      ),
      score:
        toNumber(row.forward_indicator_score) ??
        toNumber(row.sentiment_score) ??
        0,
    }))
    .sort((a, b) => b.magnitude - a.magnitude)
    .slice(0, 6);

  return (
    <SectionPanel
      eyebrow="Market Sentiment"
      title="Top movers"
      aside={
        <a className="readonly-label" href="/signals">
          → all signals
        </a>
      }
    >
      {ranked.length === 0 ? (
        <EmptyState
          reason="No signal snapshots yet. Run the advisory pipeline to populate sentiment, technical, and fundamental scores."
          ctaLabel="View signals"
          ctaHref="/signals"
        />
      ) : (
        <ul className="sentiment-rows">
          {ranked.map(({ row, score }) => {
            const driver = dominantDriver(row);
            const indicator = arrow(score);
            const label = score > 0 ? `+${score.toFixed(2)}` : score.toFixed(2);
            return (
              <li key={row.ticker} className="sentiment-row">
                <span className="sentiment-ticker">{row.ticker}</span>
                <span className="sentiment-score">{label}</span>
                <span className="sentiment-driver">{driver}</span>
                <span className="sentiment-arrow" aria-hidden>
                  {indicator}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </SectionPanel>
  );
}
