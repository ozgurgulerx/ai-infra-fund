import { AppShell } from "../../components/app-shell";
import { SectionPanel } from "../../components/section-panel";
import { portfolioRows } from "../../lib/portfolio-data";

export default function WatchlistPage() {
  return (
    <div className="control-room-shell">
      <AppShell eyebrow="Universe" title="Watchlist Status">
        <div className="workbench-grid">
          <SectionPanel eyebrow="Local universe" title="Watchlist Status" aside={<span className="readonly-label">CSV-backed</span>}>
            <div className="data-table data-table-four" role="table" aria-label="Watchlist">
              <div className="data-row data-header" role="row">
                <span>Symbol</span>
                <span>Theme role</span>
                <span>Bucket</span>
                <span>Weight</span>
              </div>
              {portfolioRows.map(([symbol, role, bucket, weight]) => (
                <div className="data-row" role="row" key={symbol}>
                  <span>{symbol}</span>
                  <span>{role}</span>
                  <span>{bucket}</span>
                  <span>{weight}</span>
                </div>
              ))}
            </div>
          </SectionPanel>
        </div>
      </AppShell>
    </div>
  );
}
