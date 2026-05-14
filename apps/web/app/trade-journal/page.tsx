import { AppShell } from "../../components/app-shell";
import { SectionPanel } from "../../components/section-panel";
import { journalEntries } from "../../lib/portfolio-data";

export default function TradeJournalPage() {
  return (
    <div className="control-room-shell">
      <AppShell eyebrow="Local Journal" title="Trade Journal">
        <div className="workbench-grid">
          <SectionPanel eyebrow="Manual records" title="Trade Journal" aside={<span className="advisory-inline">Advisory-only</span>}>
            <div className="data-table" role="table" aria-label="Trade journal">
              <div className="data-row data-header" role="row">
                <span>Ticker</span>
                <span>Action</span>
                <span>Status</span>
                <span>Target price</span>
                <span>Limit price</span>
                <span>Linked recommendation_id</span>
              </div>
              {journalEntries.map((entry) => (
                <div className="data-row" role="row" key={`${entry.ticker}-${entry.action}`}>
                  <span>{entry.ticker}</span>
                  <span>{entry.action}</span>
                  <span>{entry.status}</span>
                  <span>{entry.targetPrice}</span>
                  <span>{entry.limitPrice}</span>
                  <span>{entry.linkedRecommendation}</span>
                </div>
              ))}
            </div>
          </SectionPanel>
        </div>
      </AppShell>
    </div>
  );
}
