"use client";

import { useEffect, useState } from "react";
import { SectionPanel } from "./section-panel";
import { EmptyState } from "./empty-state";
import {
  fetchLatestRecommendations,
  type LatestRecommendationsPayload,
} from "../lib/api";

function actionTone(action: string): string {
  const a = action.toLowerCase();
  if (a.includes("buy") || a.includes("accumulate")) return "actions-tone-buy";
  if (a.includes("sell") || a.includes("exit") || a.includes("trim"))
    return "actions-tone-sell";
  if (a.includes("watch") || a.includes("avoid")) return "actions-tone-watch";
  return "actions-tone-hold";
}

export function ActionsTile() {
  const [payload, setPayload] = useState<LatestRecommendationsPayload | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const result = await fetchLatestRecommendations(6);
      if (!cancelled) setPayload(result);
    }
    void load();
    const id = window.setInterval(load, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const items = payload?.items ?? [];

  return (
    <SectionPanel
      eyebrow="Suggested Actions"
      title="Advisory-only"
      aside={
        <a className="readonly-label" href="/runs">
          → runs
        </a>
      }
    >
      {items.length === 0 ? (
        <EmptyState
          reason="No advisory recommendations yet. Trigger an advisory run to produce suggestions."
          ctaLabel="View runs"
          ctaHref="/runs"
        />
      ) : (
        <ul className="actions-rows">
          {items.map((item) => (
            <li key={item.recommendation_id} className="actions-row">
              <span className="actions-ticker">{item.ticker_or_portfolio}</span>
              <span className={`actions-badge ${actionTone(item.action)}`}>
                {item.action.toUpperCase()}
              </span>
              <span className="actions-horizon">{item.horizon}</span>
              <span className="actions-meta">
                {item.evidence_count} evidence · {item.model_run_count} runs
              </span>
              <span className="actions-advisory" aria-label="advisory only">
                ·advisory
              </span>
            </li>
          ))}
        </ul>
      )}
    </SectionPanel>
  );
}
