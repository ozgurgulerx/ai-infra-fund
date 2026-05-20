import Link from "next/link";

import { AppShell } from "../../components/app-shell";
import { RiskFlags } from "../../components/daily-cockpit/evidence-pills";
import {
  AdvisoryTable,
  EmptyState,
  MetricTile,
  SectionCard,
  StatusChip,
} from "../../components/workstation";
import {
  formatTimestamp,
  list,
  readLatestPortfolioExposure,
  readLatestTradingAdvisory,
  type PortfolioPosition,
} from "../../lib/advisory/workstation-data";

import { ShadowCurveChart } from "./components/shadow-curve-chart";

export const dynamic = "force-dynamic";

function positionWeight(position: PortfolioPosition): string | number | null | undefined {
  return position.portfolio_weight ?? position.portfolio_weight_pct;
}

function targetWeight(position: PortfolioPosition): string | number | null | undefined {
  return position.target_weight ?? position.target_weight_pct;
}

function drift(position: PortfolioPosition): string | number | null | undefined {
  if (position.drift !== undefined && position.drift !== null) {
    return position.drift;
  }
  return targetWeight(position) ? "pending calculation" : "target unavailable";
}

export default async function PortfolioPage() {
  const [portfolioPayload, advisoryPayload] = await Promise.all([
    readLatestPortfolioExposure(),
    readLatestTradingAdvisory(),
  ]);
  const snapshot = portfolioPayload.snapshot;
  const positions = snapshot?.positions ?? [];
  const advisoriesByTicker = new Map(
    (advisoryPayload.items ?? []).map((advisory) => [advisory.ticker, advisory]),
  );

  return (
    <div className="control-room-shell">
      <AppShell
        eyebrow="Portfolio"
        title="Portfolio Workbench"
        aside={<div className="advisory-badge">Advisory-only</div>}
      >
        <section className="summary-strip" aria-label="Portfolio exposure status">
          <MetricTile
            label="Total market value"
            value={snapshot?.total_market_value ?? "n/a"}
            detail={snapshot?.currency ?? "currency pending"}
          />
          <MetricTile
            label="Gross equity exposure"
            value={snapshot?.gross_equity_exposure ?? "n/a"}
            detail={snapshot?.source ?? "source pending"}
          />
          <MetricTile
            label="Positions"
            value={snapshot?.position_count ?? 0}
            detail={formatTimestamp(snapshot?.as_of)}
          />
          <MetricTile
            label="Cash placeholder"
            value={snapshot?.cash_placeholder ?? "n/a"}
            detail="manual journal only"
            tone="review"
          />
        </section>

        <SectionCard
          eyebrow="Read-only exposure"
          title="Detailed portfolio exposure"
          subtitle="Current positions, advisory stances, risk flags, and target/drift availability from backend read models."
          badge={<StatusChip label={portfolioPayload.status ?? "degraded"} tone="review" />}
        >
          <AdvisoryTable
            columns={["Symbol", "Role / segment", "Weight", "Target / drift", "PnL", "Advisory"]}
            density="compact"
            emptyLabel="No portfolio exposure snapshot is available."
            rows={positions.map((position) => {
              const advisory = advisoriesByTicker.get(position.ticker);
              return {
                id: position.ticker ?? position.company ?? "position",
                cells: [
                  <span className="table-main" key="symbol">
                    <Link className="ticker-link" href={`/ticker/${position.ticker ?? "NVDA"}`}>
                      {position.ticker ?? "Ticker"}
                    </Link>
                    <small>{position.company ?? "Company pending"}</small>
                  </span>,
                  <span className="table-main" key="role">
                    <strong>{position.role ?? (list(position.segment_tags).join(", ") || "segment pending")}</strong>
                    <small>{position.bucket ?? position.open_trade_plan_id ?? "no active plan link"}</small>
                  </span>,
                  positionWeight(position) ?? "n/a",
                  <span className="table-main" key="target">
                    <strong>{targetWeight(position) ?? "target unavailable"}</strong>
                    <small>{drift(position)}</small>
                  </span>,
                  position.unrealized_pnl ?? "not calculated",
                  <StatusChip
                    key="stance"
                    label={advisory?.analyst_action ?? "unrated"}
                    tone="review"
                  />,
                ],
              };
            })}
          />
          {positions.length === 0 ? (
            <EmptyState
              title="Portfolio snapshot empty"
              detail="The page remains advisory-only while waiting for backend exposure rows."
            />
          ) : null}
        </SectionCard>

        <div className="workstation-grid workstation-grid-2">
          <SectionCard
            eyebrow="Concentration and correlation"
            title="Exposure checks"
            badge={<StatusChip label="deterministic checks" tone="neutral" />}
          >
            <div className="compact-list">
              <article className="compact-card">
                <strong>Concentration flags</strong>
                <RiskFlags flags={list(snapshot?.concentration_flags)} />
                {list(snapshot?.concentration_flags).length === 0 ? (
                  <span className="muted-meta">No concentration flags published.</span>
                ) : null}
              </article>
              <article className="compact-card">
                <strong>Correlation exposure IDs</strong>
                <span>{list(snapshot?.correlation_exposure_ids).join(", ") || "No correlation cluster published."}</span>
              </article>
              <article className="compact-card">
                <strong>Price freshness</strong>
                <RiskFlags flags={list(snapshot?.stale_price_flags)} />
                {list(snapshot?.stale_price_flags).length === 0 ? (
                  <span className="muted-meta">No stale price flags published.</span>
                ) : null}
              </article>
            </div>
          </SectionCard>

          <SectionCard
            eyebrow="Counterfactual drift"
            title="Advisory target availability"
            badge={<StatusChip label="planning guidance only" tone="review" />}
          >
            {snapshot?.target_weights_id ? (
              <div className="compact-card">
                <strong>{snapshot.target_weights_id}</strong>
                <span>
                  Target weights are available from the backend read model. Review
                  drift in context before any manual journal entry.
                </span>
              </div>
            ) : (
              <EmptyState
                title="Target weights unavailable"
                detail="Counterfactual drift cannot be calculated until deterministic target weights are published."
              />
            )}
            <p className="panel-note">
              Shadow simulation is advisory-only and cannot transmit trades or
              connect accounts. Deterministic code owns portfolio weights and PnL.
            </p>
          </SectionCard>
        </div>

        <SectionCard
          eyebrow="Shadow curve"
          title="Counterfactual value curve"
          badge={<StatusChip label="manual review only" tone="neutral" />}
        >
          <ShadowCurveChart />
        </SectionCard>
      </AppShell>
    </div>
  );
}
