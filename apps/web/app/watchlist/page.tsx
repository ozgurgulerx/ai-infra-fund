import Link from "next/link";

import { AppShell } from "../../components/app-shell";
import { AdvisoryPill, RiskFlags } from "../../components/daily-cockpit/evidence-pills";
import {
  AdvisoryTable,
  EmptyState,
  EvidenceDrawer,
  MetricTile,
  SectionCard,
  StatusChip,
} from "../../components/workstation";
import {
  collectEvidenceIds,
  collectSourceLinks,
  formatTimestamp,
  list,
  readLatestWatchlistRatings,
} from "../../lib/advisory/workstation-data";

export const dynamic = "force-dynamic";

export default async function WatchlistPage() {
  const payload = await readLatestWatchlistRatings();
  const ratings = payload.items ?? [];
  const evidenceIds = collectEvidenceIds(ratings);
  const sourceLinks = collectSourceLinks(ratings);
  const changed = ratings.filter((row) => row.source_update_id).length;

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Universe"
        title="Watchlist Ratings"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <section className="summary-strip" aria-label="Watchlist ratings status">
          <MetricTile label="Monitored assets" value={ratings.length} detail="read-only advisory rows" />
          <MetricTile label="Changed ratings" value={changed} detail="latest AdvisoryUpdate feed" tone="review" />
          <MetricTile label="Evidence refs" value={evidenceIds.length} detail="hidden by default" />
          <MetricTile label="Freshness" value={payload.status ?? "degraded"} detail="backend read model" />
        </section>

        <SectionCard
          eyebrow="All monitored asset ratings"
          title="Ratings, outlook, and latest advisory changes"
          subtitle="Internal advisory/research stances only. This is not external analyst consensus."
          badge={<StatusChip label="No transaction surface" tone="neutral" />}
        >
          <AdvisoryTable
            columns={["Asset", "Current", "Delta", "Risk", "Latest change", "Freshness"]}
            density="compact"
            emptyLabel="No watchlist ratings have been published yet."
            rows={ratings.map((row) => ({
              id: row.ticker ?? row.source_update_id ?? "watchlist-rating",
              cells: [
                <span className="table-main" key="ticker">
                  <Link className="ticker-link" href={`/ticker/${row.ticker ?? "NVDA"}`}>
                    {row.ticker ?? "Ticker"}
                  </Link>
                  <small>{row.company ?? "AI infrastructure asset"}</small>
                </span>,
                <AdvisoryPill key="label" label={row.current_label ?? "review"} />,
                <span className="table-main" key="delta">
                  <strong>{row.outlook_delta ?? "no published delta"}</strong>
                  <small>{row.previous_label ?? "prior"} {"->"} {row.current_label ?? "review"}</small>
                </span>,
                <span className="table-main" key="risk">
                  <strong>{row.risk_delta ?? "review_needed"}</strong>
                  <small>{row.valuation_delta ?? "valuation review pending"}</small>
                </span>,
                row.latest_change ?? "No latest change explanation.",
                formatTimestamp(row.freshness),
              ],
            }))}
          />
          {ratings.length === 0 ? (
            <EmptyState
              title="Ratings feed empty"
              detail="The cockpit can still render, but no AdvisoryUpdate or TradingAdvisory rows are available."
            />
          ) : null}
        </SectionCard>

        <SectionCard
          eyebrow="Risk flags"
          title="Cross-asset risk and invalidation notes"
        >
          <div className="compact-list">
            {ratings
              .filter((row) => list(row.risk_flags).length || row.invalidation)
              .slice(0, 10)
              .map((row) => (
                <article className="compact-card" key={`${row.ticker}-risk`}>
                  <div className="compact-row-heading">
                    <strong>{row.ticker}</strong>
                    <StatusChip label={row.current_label ?? "review"} tone="review" />
                  </div>
                  <RiskFlags flags={list(row.risk_flags)} />
                  <div className="wave2-invalidation">
                    <strong>Invalidation</strong>
                    <span>{row.invalidation ?? "Invalidation not yet defined"}</span>
                  </div>
                </article>
              ))}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Evidence And Audit Trace"
          title="Source review"
          subtitle="Evidence and source links remain available without cluttering the ratings table."
        >
          <EvidenceDrawer ids={evidenceIds} links={sourceLinks} />
        </SectionCard>
      </AppShell>
    </div>
  );
}
