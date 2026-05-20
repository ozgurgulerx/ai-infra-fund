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
  readLatestPortfolioExposure,
  readLatestTradingAdvisory,
} from "../../lib/advisory/workstation-data";
import { mockWorkstationData } from "../../lib/situational-awareness/mock-workstation-data";
import { watchlist } from "../../lib/watchlist-mirror";

export const dynamic = "force-dynamic";

export default async function TradePlansPage() {
  const [advisoryPayload, updatePayload, portfolioPayload] = await Promise.all([
    readLatestTradingAdvisory(),
    readLatestAdvisoryUpdates(),
    readLatestPortfolioExposure(),
  ]);
  const advisories = advisoryPayload.items ?? [];
  const updates = updatePayload.items ?? [];
  const advisoriesByTicker = new Map(
    advisories
      .filter((advisory) => advisory.ticker)
      .map((advisory) => [advisory.ticker as string, advisory]),
  );
  const updatesByTicker = new Map(
    updates
      .filter((update) => update.ticker)
      .map((update) => [update.ticker as string, update]),
  );
  const watchlistTickers = new Set(watchlist.map((entry) => entry.ticker));
  const extraAdvisoryRows = advisories
    .filter((advisory) => advisory.ticker && !watchlistTickers.has(advisory.ticker))
    .map((advisory) => ({
      advisory,
      companyName: advisory.ticker ?? "AI infrastructure asset",
      priority: "published advisory",
      ticker: advisory.ticker ?? "Ticker",
      update: updatesByTicker.get(advisory.ticker ?? ""),
    }));
  const tradePlanRows = [
    ...watchlist.map((entry) => ({
      advisory: advisoriesByTicker.get(entry.ticker),
      companyName: entry.companyName,
      priority: entry.priority,
      ticker: entry.ticker,
      update: updatesByTicker.get(entry.ticker),
    })),
    ...extraAdvisoryRows,
  ];
  const evidenceIds = collectEvidenceIds(advisories, updates);
  const sourceLinks = collectSourceLinks(advisories, updates);
  const positionTickers = new Set(
    (portfolioPayload.snapshot?.positions ?? [])
      .map((position) => position.ticker)
      .filter(Boolean),
  );

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Manual Planning"
        title="Trade Plan Workbench"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <SectionCard
          badge={<StatusChip label="planning guidance only" tone="neutral" />}
          eyebrow="Planning guidance only"
          title="Evidence-backed manual review queue"
          subtitle="Review advisory stances, invalidation, and portfolio impact before any manual journal decision."
        >
          <div className="wave2-card-grid">
            {tradePlanRows.map(({ advisory, companyName, priority, ticker, update }) => {
              const riskFlags = list(advisory?.payload?.risk_flags as string[] | undefined);
              return (
                <article className="wave2-card" key={advisory?.advisory_id ?? `watchlist-${ticker}`}>
                  <div className="wave2-equity-title">
                    <div>
                      <Link className="ticker-link" href={`/ticker/${ticker}`}>
                        {ticker}
                      </Link>
                      <span>{companyName}</span>
                    </div>
                    <AdvisoryPill label={advisory?.analyst_action ?? update?.current_label ?? "review"} />
                  </div>
                  <p>
                    {advisory?.advisory_summary
                      ?? update?.what_changed
                      ?? "No published trade advisory yet; keep this ticker in manual review until evidence updates."}
                  </p>
                  <div className="wave2-case-grid">
                    <span>Catalyst</span>
                    <p>{update?.what_changed ?? "Latest advisory delta pending."}</p>
                    <span>Entry level</span>
                    <p>{payloadText(advisory?.payload, "entry_zone", "deterministic level unavailable")}</p>
                    <span>Add level</span>
                    <p>{payloadText(advisory?.payload, "add_zone", "deterministic level unavailable")}</p>
                    <span>Stop/invalidation</span>
                    <p>
                      {payloadText(
                        advisory?.payload,
                        "invalidation_condition",
                        "Invalidation not yet defined",
                      )}
                    </p>
                    <span>Target 1 / target 2</span>
                    <p>{payloadText(advisory?.payload, "target_zone", "target scenario unavailable")}</p>
                    <span>Time horizon</span>
                    <p>{update?.time_horizon ?? "review horizon pending"}</p>
                    <span>position-sizing note</span>
                    <p>{priority} priority; deterministic constraints and portfolio exposure own sizing checks.</p>
                    <span>portfolio impact</span>
                    <p>{positionTickers.has(ticker) ? "Existing exposure requires drift review." : "No current holding in exposure snapshot."}</p>
                    <span>LLM critique</span>
                    <p>
                      {advisory
                        ? "LLM critique may explain evidence, but cannot own levels, weights, or PnL."
                        : "No advisory artifact is published for this ticker yet; avoid inferred levels until evidence is materialized."}
                    </p>
                  </div>
                  <RiskFlags flags={riskFlags} />
                </article>
              );
            })}
          </div>
          <EvidenceDrawer ids={evidenceIds} links={sourceLinks} />
        </SectionCard>

        <SectionCard
          eyebrow="Exposure context"
          title="Correlation and concentration checks"
        >
          <div className="wave2-card-grid">
            {mockWorkstationData.correlationExposures.map((cluster) => (
              <article className="wave2-card" key={cluster.cluster}>
                <div className="wave2-card-kicker">
                  <span>{cluster.weight}</span>
                  <strong>{cluster.cluster}</strong>
                </div>
                <p>{cluster.note}</p>
                <div className="wave2-chip-row">
                  {cluster.tickers.map((ticker) => (
                    <Link className="wave2-chip" href={`/ticker/${ticker}`} key={`${cluster.cluster}-${ticker}`}>
                      {ticker}
                    </Link>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </SectionCard>
      </AppShell>
    </div>
  );
}
